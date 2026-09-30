using System.Diagnostics;
using System.Diagnostics.Metrics;

namespace OpenTelemetryWeb.Services;

public sealed class CheckoutTraceService
{
    public const string ActivitySourceName = "AI200.OpenTelemetry.Checkout";
    public const string MeterName = "AI200.OpenTelemetry.Checkout";

    // ActivitySource is the .NET tracing API used to create custom OpenTelemetry spans.
    private static readonly ActivitySource ActivitySource = new(ActivitySourceName);
    // Meter is the .NET metrics API used to create OpenTelemetry instruments.
    private static readonly Meter Meter = new(MeterName);
    private static readonly Counter<long> CheckoutsCompleted =
        Meter.CreateCounter<long>(
            name: "demo.checkout.completed",
            unit: "{checkout}",
            description: "Number of completed checkout operations");
    private readonly HttpClient _httpClient;
    private readonly ILogger<CheckoutTraceService> _logger;

    public CheckoutTraceService(
        HttpClient httpClient,
        ILogger<CheckoutTraceService> logger)
    {
        _httpClient = httpClient;
        _logger = logger;
    }

    public async Task<CheckoutTraceResult> RunAsync(
        Uri inventoryEndpoint,
        CancellationToken cancellationToken)
    {
        string orderId = Guid.NewGuid().ToString("N")[..8];

        // Create the parent custom span for the demonstration's business operation.
        using Activity? checkoutActivity = ActivitySource.StartActivity("ProcessCheckout");
        checkoutActivity?.SetTag("demo.order.id", orderId);
        checkoutActivity?.SetTag("demo.item", "ai-course");

        // Create a child span for a simulated validation step.
        using (Activity? validationActivity = ActivitySource.StartActivity("ValidateOrder"))
        {
            validationActivity?.SetTag("demo.validation.result", "approved");
            await Task.Delay(80, cancellationToken);
        }

        // Create another child span around an outgoing HTTP dependency call.
        using (Activity? inventoryActivity = ActivitySource.StartActivity("CheckInventory"))
        {
            inventoryActivity?.SetTag("demo.inventory.item", "ai-course");

            // HttpClient instrumentation creates a client span and injects trace context
            // into this request. The receiving endpoint joins the same distributed trace.
            using HttpResponseMessage response = await _httpClient.GetAsync(
                inventoryEndpoint,
                cancellationToken);
            response.EnsureSuccessStatusCode();

            inventoryActivity?.SetTag("demo.inventory.available", true);
        }

        // Events record meaningful points in time inside a span.
        checkoutActivity?.AddEvent(new ActivityEvent("checkout.completed"));
        checkoutActivity?.SetStatus(ActivityStatusCode.Ok);

        // Record one custom metric data point for the successful operation.
        CheckoutsCompleted.Add(
            1,
            new KeyValuePair<string, object?>("demo.item", "ai-course"));

        // Emit a structured log while the Activity is active so the log is
        // automatically correlated with the current trace and span.
        _logger.LogInformation(
            "Checkout {OrderId} completed for {Item}",
            orderId,
            "ai-course");

        string traceId = checkoutActivity?.TraceId.ToString()
            ?? Activity.Current?.TraceId.ToString()
            ?? "unavailable";

        return new CheckoutTraceResult(orderId, traceId);
    }
}

public sealed record CheckoutTraceResult(string OrderId, string TraceId);
