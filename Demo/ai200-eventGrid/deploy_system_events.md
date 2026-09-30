# Demonstrate system events with Azure Event Grid

This guide demonstrates a system event generated automatically by Azure Blob Storage. When a text file is uploaded, Azure Storage publishes a `Microsoft.Storage.BlobCreated` event. Event Grid filters the event and places it in an Azure Storage queue for a Python receiver to process.

## System events and custom events

| | System events | Custom events |
| --- | --- | --- |
| Producer | An Azure service | Your application or script |
| Event definition | Defined by Microsoft | Defined by you |
| Publishing | Azure publishes automatically | Your code sends the event |
| Example | A blob was created in Storage | Product inventory became low |
| Topic type | System topic | Custom topic |
| Payload | Uses the Azure service's event schema | Contains your own JSON data |

A system event is generated automatically by an Azure service. A custom event represents an application or business event whose type, subject, and data are defined by the application.

```text
System event: Azure service → Event Grid → Subscriber
Custom event: Your application → Custom Event Grid topic → Subscriber
```

## Scenario: process uploaded text files

```text
blob_upload.py
      ↓ uploads .txt and .json blobs
Azure Blob Storage
      ↓ automatically publishes BlobCreated system events
Event Grid subscription
      ↓ keeps only events whose subject ends with .txt
Azure Storage queue
      ↓
system_event_receiver.py
```

The application does not publish the system event. Azure Storage creates it automatically after the blob upload succeeds.

## Files used by this demonstration

| File | Purpose |
| --- | --- |
| `blob_upload.py` | Uploads one `.txt` blob and one `.json` blob |
| `system_event_receiver.py` | Reads the delivered `.txt` BlobCreated event from Queue Storage |

## 1. Prerequisites

- An Azure subscription
- Azure CLI
- Python 3.10 or later

## 2. Sign in and register Event Grid

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

az provider register --namespace Microsoft.EventGrid
```

`az provider register --namespace Microsoft.EventGrid` registers the `Microsoft.EventGrid` resource provider in the currently selected Azure subscription. This enables the subscription to create and manage Event Grid resources such as custom topics, system topics, and event subscriptions. Registration is performed at the Azure subscription level, so it normally needs to be completed only once per subscription.

Verify registration:

```powershell
az provider show `
  --namespace Microsoft.EventGrid `
  --query registrationState `
  --output tsv
```

Continue when the result is `Registered`.

## 3. Define the resource names

```powershell
$resourceGroup = "AI-200"
$location = "canadacentral"
$suffix = Get-Random -Minimum 100000 -Maximum 999999
$storageAccount = "ai200events$suffix"
$containerName = "uploads"
$queueName = "blob-events"
$eventSubscriptionName = "text-blob-created"
```

Storage account names must be globally unique, lowercase, and contain only letters and numbers.

## 4. Create the Storage account

```powershell
az storage account create `
  --name $storageAccount `
  --resource-group $resourceGroup `
  --location $location `
  --sku Standard_LRS `
  --kind StorageV2 `
  --allow-blob-public-access false
```

`StorageV2` supports Blob Storage integration with Event Grid.

## 5. Retrieve the connection string

```powershell
$env:STORAGE_CONNECTION_STRING = az storage account show-connection-string `
  --name $storageAccount `
  --resource-group $resourceGroup `
  --query connectionString `
  --output tsv

$env:BLOB_CONTAINER_NAME = $containerName
$env:EVENT_QUEUE_NAME = $queueName
```

The connection string is a secret. Keep it in the current PowerShell session and do not add it to source control.

## 6. Create the blob container and event queue

```powershell
az storage container create `
  --name $containerName `
  --connection-string $env:STORAGE_CONNECTION_STRING

az storage queue create `
  --name $queueName `
  --connection-string $env:STORAGE_CONNECTION_STRING
```

The `uploads` container is the event source. The `blob-events` queue is the event handler where Event Grid delivers matching events.

## 7. Create the filtered system-event subscription

Retrieve the source and destination resource IDs:

```powershell
$storageId = az storage account show `
  --name $storageAccount `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

$queueId = "$storageId/queueServices/default/queues/$queueName"
```

Create an event subscription on the Storage account:

```powershell
az eventgrid event-subscription create `
  --name $eventSubscriptionName `
  --source-resource-id $storageId `
  --endpoint-type storagequeue `
  --endpoint $queueId `
  --included-event-types Microsoft.Storage.BlobCreated `
  --subject-begins-with "/blobServices/default/containers/$containerName/blobs/" `
  --subject-ends-with ".txt"
```

This subscription accepts only `BlobCreated` events from the selected container whose subjects end in `.txt`. Event Grid creates and manages the system topic associated with the Storage account.

## 8. Configure the Python environment

Run these commands from `Demo\ai200-eventGrid`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade azure-eventgrid azure-storage-blob azure-storage-queue
```

## 9. Upload the sample blobs

```powershell
python .\blob_upload.py
```

The script uploads:

- A `.txt` blob that matches the event-subscription filter.
- A `.json` blob that produces a BlobCreated system event but is filtered out before queue delivery.

## 10. Receive the system event

```powershell
python .\system_event_receiver.py
```

Event delivery is asynchronous. The receiver checks the queue for up to 60 seconds, displays the event, and deletes the queue message after successful processing.

Event Grid stores the event body in Queue Storage using Base64 encoding. The receiver configures `TextBase64DecodePolicy` so the Azure Storage SDK decodes the message before `EventGridEvent.from_json()` parses it.

The result should include:

```text
Event type: Microsoft.Storage.BlobCreated
Subject: /blobServices/default/containers/uploads/blobs/notes/event-grid-<timestamp>.txt
```

Only the `.txt` event should be present. The `.json` event was created by Azure Storage but rejected by the subscription's subject-suffix filter.

## 11. View the system topic and subscription

List the Storage account's event subscriptions:

```powershell
az eventgrid event-subscription list `
  --source-resource-id $storageId `
  --output table
```

You can also open the Storage account in the Azure portal and select **Events** to view the system-topic subscription.

## Troubleshooting

- **No event arrives:** Wait briefly and run `system_event_receiver.py` again because delivery is asynchronous.
- **Both uploads appear in the queue:** Confirm that the event subscription contains `--subject-ends-with ".txt"`.
- **Storage authentication fails:** Retrieve the connection string again in the current PowerShell session.
- **Event subscription creation fails:** Confirm that Event Grid provider registration has reached `Registered`.
- **`Failed to load JSON content from the object`:** Confirm that `system_event_receiver.py` configures `TextBase64DecodePolicy` on `QueueClient`.

## Microsoft Learn references

- [Azure Event Grid system topics](https://learn.microsoft.com/azure/event-grid/system-topics)
- [Azure Blob Storage as an Event Grid source](https://learn.microsoft.com/azure/event-grid/event-schema-blob-storage)
- [Send Blob Storage events to a web endpoint](https://learn.microsoft.com/azure/storage/blobs/storage-blob-event-quickstart)
- [Storage queues as Event Grid handlers](https://learn.microsoft.com/azure/event-grid/handler-storage-queues)
- [Event filtering in Azure Event Grid](https://learn.microsoft.com/azure/event-grid/event-filtering)
- [Azure Queue Storage client library for Python](https://learn.microsoft.com/azure/storage/queues/storage-python-how-to-use-queue-storage)
- [Azure Blob Storage client library for Python](https://learn.microsoft.com/azure/storage/blobs/storage-quickstart-blobs-python)
