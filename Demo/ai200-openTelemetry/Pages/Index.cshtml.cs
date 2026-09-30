using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;
using OpenTelemetryWeb.Services;

namespace OpenTelemetryWeb.Pages;

public sealed class IndexModel : PageModel
{
    private readonly CheckoutTraceService _checkoutTraceService;

    public IndexModel(CheckoutTraceService checkoutTraceService)
    {
        _checkoutTraceService = checkoutTraceService;
    }

    public CheckoutTraceResult? Result { get; private set; }

    public void OnGet()
    {
    }

    public async Task<IActionResult> OnPostAsync(CancellationToken cancellationToken)
    {
        // Call this same web application through HttpClient so the demonstration
        // includes both outgoing client instrumentation and incoming server instrumentation.
        var inventoryEndpoint = new Uri(
            $"{Request.Scheme}://{Request.Host}{Request.PathBase}/api/inventory/ai-course");

        Result = await _checkoutTraceService.RunAsync(
            inventoryEndpoint,
            cancellationToken);

        return Page();
    }
}
