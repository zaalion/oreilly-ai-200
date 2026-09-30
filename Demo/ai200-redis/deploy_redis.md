# Deploy Azure Managed Redis

This guide provisions an Azure Managed Redis instance with Azure CLI and demonstrates common Redis data operations and semantic similarity search with two Python scripts.

## Scenario: course data and semantic course search

The first script stores and retrieves course-related data by using Redis strings, hashes, lists, sets, counters, and key expiration.

The second script stores course descriptions with vector embeddings. A natural-language question is converted into an embedding, and Azure Managed Redis returns courses with similar meaning.

```text
Question
   ↓
text-embedding-3-small creates a query vector
   ↓
Azure Managed Redis and RediSearch compare stored vectors
   ↓
The most similar courses are returned
```

## Understand the Redis configuration choices

### Modules

Modules add capabilities that are not part of the basic Redis command set. Azure Managed Redis supports managed modules such as:

- **RediSearch:** Adds full-text search, secondary indexes, filtering, and vector similarity search.
- **RedisJSON:** Adds commands for storing, retrieving, and updating JSON documents.
- **RedisBloom:** Adds probabilistic data structures such as Bloom filters.
- **RedisTimeSeries:** Adds time-series storage and queries.

Modules must be selected when the Redis database is created; they cannot be added afterward. Module availability can also depend on the selected tier and other configuration settings. This guide enables `RediSearch` because the similarity-search script needs a vector index and a K-nearest-neighbor query.

### Eviction Policy

The eviction policy determines what Redis does when its allocated memory is full:

- **NoEviction:** Redis does not remove existing keys. Write operations that require more memory fail instead.
- **AllKeysLRU:** Removes the least recently used keys from all keys.
- **AllKeysLFU:** Removes the least frequently used keys from all keys.
- **AllKeysRandom:** Removes random keys.
- **VolatileLRU, VolatileLFU, and VolatileRandom:** Remove only keys that have an expiration time.
- **VolatileTTL:** Removes keys with an expiration time, starting with keys that have the shortest remaining time.

This guide uses `NoEviction` because Azure Managed Redis requires that policy when RediSearch is enabled. The application must handle a failed write if the instance runs out of available memory.

### Clustering Policy

Clustering divides data across Redis processes called shards. Azure Managed Redis provides three client-facing clustering policies:

- **OSSCluster:** Uses the open-source Redis Cluster protocol. A cluster-aware client connects to individual shard endpoints. This policy generally provides the highest throughput.
- **EnterpriseCluster:** Presents one endpoint and internally routes each request to the correct shard. Client libraries do not need to support the Redis Cluster protocol.
- **NoCluster:** Stores data without sharding. It is available only for instances of 25 GB or smaller and supports applications that depend heavily on cross-key or cross-slot operations.

This guide uses `EnterpriseCluster` because it is the clustering policy supported by the RediSearch module.

### Data Persistence

Redis primarily stores data in memory. Azure Managed Redis can optionally persist that data to a managed disk and use it to restore the same instance after an unexpected failure:

- **RDB persistence:** Saves periodic binary snapshots. It has less effect on normal throughput, but changes made after the most recent snapshot can be lost.
- **AOF persistence:** Records write operations in an append-only log approximately once per second. It can reduce potential data loss, but it has a larger effect on write throughput.

Persistence requires high availability. RDB and AOF cannot be enabled together, and persistence cannot be combined with active geo-replication. Persistence restores the same Redis instance; it is not a backup or point-in-time recovery system. Import and export are used when a portable backup is required.

The instance created in this guide has high availability disabled, so it does not enable data persistence.

### Authentication options

Azure Managed Redis supports two authentication methods:

- **Microsoft Entra ID:** Uses an Entra user, service principal, or managed identity and avoids storing a static password. The identity must be added as a Redis user, and the client must obtain and refresh Redis access tokens.
- **Access keys:** Uses the Redis primary or secondary access key as the password. The key must be kept outside source code and rotated if it is exposed.

Microsoft Entra ID authentication is enabled by default for Azure Managed Redis. This guide also enables access-key authentication so the two local Python scripts can use the primary key stored in the current PowerShell session. Both methods require a TLS-encrypted connection.


## Files used by the demonstrations

| File | Purpose |
| --- | --- |
| `data_operations.py` | Demonstrates strings, hashes, lists, sets, counters, expiration, and deletion |
| `similarity_search.py` | Creates a vector index, stores course embeddings, and performs semantic similarity search |

Azure resource provisioning is performed with Azure CLI. Python is used only for the data demonstrations.

## 1. Prerequisites

- An Azure subscription
- Azure CLI 2.75.0 or later
- Python 3.10 or later
- The `text-embedding-3-small` deployment in `oreilly-foundry-ai200`
- `Cognitive Services OpenAI User` access to the Foundry resource

## 2. Sign in and define the Azure resources

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

az extension add --name redisenterprise --upgrade

$resourceGroup = "AI-200"
$location = "centralus"
$suffix = Get-Random -Minimum 100000 -Maximum 999999
$redisName = "oreilly-ai200-redis-$suffix"
```

The Azure Managed Redis name must be unique in Azure. The random suffix helps produce an available name.

## 3. Provision Azure Managed Redis

Create a small Balanced instance with a default database:

```powershell
az redisenterprise create `
  --name $redisName `
  --resource-group $resourceGroup `
  --location $location `
  --sku Balanced_B0 `
  --high-availability Disabled `
  --public-network-access Enabled `
  --client-protocol Encrypted `
  --clustering-policy EnterpriseCluster `
  --eviction-policy NoEviction `
  --modules name=RediSearch `
  --access-keys-authentication Enabled
```

This configuration uses:

- `Balanced_B0` for the smallest Balanced tier in this example
- TLS-encrypted client connections
- Enterprise clustering, which RediSearch requires
- `NoEviction`, which is required when RediSearch is enabled
- The RediSearch module for vector indexing and similarity queries
- Access-key authentication for the local Python demonstrations

The RediSearch module must be enabled when the instance is created. It cannot be added later.

Provisioning can take several minutes. Wait for the instance to finish:

```powershell
az redisenterprise wait `
  --name $redisName `
  --resource-group $resourceGroup `
  --created
```

This command does not create another Redis instance. It pauses the PowerShell script until the earlier `az redisenterprise create` operation finishes and the instance reaches the `Succeeded` provisioning state:

- `--name $redisName` identifies the Redis instance to monitor.
- `--resource-group $resourceGroup` identifies the resource group containing the instance.
- `--created` waits until the instance has been created successfully.

## 4. Verify the instance and database

```powershell
az redisenterprise show `
  --name $redisName `
  --resource-group $resourceGroup `
  --query "{name:name, hostName:hostName, provisioningState:provisioningState, sku:sku.name}" `
  --output table

az redisenterprise database show `
  --cluster-name $redisName `
  --resource-group $resourceGroup `
  --query "{port:port, clientProtocol:clientProtocol, clusteringPolicy:clusteringPolicy, modules:modules[].name}" `
  --output json
```

The database should use the `EnterpriseCluster` policy and list `RediSearch` as an enabled module.

## 5. Retrieve the connection settings

Store the Redis host, port, and primary access key in environment variables for the current PowerShell session:

```powershell
$env:REDIS_HOST = az redisenterprise show `
  --name $redisName `
  --resource-group $resourceGroup `
  --query hostName `
  --output tsv

$env:REDIS_PORT = az redisenterprise database show `
  --cluster-name $redisName `
  --resource-group $resourceGroup `
  --query port `
  --output tsv

$env:REDIS_ACCESS_KEY = az redisenterprise database list-keys `
  --cluster-name $redisName `
  --resource-group $resourceGroup `
  --query primaryKey `
  --output tsv
```

Display the nonsecret connection values:

```powershell
Write-Output "Host: $env:REDIS_HOST"
Write-Output "Port: $env:REDIS_PORT"
```

Do not display, save, or commit the access key. These environment variables exist only in the current PowerShell session.

Test the connection with Azure CLI:

```powershell
az redisenterprise test-connection `
  --name $redisName `
  --resource-group $resourceGroup `
  --auth access-key `
  --access-key $env:REDIS_ACCESS_KEY
```

## 6. Configure the Python environment

Run these commands from `Demo\ai200-redis`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade redis numpy azure-identity openai
```

## 7. Demonstrate Redis data operations

Run:

```powershell
python .\data_operations.py
```

The script demonstrates:

- `SET` and `GET` with a string
- `HSET` and `HGETALL` with a course hash
- `SADD` and `SMEMBERS` with a set of unique categories
- `RPUSH` and `LRANGE` with an ordered list
- `INCR` with a counter
- `EXPIRE` and `TTL` with a temporary key
- `DELETE` to remove the script's earlier demonstration keys before each run

## 8. Configure access to the embedding model

The similarity-search script uses the existing `text-embedding-3-small` deployment to convert course descriptions and search text into vectors.

```powershell
$env:OPENAI_ENDPOINT = "https://oreilly-foundry-ai200.services.ai.azure.com/openai/v1/"
$env:EMBEDDING_DEPLOYMENT = "text-embedding-3-small"
```

The identity signed in through Azure CLI is used to call the embedding model. It must have the `Cognitive Services OpenAI User` role on `oreilly-foundry-ai200`.

## 9. Demonstrate semantic similarity search

Run:

```powershell
python .\similarity_search.py
```

At the `Semantic search:` prompt, enter:

```text
How do I protect access to a cloud application?
```

The script:

1. Creates a RediSearch `FLAT` vector index for 1,536-dimensional `FLOAT32` embeddings.
2. Generates embeddings for four course descriptions with `text-embedding-3-small`.
3. Stores each course and its embedding in a Redis hash.
4. Generates an embedding for the question.
5. Runs a three-nearest-neighbor cosine-distance query.
6. Displays each result and its cosine similarity.

The search should rank **Microsoft Entra ID and managed identities** highly even though the question does not use the course title.

RediSearch returns cosine distance. The script converts it to cosine similarity:

```text
similarity = 1 - distance
```

A similarity value closer to `1` means the vectors are more similar.

## 10. Try other searches

Run the script again and enter:

```text
I want to find information based on meaning instead of exact words
```

This should rank **Vector search and semantic retrieval** highly.

Another example is:

```text
I need a low-latency store for temporary application data
```

This should rank **Cache application data with Azure Managed Redis** highly.

## Troubleshooting

- **The module is missing:** RediSearch must be enabled during instance creation. Confirm that the database lists `RediSearch`.
- **The connection times out:** Confirm that public network access is enabled and that the host and port environment variables contain values.
- **Authentication fails:** Retrieve the current primary key again and keep `ssl=True` in the Python client.
- **Foundry returns an authorization error:** Confirm that the signed-in identity has the `Cognitive Services OpenAI User` role.
- **The vector dimension is rejected:** Confirm that `text-embedding-3-small` returns 1,536 values and that `VECTOR_DIMENSIONS` in the script is also `1536`.
- **The index already exists:** The script reuses the existing `course-vector-index`; this is expected on later runs.

## Microsoft Learn references

- [Azure Managed Redis documentation](https://learn.microsoft.com/azure/redis/)
- [What is Azure Managed Redis?](https://learn.microsoft.com/azure/redis/overview)
- [Azure CLI reference for `az redisenterprise`](https://learn.microsoft.com/cli/azure/redisenterprise)
- [Quickstart: Create a Python app with Azure Managed Redis](https://learn.microsoft.com/azure/redis/python-get-started)
- [Vector embeddings and vector search in Azure Managed Redis](https://learn.microsoft.com/azure/redis/overview-vector-similarity)
- [Use Redis modules with Azure Managed Redis](https://learn.microsoft.com/azure/redis/redis-modules)
- [Azure Managed Redis architecture and clustering policies](https://learn.microsoft.com/azure/redis/architecture)
- [Configure data persistence](https://learn.microsoft.com/azure/redis/how-to-persistence)
- [Use Microsoft Entra ID for authentication](https://learn.microsoft.com/azure/redis/entra-for-authentication)
- [Generate embeddings with Azure OpenAI](https://learn.microsoft.com/azure/foundry/openai/how-to/embeddings)
