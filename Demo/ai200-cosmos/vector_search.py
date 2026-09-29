import os

from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import OpenAI


cosmos = CosmosClient.from_connection_string(
    os.environ["COSMOS_CONNECTION_STRING"]
)
container = (
    cosmos.get_database_client(os.environ["COSMOS_DATABASE_NAME"])
    .get_container_client(os.environ["COSMOS_CONTAINER_NAME"])
)

token_provider = get_bearer_token_provider(
    DefaultAzureCredential(),
    "https://ai.azure.com/.default",
)
openai = OpenAI(
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
        "title": "Store JSON data with Azure Cosmos DB",
        "description": (
            "Build globally distributed applications with a NoSQL database, "
            "partitioned containers, and low-latency queries."
        ),
    },
    {
        "id": "course-004",
        "category": "AI",
        "title": "Vector search and semantic retrieval",
        "description": (
            "Convert text into embeddings and retrieve documents according "
            "to meaning instead of exact keyword matches."
        ),
    },
]

# Embed and store the sample courses.
texts = [f"{course['title']}. {course['description']}" for course in courses]
embedding_response = openai.embeddings.create(
    model=embedding_deployment,
    input=texts,
)

for course, embedding_item in zip(courses, embedding_response.data):
    course["descriptionVector"] = embedding_item.embedding
    container.upsert_item(course)

print(f"Stored {len(courses)} courses.")

# Convert the user's natural-language search into a vector.
search_text = "I need a low-latency database for JSON documents"
search_vector = openai.embeddings.create(
    model=embedding_deployment,
    input=search_text,
).data[0].embedding

query = """
SELECT TOP 3
    c.id,
    c.category,
    c.title,
    c.description,
    VectorDistance(c.descriptionVector, @embedding) AS similarityScore
FROM c
ORDER BY VectorDistance(c.descriptionVector, @embedding)
"""

results = container.query_items(
    query=query,
    parameters=[
        {"name": "@embedding", "value": search_vector}
    ],
    enable_cross_partition_query=True,
)

print(f'\nSearch: "{search_text}"')
for result in results:
    print(
        f"{result['title']} "
        f"(category: {result['category']}, "
        f"score: {result['similarityScore']:.4f})"
    )
