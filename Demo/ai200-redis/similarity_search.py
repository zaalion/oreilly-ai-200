import os

import numpy as np
import redis
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI
from redis.commands.search.field import TagField, TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError


INDEX_NAME = "course-vector-index"
KEY_PREFIX = "vector-course:"
VECTOR_DIMENSIONS = 1536


def as_text(value: bytes | str) -> str:
    return value.decode("utf-8") if isinstance(value, bytes) else value


# Redis creates a client configured for TLS and preserves binary vector data as bytes.
redis_client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ.get("REDIS_PORT", "10000")),
    password=os.environ["REDIS_ACCESS_KEY"],
    ssl=True,
    decode_responses=False,
    socket_connect_timeout=10,
)

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)
openai_client = OpenAI(
    base_url=os.environ["OPENAI_ENDPOINT"],
    api_key=token_provider,
)
embedding_deployment = os.environ["EMBEDDING_DEPLOYMENT"]

courses = [
    {
        "id": "course-001",
        "category": "Security",
        "title": "Microsoft Entra ID and managed identities",
        "description": (
            "Protect cloud applications with identity-based authentication, "
            "managed identities, and role-based access control."
        ),
    },
    {
        "id": "course-002",
        "category": "AI",
        "title": "Build generative AI applications",
        "description": (
            "Create applications that send prompts to language models and "
            "generate natural-language responses."
        ),
    },
    {
        "id": "course-003",
        "category": "Data",
        "title": "Cache application data with Azure Managed Redis",
        "description": (
            "Store temporary application data in memory for low-latency reads, "
            "caching, counters, sessions, and fast data access."
        ),
    },
    {
        "id": "course-004",
        "category": "AI",
        "title": "Vector search and semantic retrieval",
        "description": (
            "Convert text into embeddings and retrieve information according "
            "to meaning instead of exact keyword matches."
        ),
    },
]

try:
    # PING checks whether the Redis server is reachable and responding.
    redis_client.ping()

    fields = [
        TextField("title"),
        TextField("description"),
        TagField("category"),
        VectorField(
            "embedding",
            "FLAT",
            {
                "TYPE": "FLOAT32",
                "DIM": VECTOR_DIMENSIONS,
                "DISTANCE_METRIC": "COSINE",
            },
        ),
    ]

    try:
        # FT().CREATE_INDEX creates a RediSearch index over hashes with the key prefix.
        redis_client.ft(INDEX_NAME).create_index(
            fields,
            definition=IndexDefinition(
                prefix=[KEY_PREFIX],
                index_type=IndexType.HASH,
            ),
        )
        print(f"Created index: {INDEX_NAME}")
    except ResponseError as error:
        if "Index already exists" not in str(error):
            raise
        print(f"Using existing index: {INDEX_NAME}")

    course_texts = [
        f"{course['title']}. {course['description']}" for course in courses
    ]
    embedding_response = openai_client.embeddings.create(
        model=embedding_deployment,
        input=course_texts,
    )

    for course, embedding_item in zip(courses, embedding_response.data):
        embedding = np.asarray(embedding_item.embedding, dtype=np.float32)

        # HSET stores the course fields and binary embedding together in a Redis hash.
        redis_client.hset(
            f"{KEY_PREFIX}{course['id']}",
            mapping={
                "title": course["title"],
                "description": course["description"],
                "category": course["category"],
                "embedding": embedding.tobytes(),
            },
        )

    print(f"Stored {len(courses)} courses.")

    search_text = input("\nSemantic search: ").strip()
    if not search_text:
        raise ValueError("Enter a search question.")

    query_embedding = openai_client.embeddings.create(
        model=embedding_deployment,
        input=search_text,
    ).data[0].embedding
    query_vector = np.asarray(query_embedding, dtype=np.float32).tobytes()

    query = (
        Query("*=>[KNN 3 @embedding $query_vector AS vector_distance]")
        .sort_by("vector_distance")
        .return_fields("title", "category", "description", "vector_distance")
        .dialect(2)
    )

    # FT().SEARCH runs the K-nearest-neighbor query against the RediSearch index.
    results = redis_client.ft(INDEX_NAME).search(
        query,
        query_params={"query_vector": query_vector},
    )

    print(f'\nResults for: "{search_text}"')
    for position, document in enumerate(results.docs, start=1):
        distance = float(as_text(document.vector_distance))
        similarity = 1 - distance
        print(
            f"{position}. {as_text(document.title)} "
            f"(category: {as_text(document.category)}, "
            f"similarity: {similarity:.4f})"
        )
        print(f"   {as_text(document.description)}")
finally:
    # CLOSE releases the client's connections to Redis.
    redis_client.close()
