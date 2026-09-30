using Azure.Identity;
using Azure.Security.KeyVault.Secrets;

var builder = WebApplication.CreateBuilder(args);

builder.Logging.ClearProviders();
builder.Logging.AddConsole();
builder.Services.AddRazorPages();

string vaultUri = builder.Configuration["KeyVault:VaultUri"]
    ?? throw new InvalidOperationException(
        "Set KeyVault:VaultUri or the KeyVault__VaultUri environment variable.");

// DefaultAzureCredential uses the signed-in Azure CLI user locally and the
// App Service system-assigned managed identity after the website is deployed.
builder.Services.AddSingleton(
    new SecretClient(new Uri(vaultUri), new DefaultAzureCredential()));

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
