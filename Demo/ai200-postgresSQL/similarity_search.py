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


def create_embedding(text):
    response = openai.embeddings.create(
        model=embedding_deployment,
        input=text,
    )
    return np.array(response.data[0].embedding, dtype=np.float32)


with connect() as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT course_id, title, description
            FROM courses
            WHERE embedding IS NULL;
            """
        )
        courses_without_embeddings = cursor.fetchall()

        for course_id, title, description in courses_without_embeddings:
            embedding = create_embedding(f"{title}. {description}")
            cursor.execute(
                """
                UPDATE courses
                SET embedding = %s
                WHERE course_id = %s;
                """,
                (embedding, course_id),
            )

        connection.commit()

        search_text = input("Semantic search: ").strip()
        search_embedding = create_embedding(search_text)

        cursor.execute(
            """
            SELECT
                course_id,
                category,
                title,
                description,
                1 - (embedding <=> %s) AS cosine_similarity
            FROM courses
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> %s
            LIMIT 3;
            """,
            (search_embedding, search_embedding),
        )
        results = cursor.fetchall()

print(f'\nMost relevant courses for "{search_text}":')
for course_id, category, title, description, similarity in results:
    print(
        f"\n{title} ({category})\n"
        f"Similarity: {similarity:.4f}\n"
        f"{description}"
    )
