using Microsoft.AspNetCore.Mvc.RazorPages;

namespace AppConfigurationWeb.Pages;

public sealed class IndexModel : PageModel
{
    private readonly IConfiguration _configuration;

    public IndexModel(IConfiguration configuration)
    {
        _configuration = configuration;
    }

    public string DirectMessage { get; private set; } = string.Empty;
    public string KeyVaultMessage { get; private set; } = string.Empty;

    public void OnGet()
    {
        // Read a normal key-value stored directly in Azure App Configuration.
        DirectMessage = _configuration["Demo:DirectMessage"]
            ?? "The direct App Configuration value was not found.";

        // The provider recognizes this key as a Key Vault reference, retrieves
        // its secret from Key Vault, and exposes the resolved value like any other setting.
        KeyVaultMessage = _configuration["Demo:KeyVaultMessage"]
            ?? "The Key Vault reference value was not found.";
    }
}
