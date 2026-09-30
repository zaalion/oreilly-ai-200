# Deploy the .NET 9 Key Vault website

## What this demonstration creates

This demonstration creates an ASP.NET Core 9 Razor Pages website with two operations:

- **Save secret** stores the textbox value in Azure Key Vault as `student-demo-secret`.
- **Fetch secret** reads the latest version of that secret and displays it on the page.

No container is used. The compiled website is deployed directly to Azure App Service on a Linux S1 App Service plan.

The code uses `DefaultAzureCredential` and does not contain a Key Vault password or access key:

- When the website runs locally, `DefaultAzureCredential` can use the identity authenticated by `az login`.
- When the website runs in App Service, it uses the web app's system-assigned managed identity.

Both identities require an Azure Key Vault data-plane role before they can access secrets.

## 1. Prerequisites

Install or verify:

- .NET 9 SDK
- Azure CLI
- An Azure account that can create resources and role assignments

```powershell
dotnet --version
az version
```

## 2. Open the project

```powershell
cd C:\Data\Repo\oreilly-ai-200\Demo\ai-200-keyVault
```

## 3. Sign in and define deployment values

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

$resourceGroup = "AI-200"
$location = "eastus"
$suffix = Get-Random -Minimum 100000 -Maximum 999999
$vaultName = "oreilly-ai200-kv-$suffix"
$planName = "oreilly-ai200-kv-s1-plan"
$appName = "oreilly-ai200-kv-web-$suffix"
```

Key Vault names and App Service app names must be globally unique, so the random suffix is included in both names.

## 4. Register the resource providers (confirm registration first)

```powershell
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Web
```

Resource-provider registration allows the subscription to create Key Vault and App Service resources. Registration is normally required only once per subscription.

Confirm registration:

```powershell
az provider show --namespace Microsoft.KeyVault --query registrationState --output tsv
az provider show --namespace Microsoft.Web --query registrationState --output tsv
```

Continue when both commands return `Registered`.

## 5. Create the resource group and Key Vault

The resource-group command is safe to run when `AI-200` already exists.

```powershell
az group create `
  --name $resourceGroup `
  --location $location

az keyvault create `
  --name $vaultName `
  --resource-group $resourceGroup `
  --location $location `
  --sku standard `
  --enable-rbac-authorization true `
  --enable-purge-protection true
```

This vault uses Azure RBAC for data access. Purge protection prevents a deleted vault from being permanently removed until its retention period expires.

Save the vault resource ID and URI:

```powershell
$vaultId = az keyvault show `
  --name $vaultName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

$vaultUri = az keyvault show `
  --name $vaultName `
  --resource-group $resourceGroup `
  --query properties.vaultUri `
  --output tsv
```

## 6. Give your local Azure CLI identity access

`DefaultAzureCredential` uses your Azure CLI identity while the application runs locally. Assign that user the `Key Vault Secrets Officer` role because the website must both save and retrieve secrets:

```powershell
$signedInUserId = az ad signed-in-user show --query id --output tsv

az role assignment create `
  --assignee-object-id $signedInUserId `
  --assignee-principal-type User `
  --role "Key Vault Secrets Officer" `
  --scope $vaultId
```

Azure role assignments can take several minutes to become effective.

## 7. Run and test the website locally

Set the vault URI in the current PowerShell terminal. A vault URI is not a secret.

```powershell
$env:KeyVault__VaultUri = $vaultUri
dotnet restore
dotnet run
```

Open `http://localhost:5180` if the browser does not open automatically.

1. Enter a value in the textbox.
2. Select **Save secret**.
3. Select **Fetch secret**.
4. Confirm that the saved value appears on the page.

The application saves each new value as a new version of `student-demo-secret`. Fetching the secret returns its latest enabled version.

## 8. Confirm that App Service supports the .NET 9 runtime

```powershell
az webapp list-runtimes --os linux | Select-String "DOTNETCORE"
```

Confirm that `DOTNETCORE:9.0` appears in the output.

## 9. Create the Linux S1 App Service plan

```powershell
az appservice plan create `
  --name $planName `
  --resource-group $resourceGroup `
  --location $location `
  --sku S1 `
  --is-linux
```

An App Service plan supplies the compute resources for the website. `S1` is the Standard tier with one worker by default.

## 10. Create the App Service web app

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

This creates a code-based Linux web app and redirects public HTTP requests to HTTPS. It does not create or use a container image.

## 11. Enable the system-assigned identity

```powershell
$appPrincipalId = az webapp identity assign `
  --name $appName `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv
```

The identity belongs to this web app and is managed by Azure. The application can request Microsoft Entra tokens without storing a client secret.

## 12. Authorize the App Service identity to use secrets

```powershell
az role assignment create `
  --assignee-object-id $appPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role "Key Vault Secrets Officer" `
  --scope $vaultId
```

`Key Vault Secrets Officer` permits the app to create, update, and read secrets. Assigning it at `$vaultId` limits the role to this vault.

Role assignments can take several minutes to propagate. If the deployed app initially receives an authorization error, wait briefly and try again.

## 13. Configure the vault URI in App Service

```powershell
az webapp config appsettings set `
  --name $appName `
  --resource-group $resourceGroup `
  --settings "KeyVault__VaultUri=$vaultUri"
```

ASP.NET Core converts the double underscore in `KeyVault__VaultUri` to the configuration key `KeyVault:VaultUri`.

Only the URI is stored in App Service configuration. Authentication is performed by the system-assigned identity.

## 14. Publish and deploy the website

```powershell
dotnet publish .\KeyVaultWeb.csproj `
  --configuration Release `
  --output .\publish

Compress-Archive `
  -Path .\publish\* `
  -DestinationPath .\keyvault-web.zip `
  -Force

az webapp deploy `
  --name $appName `
  --resource-group $resourceGroup `
  --src-path .\keyvault-web.zip `
  --type zip `
  --clean true
```

The ZIP contains the already compiled application. App Service does not need to build the source code or pull a container image.

## 15. Open and test the deployed website

```powershell
$hostName = az webapp show `
  --name $appName `
  --resource-group $resourceGroup `
  --query defaultHostName `
  --output tsv

"https://$hostName"
```

Open the returned URL, save a secret, and then select **Fetch secret**. The web app now accesses Key Vault through its system-assigned identity.

## 16. View App Service logs

Enable application logging:

```powershell
az webapp log config `
  --name $appName `
  --resource-group $resourceGroup `
  --application-logging filesystem `
  --level information
```

Stream the logs:

```powershell
az webapp log tail `
  --name $appName `
  --resource-group $resourceGroup
```

Press `Ctrl+C` to stop streaming.

## Troubleshooting

### `DefaultAzureCredential failed to retrieve a token`

For local execution, run `az login` again in your Windows user account. For App Service, confirm that the system-assigned identity is enabled.

### HTTP 403 or `Forbidden` from Key Vault

Confirm that the correct identity has `Key Vault Secrets Officer` at the vault scope. For local execution, check the signed-in user. For App Service, check `$appPrincipalId`. Allow time for a new role assignment to propagate.

### The app reports that `KeyVault:VaultUri` is missing

Locally, set `$env:KeyVault__VaultUri = $vaultUri` in the terminal before `dotnet run`. In App Service, repeat step 13 and restart the web app:

```powershell
az webapp restart --name $appName --resource-group $resourceGroup
```

### The deployment succeeds but the website does not start

Confirm that the App Service runtime is `DOTNETCORE:9.0`, then inspect the log stream from step 16.

## Microsoft Learn references

- [Azure Key Vault overview](https://learn.microsoft.com/azure/key-vault/general/overview)
- [Create a Key Vault using the Azure CLI](https://learn.microsoft.com/azure/key-vault/general/quick-create-cli)
- [Use Azure RBAC to grant access to Key Vault](https://learn.microsoft.com/azure/key-vault/general/rbac-guide)
- [Authenticate .NET apps to Azure services using DefaultAzureCredential](https://learn.microsoft.com/dotnet/azure/sdk/authentication/credential-chains)
- [Use managed identities for App Service](https://learn.microsoft.com/azure/app-service/overview-managed-identity)
- [Deploy an ASP.NET Core web app to Azure App Service](https://learn.microsoft.com/azure/app-service/quickstart-dotnetcore)
- [Deploy files to Azure App Service](https://learn.microsoft.com/azure/app-service/deploy-zip)
- [Azure App Service plan CLI reference](https://learn.microsoft.com/cli/azure/appservice/plan)
