import os

import redis


# Redis creates a client configured to connect to the Azure Managed Redis endpoint.
client = redis.Redis(
    host=os.environ["REDIS_HOST"],
    port=int(os.environ.get("REDIS_PORT", "10000")),
    password=os.environ["REDIS_ACCESS_KEY"],
    ssl=True,
    decode_responses=True,
    socket_connect_timeout=10,
)

demo_keys = [
    "demo:message",
    "demo:course:001",
    "demo:categories",
    "demo:recent-courses",
    "demo:page-views",
    "demo:temporary-note",
]

try:
    # PING checks whether the Redis server is reachable and responding.
    print("PING:", client.ping())

    # DELETE removes the specified keys so every run starts with the same data.
    client.delete(*demo_keys)

    # SET stores a string value under a key.
    client.set("demo:message", "Hello from Azure Managed Redis!")

    # GET retrieves the string value stored under a key.
    print("\nString:", client.get("demo:message"))

    # HSET stores multiple named fields and values in a Redis hash.
    client.hset(
        "demo:course:001",
        mapping={
            "title": "Microsoft Entra ID and managed identities",
            "category": "Security",
            "level": "Beginner",
        },
    )

    # HGETALL retrieves every field and value from the hash.
    print("\nHash:", client.hgetall("demo:course:001"))

    # SADD adds unique values to a set; adding "AI" twice still stores it once.
    client.sadd("demo:categories", "AI", "Data", "Security", "AI")

    # SMEMBERS retrieves all unique values from the set.
    print("\nSet:", sorted(client.smembers("demo:categories")))

    # RPUSH appends values to the right-hand end of a list.
    client.rpush(
        "demo:recent-courses",
        "Build generative AI applications",
        "Vector search and semantic retrieval",
    )

    # LRANGE retrieves list elements; 0 through -1 means the entire list.
    print("\nList:", client.lrange("demo:recent-courses", 0, -1))

    # INCR atomically increases the numeric value by one on each call.
    client.incr("demo:page-views")
    client.incr("demo:page-views")

    # GET retrieves the counter value stored as a Redis string.
    print("\nCounter:", client.get("demo:page-views"))

    # SET stores a temporary string value.
    client.set("demo:temporary-note", "This key expires in 60 seconds.")

    # EXPIRE assigns a 60-second lifetime to the key.
    client.expire("demo:temporary-note", 60)

    # TTL returns the key's remaining lifetime in seconds.
    print("\nTemporary key TTL:", client.ttl("demo:temporary-note"), "seconds")
finally:
    # CLOSE releases the client's connections to Redis.
    client.close()
