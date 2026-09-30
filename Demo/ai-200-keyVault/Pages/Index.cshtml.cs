using System.ComponentModel.DataAnnotations;
using Azure;
using Azure.Security.KeyVault.Secrets;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Mvc.RazorPages;

namespace KeyVaultWeb.Pages;

public sealed class IndexModel : PageModel
{
    private const string StoredSecretName = "student-demo-secret";
    private readonly SecretClient _secretClient;

    public IndexModel(SecretClient secretClient)
    {
        _secretClient = secretClient;
    }

    [BindProperty]
    [Required(ErrorMessage = "Enter a secret value.")]
    public string SecretValue { get; set; } = string.Empty;

    public string SecretName => StoredSecretName;
    public string? FetchedSecret { get; private set; }
    public string? StatusMessage { get; private set; }

    public void OnGet()
    {
    }

    // Save the submitted value as a new version of the fixed demo secret.
    public async Task<IActionResult> OnPostSaveAsync()
    {
        if (!ModelState.IsValid)
        {
            return Page();
        }

        await _secretClient.SetSecretAsync(StoredSecretName, SecretValue);
        StatusMessage = $"Secret '{StoredSecretName}' was saved to Key Vault.";
        SecretValue = string.Empty;
        ModelState.Clear();

        return Page();
    }

    // Read the latest enabled version of the demo secret from Key Vault.
    public async Task<IActionResult> OnPostFetchAsync()
    {
        ModelState.Clear();

        try
        {
            KeyVaultSecret secret = await _secretClient.GetSecretAsync(StoredSecretName);
            FetchedSecret = secret.Value;
            StatusMessage = $"Secret '{StoredSecretName}' was fetched from Key Vault.";
        }
        catch (RequestFailedException exception) when (exception.Status == 404)
        {
            StatusMessage = $"Secret '{StoredSecretName}' does not exist yet.";
        }

        return Page();
    }
}
