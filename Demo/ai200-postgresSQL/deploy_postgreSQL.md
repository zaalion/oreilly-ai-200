# Deploy Azure Database for PostgreSQL Flexible Server

This guide provisions Azure Database for PostgreSQL Flexible Server with Azure CLI and demonstrates SQL queries, relational and vector indexes, semantic similarity search, and retrieval-augmented generation with separate Python scripts.

`pgvector` is an open-source PostgreSQL extension that adds a vector data type, vector-distance operators, and specialized indexes. It allows PostgreSQL to store embeddings and find records with similar meaning without requiring a separate vector database. The extension is installed in PostgreSQL with the name `vector`.

## Scenario: semantic course search

The database stores a training course catalog. Traditional SQL queries filter courses by exact values, while `pgvector` retrieves courses whose descriptions are semantically related to a natural-language question.

The RAG console application retrieves relevant course records from PostgreSQL and gives that context to the deployed `gpt-5-mini` model to generate an answer.

```text
Question
   ↓
text-embedding-3-small creates a query vector
   ↓
PostgreSQL and pgvector retrieve relevant courses
   ↓
Retrieved course descriptions are added to the prompt
   ↓
gpt-5-mini generates a grounded answer
```

## Files used by the demonstrations

| File | Purpose |
| --- | --- |
| `setup.sql` | Creates the `vector` extension, course table, and sample rows |
| `query_demo.py` | Runs a parameterized SQL query with an exact category filter |
| `indexing_demo.py` | Creates a B-tree index and an HNSW vector index and displays the indexes |
| `similarity_search.py` | Generates embeddings and runs cosine-similarity search with `pgvector` |
| `rag_console.py` | Retrieves relevant records and sends them to `gpt-5-mini` as grounding context |

PostgreSQL provisioning and initial schema creation are performed with Azure CLI and SQL commands, not Python.

## 1. Prerequisites

- An Azure subscription
- Azure CLI
- Python 3.10 or later
- The `text-embedding-3-small` deployment in `oreilly-foundry-ai200`
- The existing `gpt-5-mini` deployment
- `Cognitive Services OpenAI User` access to the Foundry resource

## 2. Sign in and define the Azure resources

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

az extension add --name rdbms-connect --upgrade

$resourceGroup = "AI-200"
$location = "canadacentral"
$suffix = Get-Random -Minimum 100000 -Maximum 999999
$serverName = "oreilly-ai200-postgres-$suffix"
$databaseName = "CourseCatalog"
$adminUser = "pgadminuser"
$adminPassword = Read-Host "Enter a PostgreSQL administrator password" -MaskInput
$clientIp = Read-Host "Enter your public IPv4 address"
```

The PostgreSQL server name must be globally unique. The random suffix helps create an available name.

## 3. Provision PostgreSQL Flexible Server

Create a PostgreSQL 16 server with a burstable compute SKU and public access restricted to the supplied client IP:

```powershell
az postgres flexible-server create `
  --resource-group $resourceGroup `
  --name $serverName `
  --location $location `
  --admin-user $adminUser `
  --admin-password $adminPassword `
  --version 16 `
  --tier Burstable `
  --sku-name Standard_B1ms `
  --storage-size 32 `
  --public-access $clientIp `
  --password-auth Enabled
```

Retrieve the server hostname:

```powershell
$serverHost = az postgres flexible-server show `
  --resource-group $resourceGroup `
  --name $serverName `
  --query fullyQualifiedDomainName `
  --output tsv

Write-Output $serverHost
```

## 4. Create the database

```powershell
az postgres flexible-server db create `
  --resource-group $resourceGroup `
  --server-name $serverName `
  --database-name $databaseName
```

## 5. Allow the `vector` extension

Azure Database for PostgreSQL requires extensions to be allowlisted at the server level:

```powershell
az postgres flexible-server parameter set `
  --resource-group $resourceGroup `
  --server-name $serverName `
  --name azure.extensions `
  --value vector
```

The PostgreSQL community project is called `pgvector`, but its PostgreSQL extension name is `vector`.

## 6. Create the extension, table, and sample rows

The table uses `vector(1536)` because the default output from `text-embedding-3-small` contains 1,536 numbers.

Run this command from `Demo\ai200-postgresSQL`:

```powershell
az postgres flexible-server execute `
  --name $serverName `
  --admin-user $adminUser `
  --admin-password $adminPassword `
  --database-name $databaseName `
  --file-path .\setup.sql
```

Using `--file-path` allows Azure CLI to execute every statement in the SQL file.

## 7. Configure the Python environment

Run these commands from `Demo\ai200-postgresSQL`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade "psycopg[binary]" pgvector numpy azure-identity openai
```

Set the environment variables used by all four Python scripts:

```powershell
$env:PGHOST = $serverHost
$env:PGPORT = "5432"
$env:PGDATABASE = $databaseName
$env:PGUSER = $adminUser
$env:PGPASSWORD = $adminPassword

$env:OPENAI_ENDPOINT = "https://oreilly-foundry-ai200.services.ai.azure.com/openai/v1/"
$env:EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
$env:CHAT_DEPLOYMENT = "gpt-5-mini"
```

These environment variables exist only in the current PowerShell session. Do not store the PostgreSQL password in source control.

## 8. Demonstrate a SQL query

Run:

```powershell
python .\query_demo.py
```

Enter a category such as `AI`, `Security`, or `Data`.

The script demonstrates:

- Connecting securely with TLS
- A parameterized `SELECT` statement
- Filtering with `WHERE category = %s`
- Ordering and displaying returned rows

Because the value is passed separately from the SQL statement, the script does not concatenate user input into SQL.

## 9. Demonstrate indexing

Run:

```powershell
python .\indexing_demo.py
```

The script creates:

- `idx_courses_category`, a B-tree index for exact category filters
- `idx_courses_embedding_hnsw`, an HNSW vector index using cosine distance

It then lists the indexes and displays the execution plan for a category query.

The table contains only a few rows, so PostgreSQL may choose a sequential scan because it is cheaper than using an index. On a larger table, the indexes reduce the amount of data PostgreSQL must examine.

## 10. Demonstrate semantic similarity search

Run:

```powershell
python .\similarity_search.py
```

On its first run, the script:

1. Finds courses that do not have embeddings.
2. Sends each course title and description to `text-embedding-3-small`.
3. Stores each 1,536-dimensional vector in the PostgreSQL `embedding` column.
4. Prompts for a natural-language search.
5. Embeds the search and uses the pgvector cosine-distance operator `<=>`.
6. Returns the three most semantically similar courses.

After running the script, wait for this prompt:

```text
Semantic search:
```

Type the following question at that prompt and press **Enter**:

```text
How do I protect access to a cloud application?
```

You do not need to edit `similarity_search.py`. The script reads the search text from the terminal.

This should rank **Microsoft Entra ID and managed identities** highly even though the wording is different.

The query calculates cosine similarity as:

```sql
-- Convert cosine distance to similarity; a value closer to 1 means more similar.
1 - (embedding <=> query_vector)
```

In this expression:

- `embedding` is the vector stored for a course description.
- `query_vector` is the vector generated from the question entered at the `Semantic search:` prompt.
- `<=>` is the pgvector cosine-distance operator. A smaller distance means the two vectors are closer.
- `1 - distance` converts cosine distance into a cosine-similarity score.

A similarity score closer to `1` means the course description is more semantically related to the question. The SQL query orders by the cosine distance from smallest to largest, so the closest matches appear first.

## 11. Demonstrate RAG with a Python console application

Run:

```powershell
python .\rag_console.py
```

Ask a question such as:

```text
Which course teaches me how to search data by meaning?
```

The script performs two distinct model calls:

1. `text-embedding-3-small` converts the question into a vector.
2. PostgreSQL retrieves the three closest course records.
3. The script adds those records to a prompt as context.
4. `gpt-5-mini` generates an answer using only that retrieved context.

The console displays both the retrieved course titles and the final generated answer. Showing the retrieved rows makes the retrieval step visible instead of presenting RAG as a single model call.

> **Note:** Step 11 uses the similarity search from Step 10 as its retrieval stage. Similarity search stops after returning the relevant database records. RAG continues by adding those records to the prompt and asking `gpt-5-mini` to generate a grounded answer.

```text
Similarity search: Question → embedding → PostgreSQL vector search → relevant courses
RAG:               Question → embedding → PostgreSQL vector search → relevant courses → gpt-5-mini → answer
```

## 12. View the data and indexes with SQL

Display the stored courses:

```powershell
az postgres flexible-server execute `
  --name $serverName `
  --admin-user $adminUser `
  --admin-password $adminPassword `
  --database-name $databaseName `
  --querytext "SELECT course_id, category, title, embedding IS NOT NULL AS has_embedding FROM courses ORDER BY course_id;"
```

Display the table indexes:

```powershell
az postgres flexible-server execute `
  --name $serverName `
  --admin-user $adminUser `
  --admin-password $adminPassword `
  --database-name $databaseName `
  --querytext "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'courses' ORDER BY indexname;"
```

## Troubleshooting

- **Connection timeout:** Confirm that `$clientIp` is the current public IP and that the PostgreSQL firewall rule includes it.
- **Password authentication failed:** Confirm `PGUSER`, `PGPASSWORD`, and the administrator credentials used at server creation.
- **The `vector` extension is unavailable:** Confirm that `azure.extensions` contains `vector`, then reconnect to the database and run `CREATE EXTENSION vector`.
- **Embedding authorization fails:** Sign in with `az login` and confirm the identity has `Cognitive Services OpenAI User` on `oreilly-foundry-ai200`.
- **Vector dimensions differ:** The database column expects 1,536 dimensions. Use the default `text-embedding-3-small` output or change the schema and all generated vectors consistently.
- **The query plan uses a sequential scan:** This is normal for the six-row sample table.

## Microsoft Learn references

- [Create an Azure Database for PostgreSQL Flexible Server](https://learn.microsoft.com/azure/postgresql/flexible-server/quickstart-create-server)
- [Azure CLI reference for PostgreSQL Flexible Server](https://learn.microsoft.com/cli/azure/postgres/flexible-server)
- [Connect and query PostgreSQL with Python](https://learn.microsoft.com/azure/postgresql/connectivity/connect-python)
- [Enable and use pgvector](https://learn.microsoft.com/azure/postgresql/extensions/how-to-use-pgvector)
- [Create PostgreSQL extensions](https://learn.microsoft.com/azure/postgresql/extensions/how-to-create-extensions)
- [Semantic search with Azure OpenAI and PostgreSQL](https://learn.microsoft.com/azure/postgresql/azure-ai/generative-ai-semantic-search)
- [Generate embeddings with Azure OpenAI](https://learn.microsoft.com/azure/foundry/openai/how-to/embeddings)
