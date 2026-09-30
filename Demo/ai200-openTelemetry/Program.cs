using Azure.Monitor.OpenTelemetry.Exporter;
using OpenTelemetry.Logs;
using OpenTelemetry.Metrics;
using OpenTelemetry.Resources;
using OpenTelemetry.Trace;
using OpenTelemetryWeb.Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddRazorPages();
builder.Services.AddHttpClient<CheckoutTraceService>();

string? applicationInsightsConnectionString =
    builder.Configuration["APPLICATIONINSIGHTS_CONNECTION_STRING"];

// Send application logs through OpenTelemetry. Log records created while an
// Activity is active automatically include its trace ID and span ID.
builder.Logging.ClearProviders();
builder.Logging.AddOpenTelemetry(logging =>
{
    logging.IncludeFormattedMessage = true;
    logging.IncludeScopes = true;
    logging.AddConsoleExporter();

    if (!string.IsNullOrWhiteSpace(applicationInsightsConnectionString))
    {
        logging.AddAzureMonitorLogExporter(options =>
        {
            options.ConnectionString = applicationInsightsConnectionString;
        });
    }
});

// Configure the OpenTelemetry SDK and identify this application in exported telemetry.
builder.Services
    .AddOpenTelemetry()
    .ConfigureResource(resource => resource.AddService(
        serviceName: "ai200-opentelemetry-demo",
        serviceVersion: "1.0.0"))
    .WithTracing(tracing =>
    {
        tracing
            // Collect custom spans created by CheckoutTraceService.ActivitySource.
            .AddSource(CheckoutTraceService.ActivitySourceName)
            // Automatically trace incoming ASP.NET Core requests.
            .AddAspNetCoreInstrumentation(options => options.RecordException = true)
            // Automatically trace outgoing requests made through HttpClient.
            .AddHttpClientInstrumentation(options => options.RecordException = true)
            // Print completed spans in the local application console.
            .AddConsoleExporter();

        if (!string.IsNullOrWhiteSpace(applicationInsightsConnectionString))
        {
            // Export the same spans to Application Insights when its connection string is configured.
            tracing.AddAzureMonitorTraceExporter(options =>
            {
                options.ConnectionString = applicationInsightsConnectionString;
            });
        }
    })
    .WithMetrics(metrics =>
    {
        metrics
            // Collect the custom checkout counter.
            .AddMeter(CheckoutTraceService.MeterName)
            // Collect standard ASP.NET Core and HttpClient measurements.
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            // Print metric data points in the local application console.
            .AddConsoleExporter();

        if (!string.IsNullOrWhiteSpace(applicationInsightsConnectionString))
        {
            metrics.AddAzureMonitorMetricExporter(options =>
            {
                options.ConnectionString = applicationInsightsConnectionString;
            });
        }
    });

var app = builder.Build();

if (!app.Environment.IsDevelopment())
{
    app.UseExceptionHandler("/Error");
    app.UseHsts();
    app.UseHttpsRedirection();
}

app.UseStaticFiles();
app.UseRouting();
app.UseAuthorization();
app.MapRazorPages();

// This endpoint simulates a dependency called by the traced checkout operation.
// ASP.NET Core instrumentation creates a server span whenever this endpoint runs.
app.MapGet("/api/inventory/{item}", async (string item, CancellationToken cancellationToken) =>
{
    await Task.Delay(120, cancellationToken);
    return Results.Ok(new { item, available = true, quantity = 12 });
});

app.Run();
