import os

import psycopg


def connect():
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.getenv("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode="require",
    )


with connect() as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_courses_category
            ON courses (category);
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_courses_embedding_hnsw
            ON courses
            USING hnsw (embedding vector_cosine_ops);
            """
        )
        cursor.execute("ANALYZE courses;")

        cursor.execute(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'courses'
            ORDER BY indexname;
            """
        )
        indexes = cursor.fetchall()

        cursor.execute(
            """
            EXPLAIN
            SELECT course_id, title
            FROM courses
            WHERE category = 'AI';
            """
        )
        query_plan = cursor.fetchall()

print("Indexes on the courses table:")
for name, definition in indexes:
    print(f"\n{name}\n  {definition}")

print("\nQuery plan for filtering by category:")
for (line,) in query_plan:
    print(f"  {line}")

print(
    "\nPostgreSQL can choose a sequential scan for this tiny dataset because "
    "reading every row is cheaper. Indexes become useful as the table grows."
)
