import os

import numpy as np
import psycopg
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI
from pgvector.psycopg import register_vector


def connect():
    connection = psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.getenv("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode="require",
    )
    register_vector(connection)
    return connection


token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)
openai = OpenAI(
    base_url=os.environ["OPENAI_ENDPOINT"],
    api_key=token_provider,
)
embedding_deployment = os.environ["EMBEDDING_DEPLOYMENT"]
chat_deployment = os.environ["CHAT_DEPLOYMENT"]


def create_embedding(text):
    response = openai.embeddings.create(
        model=embedding_deployment,
        input=text,
    )
    return np.array(response.data[0].embedding, dtype=np.float32)


def ensure_embeddings(cursor):
    cursor.execute(
        """
        SELECT course_id, title, description
        FROM courses
        WHERE embedding IS NULL;
        """
    )
    for course_id, title, description in cursor.fetchall():
        embedding = create_embedding(f"{title}. {description}")
        cursor.execute(
            """
            UPDATE courses
            SET embedding = %s
            WHERE course_id = %s;
            """,
            (embedding, course_id),
        )


question = input("Ask a question about the course catalog: ").strip()
question_embedding = create_embedding(question)

with connect() as connection:
    with connection.cursor() as cursor:
        ensure_embeddings(cursor)
        connection.commit()

        cursor.execute(
            """
            SELECT
                title,
                description,
                1 - (embedding <=> %s) AS cosine_similarity
            FROM courses
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT 3;
            """,
            (question_embedding, question_embedding),
        )
        retrieved_courses = cursor.fetchall()

context = "\n\n".join(
    f"Course: {title}\nDescription: {description}"
    for title, description, _ in retrieved_courses
)

prompt = f"""You answer questions about a training course catalog.
Use only the supplied course context. If the context does not contain the
answer, say that the course catalog does not contain enough information.

Course context:
{context}

Question:
{question}
"""

response = openai.responses.create(
    model=chat_deployment,
    input=prompt,
)

print("\nRetrieved courses:")
for title, _, similarity in retrieved_courses:
    print(f"- {title} (similarity: {similarity:.4f})")

print("\nAnswer:")
print(response.output_text)
