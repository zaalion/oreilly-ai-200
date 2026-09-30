using Azure.Identity;
using Microsoft.Extensions.Configuration.AzureAppConfiguration;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.ClearProviders();
builder.Logging.AddConsole();

string appConfigurationEndpoint = builder.Configuration["Endpoints:AppConfiguration"]
    ?? throw new InvalidOperationException(
        "Set Endpoints:AppConfiguration or the Endpoints__AppConfiguration environment variable.");

var credential = new DefaultAzureCredential(new DefaultAzureCredentialOptions
{
    // A managed-identity endpoint exists only in Azure. Skip that credential
    // locally so DefaultAzureCredential can use the signed-in Azure CLI user.
    ExcludeManagedIdentityCredential = builder.Environment.IsDevelopment()
});

// Load the Demo:* keys from Azure App Configuration using the local Azure CLI
// identity during development or the App Service managed identity in Azure.
builder.Configuration.AddAzureAppConfiguration(options =>
{
    options
        .Connect(new Uri(appConfigurationEndpoint), credential)
        .Select("Demo:*")
        // Resolve any selected App Configuration Key Vault references by using
        // the same credential to retrieve their secret values from Key Vault.
        .ConfigureKeyVault(keyVaultOptions =>
        {
            keyVaultOptions.SetCredential(credential);
        });
});

builder.Services.AddRazorPages();

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

app.Run();
