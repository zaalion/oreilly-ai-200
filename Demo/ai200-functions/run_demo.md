# Run the Cosmos DB change feed function

## What is a Cosmos DB change feed?

The Azure Cosmos DB change feed is a persistent, ordered record of changes made to documents in a container. An application can read the feed and react when documents are created or updated. Common uses include event-driven processing, materialized views, cache updates, search indexing, and data synchronization.

The change feed is enabled automatically for Azure Cosmos DB containers. This demo uses an Azure Functions Cosmos DB trigger to monitor the `CourseCatalog/courses` container in `oreilly-ai200-cosmos-266162`. The trigger runs after a course document is inserted or updated. In the default latest-version mode used here, deleting a document does not produce an event for the function.

The trigger also uses a `leases` container. Leases store checkpoints and coordinate processing so the function knows which changes it has already handled. The function creates this container automatically if it does not exist.

## 1. Prerequisites

Install or verify the following tools:

- .NET 9 SDK
- Azure Functions Core Tools 4
- Azurite, either through the VS Code Azurite extension or the `azurite` command
- Azure CLI
- An Azure account with access to resource group `AI-200`

Check the installed versions:

```powershell
dotnet --version
func --version
az version
```

The function uses the .NET isolated worker model, which is the Azure Functions execution model that supports .NET 9.

## 2. Open the project

```powershell
cd C:\Data\Repo\oreilly-ai-200\Demo\ai200-functions
```

The change feed trigger is implemented in `CourseChangeFeed.cs`. It monitors:

| Setting | Value |
|---|---|
| Cosmos DB account | `oreilly-ai200-cosmos-266162` |
| Database | `CourseCatalog` |
| Container | `courses` |
| Lease container | `leases` |

The `leases` container is used internally by the Azure Functions Cosmos DB trigger. It stores checkpoints that record how far the function has processed the change feed. This prevents previously processed changes from being handled again after the function restarts. It also coordinates work when multiple function instances are running. The function creates this container automatically because `CreateLeaseContainerIfNotExists` is set to `true`.

## 3. Sign in and select the subscription

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"
```

Set the values used by the remaining commands:

```powershell
$resourceGroup = "AI-200"
$cosmosAccount = "oreilly-ai200-cosmos-266162"
```

## 4. Verify the existing Cosmos DB resources

```powershell
az cosmosdb show `
  --name $cosmosAccount `
  --resource-group $resourceGroup `
  --query "{name:name,location:location}" `
  --output table

az cosmosdb sql database show `
  --account-name $cosmosAccount `
  --resource-group $resourceGroup `
  --name "CourseCatalog" `
  --output table

az cosmosdb sql container show `
  --account-name $cosmosAccount `
  --resource-group $resourceGroup `
  --database-name "CourseCatalog" `
  --name "courses" `
  --query "{name:name,partitionKey:resource.partitionKey.paths[0]}" `
  --output table
```

The partition-key output should be `/category`.

## 5. Start local storage with Azurite

The function app runs locally. Azure Functions still requires a storage service for host operations, so this demo uses the local Azurite emulator instead of deploying an Azure Functions app or creating an Azure Storage account.

If Azurite is not installed, install it once:

```powershell
npm install --global azurite
```

From the project folder, start Azurite in a separate terminal and leave it running:

```powershell
azurite --silent --location .azurite --debug .azurite\debug.log
```

## 6. Set the local connection settings

Run these commands in the same PowerShell terminal that will run the function:

```powershell
$env:CosmosConnection = az cosmosdb keys list `
  --name $cosmosAccount `
  --resource-group $resourceGroup `
  --type connection-strings `
  --query "connectionStrings[0].connectionString" `
  --output tsv

$env:AzureWebJobsStorage = "UseDevelopmentStorage=true"
```

Confirm that both variables contain values without displaying their secrets:

```powershell
"Cosmos connection configured: $(-not [string]::IsNullOrWhiteSpace($env:CosmosConnection))"
"Functions storage configured: $(-not [string]::IsNullOrWhiteSpace($env:AzureWebJobsStorage))"
```

Do not commit connection strings to Git. The project ignores `local.settings.json` for this reason.

## 7. Restore and build the function app

```powershell
dotnet restore
dotnet build
```

The build should finish with `Build succeeded`.

## 8. Start the function locally

```powershell
func start
```

If Azure Functions Core Tools asks you to select a worker runtime, choose:

```text
dotnet (isolated worker model)
```

This project uses .NET 9, which requires the isolated-worker model. Do not select `dotnet (in-process model)`.

Keep this terminal open. The Functions host should list a function named `CourseChangeFeed` and wait for changes from Cosmos DB.

On its first connection, the trigger creates the `leases` container in `CourseCatalog`. Existing unprocessed documents may appear in the initial console output while the first checkpoint is established.

## 9. Add a document to Cosmos DB

1. Open the [Azure portal](https://portal.azure.com/).
2. Open the Azure Cosmos DB account `oreilly-ai200-cosmos-266162`.
3. Select **Data Explorer**.
4. Expand **CourseCatalog**, expand **courses**, and select **Items**.
5. Select **New Item**.
6. Replace the editor contents with the following document:

```json
{
  "id": "course-change-feed-001",
  "category": "AI",
  "title": "Cosmos DB change feed",
  "description": "Use the Azure Cosmos DB change feed to react to inserts and updates."
}
```

7. Select **Save**.

The `category` property is required because the `courses` container uses `/category` as its partition key.

## 10. Observe the function logs

Return to the terminal running `func start`. The console should show a successful invocation with output similar to:

```text
Executing 'Functions.CourseChangeFeed'
Course change feed triggered with 1 document(s).
Changed course: Id=course-change-feed-001, Title=Cosmos DB change feed, Category=AI
Document JSON: { ... }
Executed 'Functions.CourseChangeFeed' (Succeeded)
```

The exact host messages and invocation identifiers may differ.

## 11. Demonstrate an update event

In Data Explorer, open `course-change-feed-001`, change its title, and select **Update**:

```json
"title": "Updated Cosmos DB change feed course"
```

The function runs again because the default change feed includes both inserts and updates.

## 12. Stop the local host

In the terminal running the function, press `Ctrl+C`.

The checkpoint remains in the `leases` container, so restarting the function continues from the last processed change rather than intentionally replaying every document.

## Troubleshooting

### The function is not listed

Run `dotnet build` and correct any build errors before running `func start` again.

### `CosmosConnection` is missing

Set `$env:CosmosConnection` again in the same terminal used to run `func start`.

### The host reports an `AzureWebJobsStorage` error

Confirm that Azurite is running, and then set `$env:AzureWebJobsStorage = "UseDevelopmentStorage=true"` again in the terminal used to run `func start`.

### The document is saved but no invocation appears

Confirm that the document was saved in `CourseCatalog/courses`, that it contains the `/category` partition-key value, and that the account connection string belongs to `oreilly-ai200-cosmos-266162`.

## .NET execution models in Azure Functions

Azure Functions supports two execution models for .NET function apps:

### Isolated-worker model

In the isolated-worker model, the .NET application runs in a separate process from the Azure Functions host. The application has its own startup code in `Program.cs`, uses standard .NET dependency injection, and has more control over configuration and middleware.

This project uses the isolated-worker model because it targets .NET 9. In the Core Tools runtime-selection menu, it appears as:

```text
dotnet (isolated worker model)
```

### In-process model

In the in-process model, the function code runs inside the same process as the Azure Functions host. The application is more tightly coupled to the host and its supported .NET and dependency versions. In the Core Tools runtime-selection menu, it appears as:

```text
dotnet (in-process model)
```

### Key differences

| Area | Isolated-worker model | In-process model |
|---|---|---|
| Process | Function code runs in a separate process | Function code runs inside the Functions host process |
| .NET support | Supports newer .NET versions, including .NET 9 | Limited to the .NET versions supported by the in-process host |
| Startup | Uses a standard `Program.cs` entry point | Startup is managed primarily by the Functions host |
| Dependency injection | Uses standard .NET dependency injection | Uses the Functions in-process dependency-injection model |
| Middleware | Supports custom middleware | Does not use the isolated-worker middleware pipeline |
| Project choice | Select `dotnet (isolated worker model)` | Select `dotnet (in-process model)` |

For this demo, select the **isolated-worker model**.

## Azure Functions triggers and bindings

A **trigger** defines the event that starts a function. Every Azure Function must have exactly one trigger. Examples include an HTTP request, a timer schedule, a Service Bus message, or a change in an Azure Cosmos DB container.

A **binding** connects a function to another resource without requiring the function to contain all the connection and client-management code. Bindings are expressed through attributes in .NET function code:

- An **input binding** supplies data to the function.
- An **output binding** sends data from the function to another service.
- A trigger is a special type of input binding because it both starts the function and supplies the event data.

In `CourseChangeFeed.cs`, this attribute is both the trigger and the input binding:

```csharp
[CosmosDBTrigger(
    databaseName: "CourseCatalog",
    containerName: "courses",
    Connection = "CosmosConnection",
    LeaseContainerName = "leases",
    CreateLeaseContainerIfNotExists = true)]
IReadOnlyList<JsonElement> changedDocuments
```

The parts work as follows:

| Code | Purpose |
|---|---|
| `[Function(nameof(CourseChangeFeed))]` | Marks the method as an Azure Function and gives the function its name. It is not the trigger. |
| `[CosmosDBTrigger(...)]` | Defines the Cosmos DB change feed event that starts the function. |
| `databaseName` and `containerName` | Identify the monitored `CourseCatalog/courses` container. |
| `Connection` | Names the configuration setting that contains the Cosmos DB connection string. |
| `LeaseContainerName` | Identifies the container used to store change-feed checkpoints. |
| `changedDocuments` | Receives the documents supplied by the input binding for the current invocation. |

This function does not have an output binding. It processes the input documents and writes messages to the local console through `ILogger`. Logging is normal application code and is not an Azure Functions output binding.

## Microsoft Learn references

- [Change feed in Azure Cosmos DB](https://learn.microsoft.com/azure/cosmos-db/change-feed)
- [Azure Functions triggers and bindings concepts](https://learn.microsoft.com/azure/azure-functions/functions-triggers-bindings)
- [Azure Functions triggers and bindings for Azure Cosmos DB](https://learn.microsoft.com/azure/azure-functions/functions-bindings-cosmosdb-v2)
- [Azure Cosmos DB trigger for Azure Functions](https://learn.microsoft.com/azure/azure-functions/functions-bindings-cosmosdb-v2-trigger)
- [Use the Azure Cosmos DB change feed with Azure Functions](https://learn.microsoft.com/azure/cosmos-db/change-feed-functions)
- [.NET isolated worker model for Azure Functions](https://learn.microsoft.com/azure/azure-functions/dotnet-isolated-process-guide)
- [Troubleshoot the Azure Cosmos DB change feed processor](https://learn.microsoft.com/azure/cosmos-db/troubleshoot-changefeed-functions)
