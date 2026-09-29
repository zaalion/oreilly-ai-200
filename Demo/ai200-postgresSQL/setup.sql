CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS courses (
    course_id text PRIMARY KEY,
    category text NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    embedding vector(1536)
);

INSERT INTO courses (course_id, category, title, description)
VALUES
    ('course-001', 'Security', 'Microsoft Entra ID and managed identities',
     'Protect cloud applications with identity-based authentication, managed identities, and role-based access control.'),
    ('course-002', 'AI', 'Build generative AI applications',
     'Create applications that send prompts to language models and generate natural-language responses.'),
    ('course-003', 'Data', 'Azure Database for PostgreSQL',
     'Store relational data and query it with SQL using a managed PostgreSQL flexible server.'),
    ('course-004', 'AI', 'Vector search and semantic retrieval',
     'Convert text into embeddings and retrieve information by meaning instead of exact keyword matches.'),
    ('course-005', 'Data', 'Database indexing fundamentals',
     'Improve query performance with B-tree indexes, execution plans, and PostgreSQL query optimization.'),
    ('course-006', 'AI', 'Retrieval-augmented generation',
     'Retrieve relevant private data and supply it to a language model as context for grounded answers.')
ON CONFLICT (course_id) DO UPDATE SET
    category = EXCLUDED.category,
    title = EXCLUDED.title,
    description = EXCLUDED.description;
