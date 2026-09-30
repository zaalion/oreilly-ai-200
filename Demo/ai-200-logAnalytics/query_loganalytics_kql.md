# Analyze Azure logs and metrics with KQL

## What is a Log Analytics workspace?

An Azure Log Analytics workspace is a centralized data store for logs and metrics collected by Azure Monitor. Azure resources send diagnostic logs, platform metrics, activity logs, and application telemetry to tables in the workspace. You can then query data from several resources together, create workbooks and alerts, investigate failures, and analyze performance over time.

This guide uses the existing workspace:

| Setting | Value |
|---|---|
| Workspace | `oreilly-laws-general` |
| Resource group | `AI-200` |
| Subscription | `19969c81-e8ff-4585-8c2f-3f196b588227` |

[Open the oreilly-laws-general Logs query pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

## What is KQL?

Kusto Query Language, usually called KQL, is the read-only query language used by Azure Monitor Logs. A KQL query starts with a table or data source and sends its rows through a pipeline of operators separated by `|` characters.

For example:

```kusto
AzureActivity
| where TimeGenerated > ago(24h)
| summarize Events = count() by ResourceProviderValue
| order by Events desc
```

Common operators include:

| Operator | Purpose |
|---|---|
| `where` | Filters rows. |
| `project` | Chooses, renames, or calculates columns. |
| `extend` | Adds calculated columns. |
| `summarize` | Aggregates rows using functions such as `count()`, `avg()`, and `percentile()`. |
| `bin()` | Groups timestamps or numbers into intervals. |
| `order by` | Sorts results. |
| `top` | Returns the highest or lowest results. |
| `union` | Combines rows from multiple tables. |
| `render` | Displays results as a chart. |

KQL does not modify the monitored resources or their data. It analyzes telemetry already stored in the workspace.

## Before running the queries

Azure Monitor can store resource logs in either resource-specific tables or the legacy shared `AzureDiagnostics` table. This guide primarily uses the newer resource-specific tables:

| Resource | Tables used in this guide |
|---|---|
| App Service | `AppServiceHTTPLogs`, `AppServiceConsoleLogs` |
| Azure Cosmos DB | `CDBDataPlaneRequests`, `CDBPartitionKeyRUConsumption` |
| Azure Key Vault | `AZKVAuditLogs` |
| Platform metrics | `AzureMetrics` |
| Azure control-plane operations | `AzureActivity` |

A table appears only after the corresponding diagnostic category has sent data to this workspace. `AzureMetrics` requires the resources' diagnostic settings to send metrics such as **AllMetrics** to `oreilly-laws-general`.

If a query reports that a table does not exist, first run the discovery queries below. Then verify the resource's diagnostic settings, selected log or metric categories, destination workspace, and table mode.

## Workspace-wide queries

### 1. Discover tables that are receiving data

Use this query first to see which tables have received records during the last seven days. It prevents guessing which diagnostic-table mode is configured.

```kusto
search *
| where TimeGenerated > ago(7d)
| summarize Records = count(), LatestRecord = max(TimeGenerated) by Table = $table
| order by Records desc
```

[Run query 1 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 2. Discover available platform metrics

Use this query to list the metric names, units, providers, and resources currently stored in `AzureMetrics`. Run it before selecting metric names in later examples.

```kusto
AzureMetrics
| where TimeGenerated > ago(7d)
| summarize Records = count(), LatestRecord = max(TimeGenerated)
    by ResourceProvider, Resource, MetricName, UnitName
| order by ResourceProvider asc, Resource asc, MetricName asc
```

[Run query 2 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 3. Measure billable ingestion by table

Use this query to find which tables generated the most billable ingestion during the last seven days. `_BilledSize` contains the record size in bytes.

```kusto
search *
| where TimeGenerated > ago(7d)
| where _IsBillable =~ "true"
| summarize Records = count(), IngestedGB = sum(_BilledSize) / 1024 / 1024 / 1024
    by Table = $table
| order by IngestedGB desc
```

[Run query 3 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 4. Find resources producing the most log records

Use this query to identify noisy resources. It groups recent records by their Azure resource ID.

```kusto
search *
| where TimeGenerated > ago(24h)
| where isnotempty(_ResourceId)
| summarize Records = count(), IngestedMB = sum(_BilledSize) / 1024 / 1024
    by _ResourceId
| top 20 by Records desc
```

[Run query 4 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 5. Review failed Azure management operations

Use this query to find failed control-plane operations such as resource creation, configuration changes, role assignments, or deletion. These are management events, not application requests.

```kusto
AzureActivity
| where TimeGenerated > ago(7d)
| where ActivityStatusValue =~ "Failed"
| project TimeGenerated, ResourceGroup, ResourceProviderValue,
    Resource, OperationNameValue, Caller, CallerIpAddress,
    ActivitySubstatusValue, CorrelationId
| order by TimeGenerated desc
```

[Run query 5 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

## App Service queries

### 6. Count HTTP requests by web app and status code

Use this query to understand traffic volume and the HTTP responses returned by each App Service web app.

```kusto
AppServiceHTTPLogs
| where TimeGenerated > ago(24h)
| summarize Requests = count() by WebApp = tostring(split(_ResourceId, "/")[-1]), ScStatus
| order by WebApp asc, Requests desc
```

[Run query 6 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 7. Find recent HTTP errors

Use this query to inspect client errors and server errors, including the requested URL, method, client address, and request duration.

```kusto
AppServiceHTTPLogs
| where TimeGenerated > ago(24h)
| where ScStatus >= 400
| project TimeGenerated,
    WebApp = tostring(split(_ResourceId, "/")[-1]),
    CsMethod, CsUriStem, CsUriQuery, ScStatus, ScSubStatus, CIp, TimeTaken
| order by TimeGenerated desc
```

[Run query 7 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 8. Find the slowest web endpoints

Use this query to calculate request count, average duration, and 95th-percentile duration for each endpoint. The 95th percentile shows the time under which 95 percent of requests completed.

```kusto
AppServiceHTTPLogs
| where TimeGenerated > ago(24h)
| summarize Requests = count(),
    AverageMs = round(avg(TimeTaken), 1),
    P95Ms = round(percentile(TimeTaken, 95), 1),
    MaximumMs = max(TimeTaken)
    by WebApp = tostring(split(_ResourceId, "/")[-1]), CsMethod, CsUriStem
| top 20 by P95Ms desc
```

[Run query 8 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 9. Find errors in App Service console logs

Use this query to find error-level application messages and messages containing common failure terms.

```kusto
AppServiceConsoleLogs
| where TimeGenerated > ago(24h)
| where Level in~ ("Error", "Critical")
    or ResultDescription has_any ("exception", "error", "failed", "fatal")
| project TimeGenerated,
    WebApp = tostring(split(_ResourceId, "/")[-1]),
    Level, ResultDescription
| order by TimeGenerated desc
```

[Run query 9 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 10. Graph App Service platform metrics

Use this query to graph available App Service request, response-time, CPU-time, and memory metrics. Run query 2 first because the exact exported metric names depend on the resource and diagnostic settings.

```kusto
AzureMetrics
| where TimeGenerated > ago(24h)
| where ResourceProvider =~ "MICROSOFT.WEB"
| where MetricName in ("Requests", "AverageResponseTime", "CpuTime", "MemoryWorkingSet")
| extend MetricValue = coalesce(Average, Total, Maximum)
| summarize MetricValue = avg(MetricValue)
    by bin(TimeGenerated, 5m), Resource, MetricName, UnitName
| render timechart
```

[Run query 10 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

## Azure Cosmos DB queries

### 11. Find throttled Cosmos DB requests

Use this query to find HTTP `429` responses. A `429` means the request exceeded the currently available request units and was rate limited.

```kusto
CDBDataPlaneRequests
| where TimeGenerated > ago(24h)
| where StatusCode == 429
| summarize ThrottledRequests = count(),
    TotalRU = round(sum(RequestCharge), 2),
    AverageDurationMs = round(avg(DurationMs), 2)
    by AccountName, DatabaseName, CollectionName, OperationName, RegionName
| order by ThrottledRequests desc
```

[Run query 11 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 12. Analyze request-unit consumption

Use this query to identify operations and containers consuming the most request units.

```kusto
CDBDataPlaneRequests
| where TimeGenerated > ago(24h)
| summarize Requests = count(),
    TotalRU = round(sum(RequestCharge), 2),
    AverageRU = round(avg(RequestCharge), 2),
    MaximumRU = round(max(RequestCharge), 2)
    by AccountName, DatabaseName, CollectionName, OperationName
| order by TotalRU desc
```

[Run query 12 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 13. Find the slowest Cosmos DB operations

Use this query to calculate server-side average, 95th-percentile, and maximum latency by operation and container.

```kusto
CDBDataPlaneRequests
| where TimeGenerated > ago(24h)
| summarize Requests = count(),
    AverageDurationMs = round(avg(DurationMs), 2),
    P95DurationMs = round(percentile(DurationMs, 95), 2),
    MaximumDurationMs = round(max(DurationMs), 2)
    by AccountName, DatabaseName, CollectionName, OperationName
| top 20 by P95DurationMs desc
```

[Run query 13 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 14. Identify hot logical partition keys

Use this query to find partition keys that consumed the most request units. The `CDBPartitionKeyRUConsumption` diagnostic category must be enabled for this table to contain data.

```kusto
CDBPartitionKeyRUConsumption
| where TimeGenerated > ago(24h)
| summarize Requests = count(), TotalRU = round(sum(RequestCharge), 2)
    by AccountName, DatabaseName, CollectionName,
       PartitionKey, PartitionKeyRangeId, OperationName
| top 20 by TotalRU desc
```

[Run query 14 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 15. Graph Cosmos DB platform metrics

Use this query to graph exported Cosmos DB request, request-unit, latency, and normalized RU-consumption metrics. Run query 2 first and adjust the metric-name list to match the available data.

```kusto
AzureMetrics
| where TimeGenerated > ago(24h)
| where ResourceProvider =~ "MICROSOFT.DOCUMENTDB"
| where MetricName in ("TotalRequests", "TotalRequestUnits", "ServerSideLatency", "NormalizedRUConsumption")
| extend MetricValue = coalesce(Average, Total, Maximum)
| summarize MetricValue = avg(MetricValue)
    by bin(TimeGenerated, 5m), Resource, MetricName, UnitName
| render timechart
```

[Run query 15 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

## Azure Key Vault queries

### 16. Review Key Vault operations

Use this query to see which secret, key, certificate, and vault operations occurred and whether they succeeded.

```kusto
AZKVAuditLogs
| where TimeGenerated > ago(24h)
| summarize Requests = count(),
    Successful = countif(HttpStatusCode between (200 .. 299)),
    Failed = countif(HttpStatusCode < 200 or HttpStatusCode >= 300),
    AverageDurationMs = round(avg(DurationMs), 2)
    by Vault = tostring(split(_ResourceId, "/")[-1]), OperationName
| order by Requests desc
```

[Run query 16 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 17. Show which identities and IP addresses accessed Key Vault

Use this query to audit callers. `Identity` is a dynamic object containing available user, application, or service-principal claims.

```kusto
AZKVAuditLogs
| where TimeGenerated > ago(24h)
| summarize Requests = count(), LatestRequest = max(TimeGenerated)
    by Vault = tostring(split(_ResourceId, "/")[-1]),
       Identity = tostring(Identity), CallerIpAddress, OperationName
| order by LatestRequest desc
```

[Run query 17 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 18. Find failed or unauthorized Key Vault requests

Use this query to investigate denied access, authentication failures, missing secrets, and other unsuccessful requests.

```kusto
AZKVAuditLogs
| where TimeGenerated > ago(7d)
| where HttpStatusCode < 200 or HttpStatusCode >= 300
| project TimeGenerated,
    Vault = tostring(split(_ResourceId, "/")[-1]),
    OperationName, HttpStatusCode, ResultType, ResultSignature,
    IsRbacAuthorized, IsAddressAuthorized, CallerIpAddress,
    Identity = tostring(Identity), RequestUri, ResultDescription,
    CorrelationId
| order by TimeGenerated desc
```

[Run query 18 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 19. Analyze Key Vault latency and success rate

Use this query to compare average and 95th-percentile service time and calculate the success percentage for each operation.

```kusto
AZKVAuditLogs
| where TimeGenerated > ago(24h)
| summarize Requests = count(),
    SuccessfulRequests = countif(HttpStatusCode between (200 .. 299)),
    AverageDurationMs = round(avg(DurationMs), 2),
    P95DurationMs = round(percentile(DurationMs, 95), 2)
    by Vault = tostring(split(_ResourceId, "/")[-1]), OperationName
| extend SuccessPercent = round(100.0 * SuccessfulRequests / Requests, 2)
| order by P95DurationMs desc
```

[Run query 19 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 20. Graph Key Vault platform metrics

Use this query to graph available Key Vault availability, request-volume, and service-latency metrics. Run query 2 first and adjust the metric names if necessary.

```kusto
AzureMetrics
| where TimeGenerated > ago(24h)
| where ResourceProvider =~ "MICROSOFT.KEYVAULT"
| where MetricName in ("Availability", "ServiceApiHit", "ServiceApiLatency", "ServiceApiResult")
| extend MetricValue = coalesce(Average, Total, Maximum)
| summarize MetricValue = avg(MetricValue)
    by bin(TimeGenerated, 5m), Resource, MetricName, UnitName
| render timechart
```

[Run query 20 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

## Cross-resource queries

### 21. Compare failures across App Service, Cosmos DB, and Key Vault

Use this query to create a single failure timeline across the three resource types. `isfuzzy=true` allows the union to continue when one referenced table is unavailable, provided at least one table exists.

```kusto
union isfuzzy=true
    (AppServiceHTTPLogs
        | where ScStatus >= 400
        | project TimeGenerated,
            Service = "App Service",
            Resource = tostring(split(_ResourceId, "/")[-1]),
            Failure = strcat(ScStatus, " ", CsMethod, " ", CsUriStem)),
    (CDBDataPlaneRequests
        | where StatusCode < 200 or StatusCode >= 300
        | project TimeGenerated,
            Service = "Cosmos DB",
            Resource = AccountName,
            Failure = strcat(StatusCode, " ", OperationName, " ", DatabaseName, "/", CollectionName)),
    (AZKVAuditLogs
        | where HttpStatusCode < 200 or HttpStatusCode >= 300
        | project TimeGenerated,
            Service = "Key Vault",
            Resource = tostring(split(_ResourceId, "/")[-1]),
            Failure = strcat(HttpStatusCode, " ", OperationName))
| where TimeGenerated > ago(24h)
| order by TimeGenerated desc
```

[Run query 21 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

### 22. Graph failure counts by service

Use this query to identify whether failure spikes occurred at the same time across App Service, Cosmos DB, and Key Vault.

```kusto
union isfuzzy=true
    (AppServiceHTTPLogs
        | where ScStatus >= 400
        | project TimeGenerated, Service = "App Service"),
    (CDBDataPlaneRequests
        | where StatusCode < 200 or StatusCode >= 300
        | project TimeGenerated, Service = "Cosmos DB"),
    (AZKVAuditLogs
        | where HttpStatusCode < 200 or HttpStatusCode >= 300
        | project TimeGenerated, Service = "Key Vault")
| where TimeGenerated > ago(24h)
| summarize Failures = count() by bin(TimeGenerated, 15m), Service
| render timechart
```

[Run query 22 in the Logs pane](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

## If your resources use `AzureDiagnostics`

If query 1 shows `AzureDiagnostics` instead of the resource-specific tables, inspect the available providers, categories, and columns first:

```kusto
AzureDiagnostics
| where TimeGenerated > ago(7d)
| summarize Records = count()
    by ResourceProvider, Category, ResourceType, Resource
| order by Records desc
```

[Run the AzureDiagnostics discovery query](https://portal.azure.com/#@zaalion.com/resource/subscriptions/19969c81-e8ff-4585-8c2f-3f196b588227/resourceGroups/AI-200/providers/Microsoft.OperationalInsights/workspaces/oreilly-laws-general/Logs)

The legacy table uses provider-specific columns whose names often end with type suffixes such as `_s`, `_d`, or `_g`. Select a recent row for the relevant provider and inspect its columns before adapting a resource-specific query.

## Microsoft Learn references

- [Azure Monitor Logs overview](https://learn.microsoft.com/azure/azure-monitor/logs/data-platform-logs)
- [Log Analytics tutorial](https://learn.microsoft.com/azure/azure-monitor/logs/log-analytics-tutorial)
- [Kusto Query Language overview](https://learn.microsoft.com/kusto/query/)
- [KQL quick reference](https://learn.microsoft.com/azure/data-explorer/kql-quick-reference)
- [Azure Monitor Logs table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables-index)
- [`AzureMetrics` table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables/azuremetrics)
- [`AzureActivity` table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables/azureactivity)
- [`AppServiceHTTPLogs` table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables/appservicehttplogs)
- [`AppServiceConsoleLogs` table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables/appserviceconsolelogs)
- [Azure Cosmos DB monitoring data reference](https://learn.microsoft.com/azure/cosmos-db/monitor-reference)
- [`CDBDataPlaneRequests` table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables/cdbdataplanerequests)
- [`CDBPartitionKeyRUConsumption` table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables/cdbpartitionkeyruconsumption)
- [Azure Key Vault monitoring data reference](https://learn.microsoft.com/azure/key-vault/general/monitor-key-vault-reference)
- [`AZKVAuditLogs` table reference](https://learn.microsoft.com/azure/azure-monitor/reference/tables/azkvauditlogs)
- [Diagnostic settings in Azure Monitor](https://learn.microsoft.com/azure/azure-monitor/essentials/diagnostic-settings)
