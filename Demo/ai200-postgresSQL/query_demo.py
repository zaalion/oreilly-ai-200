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


category = input("Category (AI, Security, or Data): ").strip()

with connect() as connection:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT course_id, title, description
            FROM courses
            WHERE category = %s
            ORDER BY title;
            """,
            (category,),
        )
        rows = cursor.fetchall()

if not rows:
    print(f'No courses found for category "{category}".')
else:
    for course_id, title, description in rows:
        print(f"\n{course_id}: {title}\n{description}")
