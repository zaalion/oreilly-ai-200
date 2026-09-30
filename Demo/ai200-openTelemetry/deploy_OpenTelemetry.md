# Deploy the .NET 9 OpenTelemetry telemetry demo

## What is OpenTelemetry?

OpenTelemetry is an open standard and collection of APIs, SDKs, instrumentation libraries, and exporters for producing and sending telemetry. It provides a vendor-neutral way to instrument an application and then export its telemetry to systems such as Azure Monitor, Jaeger, Zipkin, or an OpenTelemetry Collector.

OpenTelemetry supports three primary telemetry signals:

- **Traces** follow a request as it moves through operations and services.
- **Metrics** represent numeric measurements collected over time.
- **Logs** record timestamped application events.

This demonstration shows how the OpenTelemetry .NET SDK produces and exports all three signals. The examples use:

- `ActivitySource` and `Activity` for traces.
- `Meter` and `Counter<T>` for metrics.
- `ILogger<T>` with the OpenTelemetry logging provider for logs.

One selection of **Run telemetry operation** executes one checkout in this application and produces related trace spans, a checkout metric measurement, and a structured checkout log.

## Traces, spans, and context

A **trace** represents one end-to-end operation. A trace contains one or more **spans**. Each span represents a unit of work and records information such as its name, duration, status, attributes, and parent span.

All spans in the same trace share a trace ID. Parent and child identifiers describe their relationships. Trace context is propagated between services so independently created server and client spans can be correlated into one distributed trace.

In .NET, `ActivitySource` represents an OpenTelemetry tracer and `Activity` represents a span.

## What the OpenTelemetry SDK does in this demo

| SDK component | Purpose in this application |
|---|---|
| Resource | Identifies the service as `ai200-opentelemetry-demo`. |
| ASP.NET Core instrumentation | Automatically creates server spans for incoming HTTP requests. |
| HttpClient instrumentation | Automatically creates client spans and propagates trace context for outgoing HTTP requests. |
| `ActivitySource` | Creates custom spans for the checkout business operation. |
| `Meter` | Creates custom measurements for completed checkout operations. |
| `ILogger` | Creates structured, timestamped checkout events. |
| Console exporters | Print spans, metric data points, and log records to the local console. |
| Azure Monitor exporters | Send traces, metrics, and logs to Application Insights when its connection string is configured. |

## Trace produced by the demonstration

Selecting **Run telemetry operation** produces related spans similar to:

```text
POST /
└── ProcessCheckout
    ├── ValidateOrder
    └── CheckInventory
        └── HTTP GET /api/inventory/ai-course
            └── GET /api/inventory/{item}
```

The first and last server spans and the outgoing HTTP client span are created automatically. `ProcessCheckout`, `ValidateOrder`, and `CheckInventory` are custom spans created in `CheckoutTraceService.cs`.

## Metric produced by the demonstration

`CheckoutTraceService.cs` defines a `Meter` and counter in the same class that creates the custom spans:

```csharp
using System.Diagnostics.Metrics;

public const string MeterName = "AI200.OpenTelemetry.Checkout";

private static readonly Meter Meter = new(MeterName);
private static readonly Counter<long> CheckoutsCompleted =
    Meter.CreateCounter<long>(
        name: "demo.checkout.completed",
        unit: "{checkout}",
        description: "Number of completed checkout operations");
```

The same `RunAsync` method records the measurement after the checkout succeeds:

```csharp
CheckoutsCompleted.Add(
    1,
    new KeyValuePair<string, object?>("demo.item", "ai-course"));
```

Each successful selection of **Run telemetry operation** increments `demo.checkout.completed` by one. The `demo.item` attribute allows the measurements to be grouped or filtered by item.

## Log produced by the demonstration

The same `CheckoutTraceService` receives `ILogger<CheckoutTraceService>` alongside its `HttpClient`:

```csharp
private readonly HttpClient _httpClient;
private readonly ILogger<CheckoutTraceService> _logger;

public CheckoutTraceService(
    HttpClient httpClient,
    ILogger<CheckoutTraceService> logger)
{
    _httpClient = httpClient;
    _logger = logger;
}
```

`RunAsync` writes a structured log while `checkoutActivity` is still active:

```csharp
_logger.LogInformation(
    "Checkout {OrderId} completed for {Item}",
    orderId,
    "ai-course");
```

The log record includes a timestamp, severity, category, formatted message, and structured `OrderId` and `Item` values. Because it is written while the checkout activity is active, the OpenTelemetry logging provider also attaches the current trace ID and span ID for correlation.

## 1. Prerequisites

Install or verify:

- .NET 9 SDK
- Azure CLI
- An Azure account that can create Azure Monitor and App Service resources

```powershell
dotnet --version
az version
```

## 2. Open the project

```powershell
cd C:\Data\Repo\oreilly-ai-200\Demo\ai200-openTelemetry
```

## 3. Restore and build the application

```powershell
dotnet restore
dotnet build
```

The build should finish with `Build succeeded`.

## 4. Run all three telemetry signals locally

```powershell
dotnet run
```

### Create and inspect the telemetry

1. Keep the terminal running `dotnet run` visible.
2. Open `http://localhost:5200` if the browser does not open automatically.
3. Select **Run telemetry operation**.
4. Wait for the page to display **Telemetry created successfully**.
5. Copy the order ID and 32-character trace ID displayed on the page.
6. Return to the terminal and find the following output from that one operation:
   - Trace records with the displayed `TraceId`, including `ProcessCheckout`, `ValidateOrder`, and `CheckInventory`.
   - A metric record whose `Name` is `demo.checkout.completed` and whose value is `1`.
   - A log record containing `Checkout <order-id> completed for ai-course`.
7. In the trace records, compare `SpanId` and `ParentSpanId` to follow the parent-child relationships.
8. In the checkout log, confirm that `TraceId` matches the trace ID displayed on the page.

Run the operation more than once to demonstrate that each request receives a different trace ID, the checkout counter increases, and each checkout log is correlated with its active trace.

The page displays the order ID and trace ID. The three console exporters print completed spans, metric data points, and log records from the same application.

Useful span fields include:

| Field | Meaning |
|---|---|
| `TraceId` | Correlates every span belonging to the same end-to-end operation. |
| `SpanId` | Uniquely identifies one span within a trace. |
| `ParentSpanId` | Identifies the parent that caused this span. |
| `ActivitySourceName` | Identifies the instrumentation or custom source that created the span. |
| `Activity.Duration` | Shows how long the operation took. |
| `StatusCode` | Indicates whether the operation succeeded or failed. |
| Tags | Store searchable attributes such as `demo.order.id`. |
| Events | Record meaningful moments such as `checkout.completed`. |

Press `Ctrl+C` to stop the local website.

## 5. Sign in and define Azure deployment values

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

$resourceGroup = "AI-200"
$location = "eastus"
$suffix = Get-Random -Minimum 100000 -Maximum 999999
$workspaceName = "oreilly-ai200-otel-law-$suffix"
$appInsightsName = "oreilly-ai200-otel-ai-$suffix"
$planName = "oreilly-ai200-otel-s1-plan"
$appName = "oreilly-ai200-otel-web-$suffix"
```

## 6. Register the resource providers

```powershell
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.Web
```

These providers allow the subscription to create Log Analytics, Application Insights, and App Service resources. Registration is normally required only once per subscription.

Check their status:

```powershell
az provider show --namespace Microsoft.OperationalInsights --query registrationState --output tsv
az provider show --namespace Microsoft.Insights --query registrationState --output tsv
az provider show --namespace Microsoft.Web --query registrationState --output tsv
```

Continue when all commands return `Registered`.

## 7. Create a Log Analytics workspace

```powershell
az group create `
  --name $resourceGroup `
  --location $location

az monitor log-analytics workspace create `
  --workspace-name $workspaceName `
  --resource-group $resourceGroup `
  --location $location

$workspaceId = az monitor log-analytics workspace show `
  --workspace-name $workspaceName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv
```

The workspace stores the telemetry collected by the workspace-based Application Insights resource.

## 8. Create Application Insights

The `az monitor app-insights` command group belongs to the `application-insights` Azure CLI extension. Current Azure CLI versions normally install it automatically on first use. If automatic installation is disabled, install it explicitly:

```powershell
az extension add --name application-insights --upgrade
```

Create a workspace-based Application Insights resource:

```powershell
az monitor app-insights component create `
  --app $appInsightsName `
  --resource-group $resourceGroup `
  --location $location `
  --kind web `
  --application-type web `
  --workspace $workspaceId
```

Read its connection string:

```powershell
$applicationInsightsConnectionString = az monitor app-insights component show `
  --app $appInsightsName `
  --resource-group $resourceGroup `
  --query connectionString `
  --output tsv
```

## 9. Export local telemetry to Application Insights

At this point, the application is still running locally through `dotnet run`. It has not been deployed to Azure. The connection string tells the locally running application where to send its telemetry; it does not deploy or host the application.

This step verifies that traces, metrics, and logs can reach Application Insights before the application is deployed. The application itself is published and deployed to Azure App Service later in step 15.

Set the connection string in the current terminal and restart the website:

```powershell
$env:APPLICATIONINSIGHTS_CONNECTION_STRING = $applicationInsightsConnectionString
dotnet run
```

Select **Run telemetry operation** several times. The application continues to export all three signals to the console and now also sends them to Application Insights.

Telemetry ingestion can take several minutes. The browser request does not wait for the Azure Monitor portal to display the trace.

## 10. Find traces, metrics, and logs in Application Insights

### Find a trace

1. Open the Azure portal.
2. Open the Application Insights resource stored in `$appInsightsName`.
3. In the resource menu, select **Logs** under **Monitoring**.
4. If the **Observability Agent** chat appears, turn off the **Agent** toggle in the upper-right corner to display the KQL query editor.
5. Select **New Query** if an empty query editor is not already open.
6. If the query mode is set to **Simple**, change it to **KQL mode**.
7. Set the time range to **Last 30 minutes**.
8. Replace `<trace-id-from-page>` with the trace ID displayed by the application, paste the query into the editor, and select **Run**:

```kusto
union requests, dependencies
| where operation_Id == "<trace-id-from-page>"
| project timestamp, itemType, name, operation_Id, id, operation_ParentId, duration, success
| order by timestamp asc
```

Every returned row should have the displayed trace ID in `operation_Id`. Application Insights represents server spans as requests and internal or client spans as dependencies.

If the query displays **No results found**:

1. Confirm that the trace ID came from an operation run after the application was restarted in step 9 with `APPLICATIONINSIGHTS_CONNECTION_STRING` set. Telemetry created by the earlier console-only run was not sent to Application Insights.
2. Select **Run telemetry operation** again and copy the new trace ID.
3. Wait several minutes for ingestion, then rerun the query.
4. Change the portal time range from **Last 30 minutes** to **Last 24 hours** and try again.
5. Remove the `operation_Id` filter temporarily and run this query to check whether the resource has received any recent trace data:

```kusto
union requests, dependencies
| project timestamp, itemType, name, operation_Id, id, operation_ParentId, duration, success
| order by timestamp desc
| take 50
```

If this broader query returns rows, copy an `operation_Id` from the results and use it in the filtered query. If it returns no rows, stop the local application and verify the connection string before restarting it:

```powershell
$env:APPLICATIONINSIGHTS_CONNECTION_STRING
```

The command must display a nonempty connection string. Then run `dotnet run`, create a new telemetry operation, wait several minutes, and query for its new trace ID.

To view the graphical end-to-end transaction:

1. Select **Search** under **Investigate** in the Application Insights resource menu. In some older portal versions, this entry is named **Transaction search**.
2. If **Search** is not in the resource menu, open the resource's **Overview** page and select **Search** from the command bar.
3. Set the time range to include the operation.
4. Select the recent `POST` request created by the demo.
5. Open its end-to-end transaction details to view the server, custom, and dependency spans.

The **Logs** query is sufficient for completing the demo; the **Search** view is an optional graphical representation of the same correlated operation.

### Find the custom metric

1. In the same Application Insights resource, select **Metrics**.
2. Set **Metric Namespace** to `azure.applicationinsights` or the namespace containing the custom metric.
3. Select the `demo.checkout.completed` metric.
4. Set the aggregation to **Sum** and the time range to include the operations just run.

You can also select **Logs** and run:

```kusto
customMetrics
| where timestamp > ago(30m)
| where name == "demo.checkout.completed"
| project timestamp, name, value, valueSum, valueCount, customDimensions
| order by timestamp desc
```

The values can be aggregated during export, so one row can represent more than one recorded measurement. `valueSum` and `valueCount` show the total and number of measurements in that aggregation interval.

### Find a checkout log

Copy the order ID displayed by the website, replace `<order-id-from-page>`, and run:

```kusto
traces
| where timestamp > ago(30m)
| where message contains "<order-id-from-page>"
| project timestamp, message, severityLevel, operation_Id, operation_ParentId, customDimensions
| order by timestamp desc
```

Confirm that `operation_Id` matches the trace ID displayed for the same checkout. This connects the log to the request and dependency records returned by the earlier trace query.

## 11. Confirm that App Service supports .NET 9

```powershell
az webapp list-runtimes --os linux | Select-String "DOTNETCORE"
```

Confirm that `DOTNETCORE:9.0` appears.

## 12. Create an S1 App Service plan

```powershell
az appservice plan create `
  --name $planName `
  --resource-group $resourceGroup `
  --location $location `
  --sku S1 `
  --is-linux
```

## 13. Create the App Service web app

```powershell
az webapp create `
  --name $appName `
  --resource-group $resourceGroup `
  --plan $planName `
  --runtime "DOTNETCORE:9.0"

az webapp update `
  --name $appName `
  --resource-group $resourceGroup `
  --https-only true
```

This creates a code-based Linux web app. No container is used.

## 14. Configure the Azure Monitor exporter

```powershell
az webapp config appsettings set `
  --name $appName `
  --resource-group $resourceGroup `
  --settings "APPLICATIONINSIGHTS_CONNECTION_STRING=$applicationInsightsConnectionString"
```

At application startup, `Program.cs` detects this setting and adds the Azure Monitor trace, metric, and log exporters. Without it, the application uses only the three console exporters.

The application uses the OpenTelemetry SDK directly. Do not separately enable App Service Application Insights automatic instrumentation for this demo, because doing so can produce duplicate telemetry.

## 15. Publish and deploy the website

```powershell
dotnet publish .\OpenTelemetryWeb.csproj `
  --configuration Release `
  --output .\publish

Compress-Archive `
  -Path .\publish\* `
  -DestinationPath .\opentelemetry-web.zip `
  -Force

az webapp deploy `
  --name $appName `
  --resource-group $resourceGroup `
  --src-path .\opentelemetry-web.zip `
  --type zip `
  --clean true
```

## 16. Open the deployed website and create telemetry

```powershell
$hostName = az webapp show `
  --name $appName `
  --resource-group $resourceGroup `
  --query defaultHostName `
  --output tsv

"https://$hostName"
```

Open the URL and create all three signals with one operation:

1. Select **Run telemetry operation**.
2. Copy the trace ID and order ID displayed on the page.
3. Wait several minutes for telemetry ingestion.
4. Open the Application Insights resource in the Azure portal.
5. Select **Logs** under **Monitoring**.
6. To locate the exact trace, replace `<trace-id-from-page>` and run:

```kusto
union requests, dependencies
| where operation_Id == "<trace-id-from-page>"
| project timestamp, itemType, name, operation_Id, id, operation_ParentId, duration, success
| order by timestamp asc
```

7. Confirm that the results contain the automatic HTTP spans and custom checkout spans.
8. Optionally select **Search** under **Investigate**, open the recent `POST` request, and view the graphical end-to-end transaction.
9. Run the `customMetrics` query from step 10 and confirm that `demo.checkout.completed` was recorded.
10. Run the `traces` query from step 10 with the displayed order ID and confirm that the checkout log has the displayed trace ID as its `operation_Id`.

Repeat the operation several times to produce more correlated telemetry from the same application.

## 17. View the application console output

The console exporters for all three signals remain enabled after deployment. Enable App Service application logging and stream their output:

```powershell
az webapp log config `
  --name $appName `
  --resource-group $resourceGroup `
  --application-logging filesystem `
  --level information

az webapp log tail `
  --name $appName `
  --resource-group $resourceGroup
```

Run another telemetry operation while the log stream is open. Look for its spans, the `demo.checkout.completed` metric, and the structured checkout log. Press `Ctrl+C` to stop streaming.

## How the SDK is configured

The central SDK configuration is in `Program.cs`:

```csharp
builder.Logging.ClearProviders();
builder.Logging.AddOpenTelemetry(logging =>
{
    logging.IncludeFormattedMessage = true;
    logging.IncludeScopes = true;
    logging.AddConsoleExporter();

    if (!string.IsNullOrWhiteSpace(applicationInsightsConnectionString))
    {
        logging.AddAzureMonitorLogExporter(options =>
            options.ConnectionString = applicationInsightsConnectionString);
    }
});

builder.Services
    .AddOpenTelemetry()
    .ConfigureResource(resource => resource.AddService("ai200-opentelemetry-demo"))
    .WithTracing(tracing =>
    {
        tracing
            .AddSource(CheckoutTraceService.ActivitySourceName)
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddConsoleExporter();

        if (!string.IsNullOrWhiteSpace(applicationInsightsConnectionString))
        {
            tracing.AddAzureMonitorTraceExporter(options =>
                options.ConnectionString = applicationInsightsConnectionString);
        }
    })
    .WithMetrics(metrics =>
    {
        metrics
            .AddMeter(CheckoutTraceService.MeterName)
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddConsoleExporter();

        if (!string.IsNullOrWhiteSpace(applicationInsightsConnectionString))
        {
            metrics.AddAzureMonitorMetricExporter(options =>
                options.ConnectionString = applicationInsightsConnectionString);
        }
    });
```

`AddSource` connects the custom `ActivitySource` to the trace provider, and `AddMeter` connects the custom `Meter` to the metric provider. `AddOpenTelemetry` connects `ILogger` to the OpenTelemetry log provider. Each provider has a console exporter and conditionally adds its Azure Monitor exporter, so the one application emits and exports all three signals.

## Troubleshooting

### The website works but no telemetry appears in Application Insights

Confirm that `APPLICATIONINSIGHTS_CONNECTION_STRING` exists in the App Service configuration. Allow several minutes for ingestion, then run a new operation.

### Custom spans are missing

Confirm that the name passed to `AddSource` exactly matches `CheckoutTraceService.ActivitySourceName`.

### The custom metric is missing

Confirm that the name passed to `AddMeter` exactly matches `CheckoutTraceService.MeterName`. Run more than one operation and allow several minutes for the metric export interval and Azure ingestion.

### The checkout log is missing

Confirm that `builder.Logging.AddOpenTelemetry(...)` includes `AddAzureMonitorLogExporter` when the connection string is set. Search the `traces` table by the order ID rather than looking only in the **Search** view.

### The self-call fails after deployment

Confirm the site opens over HTTPS and that App Service is running. Inspect the App Service log stream for the outgoing `/api/inventory/ai-course` request.

### Traces appear twice

Do not enable both App Service Application Insights automatic instrumentation and the OpenTelemetry SDK exporter in this demonstration. Keep the SDK-based integration configured in `Program.cs`.

## Microsoft Learn and OpenTelemetry references

- [OpenTelemetry overview in Azure Monitor](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-overview)
- [Add and modify OpenTelemetry in Application Insights](https://learn.microsoft.com/azure/azure-monitor/app/opentelemetry-add-modify)
- [Azure Monitor OpenTelemetry exporter for .NET](https://learn.microsoft.com/dotnet/api/overview/azure/monitor.opentelemetry.exporter-readme)
- [Create a workspace-based Application Insights resource](https://learn.microsoft.com/azure/azure-monitor/app/create-workspace-resource)
- [Application Insights distributed tracing](https://learn.microsoft.com/azure/azure-monitor/app/distributed-trace-data)
- [OpenTelemetry .NET tracing with ASP.NET Core](https://opentelemetry.io/docs/languages/dotnet/traces/getting-started-aspnetcore/)
- [OpenTelemetry traces](https://opentelemetry.io/docs/concepts/signals/traces/)
- [OpenTelemetry metrics](https://opentelemetry.io/docs/concepts/signals/metrics/)
- [OpenTelemetry logs](https://opentelemetry.io/docs/concepts/signals/logs/)
- [Deploy an ASP.NET Core web app to Azure App Service](https://learn.microsoft.com/azure/app-service/quickstart-dotnetcore)
