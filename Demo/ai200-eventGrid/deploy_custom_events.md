# Demonstrate custom events with Azure Event Grid

This guide creates an Event Grid custom topic for low-stock inventory events. It deploys a Python webhook to Azure Container Apps, filters events before delivery, and demonstrates Event Grid retries by returning HTTP `503` twice for one event.

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

## Scenario: low-stock inventory notifications

The publisher sends inventory events to a custom topic. The event subscription delivers only events that meet all three filters:

- Event type is `Contoso.Inventory.StockChanged`.
- Subject begins with `/products/`.
- `data.remainingUnits` is less than or equal to `5`.

```text
custom_event_sender.py
          ↓
Event Grid custom topic
          ↓
Event type + subject + remainingUnits filters
          ↓
Container Apps webhook
          ├── HTTP 200: event accepted
          └── HTTP 503: Event Grid retries delivery
```

## Files used by this demonstration

| File | Purpose |
| --- | --- |
| `custom_event_sender.py` | Publishes five custom inventory events |
| `custom_event_receiver.py` | Validates the webhook, logs matching events, and simulates retryable failures |
| `Dockerfile` | Packages the webhook as a container |
| `requirements-custom-receiver.txt` | Lists the webhook's Python packages |

## 1. Prerequisites

- An Azure subscription
- Azure CLI
- Python 3.10 or later
- Permission to create Event Grid, Container Apps, and Container Registry resources

## 2. Sign in and register the resource providers

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.EventGrid
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

`az provider register --namespace Microsoft.EventGrid` registers the `Microsoft.EventGrid` resource provider in the currently selected Azure subscription. This enables the subscription to create and manage Event Grid resources such as custom topics, system topics, and event subscriptions. Registration is performed at the Azure subscription level, so it normally needs to be completed only once per subscription.

Verify Event Grid registration:

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
$topicName = "oreilly-ai200-inventory-$suffix"
$environmentName = "eg-env-$suffix"
$receiverName = "eg-receiver-$suffix"
$eventSubscriptionName = "low-stock-subscription"
```

## 4. Create the custom Event Grid topic

```powershell
az eventgrid topic create `
  --resource-group $resourceGroup `
  --name $topicName `
  --location $location `
  --input-schema eventgridschema
```

The custom topic supplies an HTTPS endpoint to which `custom_event_sender.py` publishes application-defined events.

## 5. Create the Container Apps environment

```powershell
az containerapp env create `
  --name $environmentName `
  --resource-group $resourceGroup `
  --location $location
```

## 6. Deploy the Python webhook

Run this command from `Demo\ai200-eventGrid`, where the `Dockerfile` is located:

```powershell
# Build the Dockerfile from the current directory.
# Push the resulting image to Azure Container Registry, creating a registry if needed.
# Create or update the container app in the selected Container Apps environment.
# Expose the application publicly and forward HTTPS traffic to container port 8000.
az containerapp up `
  --name $receiverName `
  --resource-group $resourceGroup `
  --environment $environmentName `
  --location $location `
  --source . `
  --ingress external `
  --target-port 8000
```

`az containerapp up --source .` builds the Docker image, pushes it to an Azure Container Registry, and deploys it to the Container Apps environment.

Keep one replica active so the in-memory retry counter stays in the same process:

```powershell
az containerapp update `
  --name $receiverName `
  --resource-group $resourceGroup `
  --min-replicas 1 `
  --max-replicas 1
```

Retrieve and test the public webhook URL:

```powershell
$receiverFqdn = az containerapp show `
  --name $receiverName `
  --resource-group $resourceGroup `
  --query properties.configuration.ingress.fqdn `
  --output tsv

$webhookUrl = "https://$receiverFqdn/events"
Invoke-WebRequest "https://$receiverFqdn/"
```

## 7. Create the filtered event subscription

Retrieve the custom topic resource ID:

```powershell
$topicId = az eventgrid topic show `
  --resource-group $resourceGroup `
  --name $topicName `
  --query id `
  --output tsv
```

Create the subscription:

```powershell
az eventgrid event-subscription create `
  --name $eventSubscriptionName `
  --source-resource-id $topicId `
  --endpoint $webhookUrl `
  --endpoint-type webhook `
  --included-event-types "Contoso.Inventory.StockChanged" `
  --subject-begins-with "/products/" `
  --advanced-filter data.remainingUnits NumberLessThanOrEquals 5 `
  --max-delivery-attempts 5 `
  --event-ttl 30
```

When the subscription is created, Event Grid sends a validation event to the webhook. `custom_event_receiver.py` returns the supplied validation code to prove that it controls the endpoint.

The retry policy permits up to five delivery attempts within a 30-minute event lifetime. A retryable response such as HTTP `503` causes Event Grid to schedule another delivery attempt.

## 8. Configure the local Python environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade azure-eventgrid
```

Set the topic endpoint and key for the current PowerShell session:

```powershell
$env:EVENTGRID_TOPIC_ENDPOINT = az eventgrid topic show `
  --resource-group $resourceGroup `
  --name $topicName `
  --query endpoint `
  --output tsv

$env:EVENTGRID_TOPIC_KEY = az eventgrid topic key list `
  --resource-group $resourceGroup `
  --name $topicName `
  --query key1 `
  --output tsv
```

The topic key is a secret. Keep it in the current PowerShell session and do not add it to source control.

## 9. Watch the webhook logs

Open another PowerShell terminal and run:

```powershell
az containerapp logs show `
  --name $receiverName `
  --resource-group $resourceGroup `
  --follow
```

Leave this command running while publishing the events. Press `Ctrl+C` after observing the deliveries.

## 10. Publish the custom events

From the original terminal, run:

```powershell
python .\custom_event_sender.py
```

The sender publishes five events:

| Event | Filter result | Expected delivery |
| --- | --- | --- |
| Laptop stock changed, 3 units | Matches all filters | Delivered once |
| Monitor stock changed, 25 units | Fails the quantity filter | Not delivered |
| Mouse price changed, 2 units | Fails the event-type filter | Not delivered |
| Keyboard stock changed, 2 units | Matches all filters | Returns `503` twice, then succeeds |
| Supplier adapter stock changed, 1 unit | Fails the subject filter | Not delivered |

## 11. Observe filtering and retries

The webhook logs should show the laptop event once. The monitor, mouse, and supplier events should not appear because Event Grid removes them before delivery.

The keyboard event should appear three times:

```text
Delivery attempt 1: Keyboard 400 has 2 units remaining.
Returning HTTP 503 to trigger an Event Grid retry.

Delivery attempt 2: Keyboard 400 has 2 units remaining.
Returning HTTP 503 to trigger an Event Grid retry.

Delivery attempt 3: Keyboard 400 has 2 units remaining.
Accepted event <event-id>.
```

Retries use a backoff schedule, so the three attempts are not immediate. Event Grid delivery is at least once, so production subscribers should use the event ID to recognize duplicate deliveries.

## Troubleshooting

- **Subscription validation fails:** Confirm that `$webhookUrl` ends with `/events` and that the container app is running.
- **No events appear in the logs:** Confirm that the event subscription provisioning state is `Succeeded` and that the sender uses the endpoint and key for the same topic.
- **The retry event succeeds immediately:** Confirm that only one replica is configured and that `simulateRetry` is `True` for the keyboard event.
- **The source deployment fails:** Run the `az containerapp up` command again from the directory containing the `Dockerfile`.

## Microsoft Learn references

- [Custom topics in Azure Event Grid](https://learn.microsoft.com/azure/event-grid/custom-topics)
- [Publish events to custom topics](https://learn.microsoft.com/azure/event-grid/post-to-custom-topic)
- [Filter events in Azure Event Grid](https://learn.microsoft.com/azure/event-grid/event-filtering)
- [Event delivery and retry](https://learn.microsoft.com/azure/event-grid/delivery-and-retry)
- [Validate webhook endpoints with the Event Grid schema](https://learn.microsoft.com/azure/event-grid/end-point-validation-event-grid-events-schema)
- [Azure Event Grid client library for Python](https://learn.microsoft.com/python/api/overview/azure/event-grid)
- [Deploy Azure Container Apps from source](https://learn.microsoft.com/azure/container-apps/containerapp-up)
