# Deploy the Azure App Configuration website

## What is Azure App Configuration?

Azure App Configuration is a managed service for storing application settings and feature flags in a central location. It separates configuration from application code so settings can be managed consistently across applications and environments.

App Configuration is intended for configuration data, not for storing secrets directly. Sensitive values should remain in Azure Key Vault. App Configuration can store a **Key Vault reference**, which is a configuration value containing the URI of a Key Vault secret. The application recognizes the reference and retrieves the secret directly from Key Vault.

In this demonstration, the website displays:

- `Demo:DirectMessage`, whose value is stored directly in Azure App Configuration.
- `Demo:KeyVaultMessage`, which is stored in App Configuration as a Key Vault reference. Its actual value is stored in a newly created Key Vault.

The App Configuration service does not retrieve the secret. The website authenticates separately to App Configuration and Key Vault and retrieves both values.

### Which identity accesses Key Vault?

Azure App Configuration does **not** need access to Key Vault for this scenario. It stores only the Key Vault secret reference, which contains the secret's URI rather than its value.

The web application performs both operations using its own identity:

```text
Web app identity -> App Configuration -> reads the configuration key and secret reference
Web app identity -> Key Vault        -> resolves the reference and reads the secret value
```

Therefore, the deployed App Service system-assigned identity needs `App Configuration Data Reader` on the App Configuration store and `Key Vault Secrets User` on the Key Vault. App Configuration's own identity does not need a Key Vault role. For local execution, the Azure CLI user needs equivalent access to both services. See [Use Key Vault references in an ASP.NET Core app](https://learn.microsoft.com/azure/azure-app-configuration/use-key-vault-references-dotnet-core).

## Common use cases

- Centrally manage settings shared by several applications or services.
- Maintain different configuration values for development, testing, and production.
- Change application behavior without rebuilding the application.
- Manage feature flags for controlled feature releases.
- Organize related settings with key prefixes and labels.
- Reference secrets stored securely in Azure Key Vault.
- Audit and control configuration access through Microsoft Entra ID and Azure RBAC.

## 1. Prerequisites

Install or verify:

- .NET 9 SDK
- Azure CLI
- An Azure account that can create resources and role assignments

```powershell
dotnet --version
az version
```

The `az appconfig` commands are included in current Azure CLI versions; no separate `appconfig` extension is required.

## 2. Open the project

```powershell
cd C:\Data\Repo\oreilly-ai-200\Demo\ai200-appConfiguration
```

## 3. Sign in and define deployment values

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

$resourceGroup = "AI-200"
$location = "eastus"
$suffix = Get-Random -Minimum 100000 -Maximum 999999
$appConfigName = "oreilly-ai200-appcfg-$suffix"
$vaultName = "oreilly-ai200-ac-$suffix"
$planName = "oreilly-ai200-appcfg-s1-plan"
$appName = "oreilly-ai200-appcfg-web-$suffix"
$secretName = "app-configuration-message"
```

App Configuration store names, Key Vault names, and App Service app names must be globally unique, so random suffixes are used.

## 4. Register the resource providers

```powershell
az provider register --namespace Microsoft.AppConfiguration
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Web
```

Resource-provider registration enables the subscription to create these Azure resource types. It is normally required only once per subscription.

Check their status:

```powershell
az provider show --namespace Microsoft.AppConfiguration --query registrationState --output tsv
az provider show --namespace Microsoft.KeyVault --query registrationState --output tsv
az provider show --namespace Microsoft.Web --query registrationState --output tsv
```

Continue when all three commands return `Registered`.

## 5. Create the resource group and App Configuration store

The resource-group command is safe to run when `AI-200` already exists.

```powershell
az group create `
  --name $resourceGroup `
  --location $location

az appconfig create `
  --name $appConfigName `
  --resource-group $resourceGroup `
  --location $location `
  --sku Standard `
  --disable-local-auth true
```

Disabling local authentication prevents applications from using long-lived App Configuration access keys. This demonstration uses Microsoft Entra identities and Azure RBAC.

Save the App Configuration resource ID and endpoint:

```powershell
$appConfigId = az appconfig show `
  --name $appConfigName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

$appConfigEndpoint = az appconfig show `
  --name $appConfigName `
  --resource-group $resourceGroup `
  --query endpoint `
  --output tsv
```

## 6. Create a new Key Vault

```powershell
az keyvault create `
  --name $vaultName `
  --resource-group $resourceGroup `
  --location $location `
  --sku standard `
  --enable-rbac-authorization true `
  --enable-purge-protection true
```

Save the Key Vault resource ID:

```powershell
$vaultId = az keyvault show `
  --name $vaultName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv
```

## 7. Give your local Azure CLI identity access

The website uses `DefaultAzureCredential`. During local execution, it can authenticate as the user signed in through `az login`.

Get the signed-in user's object ID:

```powershell
$signedInUserId = az ad signed-in-user show --query id --output tsv
```

Grant the user permission to create and read App Configuration data:

```powershell
az role assignment create `
  --assignee-object-id $signedInUserId `
  --assignee-principal-type User `
  --role "App Configuration Data Owner" `
  --scope $appConfigId
```

Grant the user permission to create and read Key Vault secrets:

```powershell
az role assignment create `
  --assignee-object-id $signedInUserId `
  --assignee-principal-type User `
  --role "Key Vault Secrets Officer" `
  --scope $vaultId
```

Azure role assignments can take several minutes to become effective.

## 8. Create the direct App Configuration value

```powershell
az appconfig kv set `
  --name $appConfigName `
  --key "Demo:DirectMessage" `
  --value "Hello directly from Azure App Configuration" `
  --auth-mode login `
  --yes
```

The complete value is stored in App Configuration and can be read by identities with an App Configuration data role.

## 9. Create the Key Vault secret

```powershell
$secretId = az keyvault secret set `
  --vault-name $vaultName `
  --name $secretName `
  --value "Hello securely from Azure Key Vault" `
  --query id `
  --output tsv
```

The sensitive value is stored only in Key Vault.

## 10. Create the App Configuration Key Vault reference

```powershell
az appconfig kv set-keyvault `
  --name $appConfigName `
  --key "Demo:KeyVaultMessage" `
  --secret-identifier $secretId `
  --auth-mode login `
  --yes
```

App Configuration stores the secret identifier and a special Key Vault-reference content type. It does not store the secret value.

View the two App Configuration keys without displaying the secret value:

```powershell
az appconfig kv list `
  --name $appConfigName `
  --key "Demo:*" `
  --auth-mode login `
  --query "[].{key:key,contentType:content_type}" `
  --output table
```

## 11. Run and test the website locally

Set the App Configuration endpoint in the current PowerShell terminal. The endpoint is not a secret.

```powershell
$env:ASPNETCORE_ENVIRONMENT = "Development"
$env:Endpoints__AppConfiguration = $appConfigEndpoint

az account show --output table
dotnet restore
dotnet run
```

`ASPNETCORE_ENVIRONMENT=Development` tells the sample to skip the Azure managed-identity endpoint while running locally. `DefaultAzureCredential` can then use the user authenticated through `az login`. The `az account show` command confirms which Azure CLI account and subscription will be used.

Open `http://localhost:5190` if the browser does not open automatically. The page should show:

- **Loaded directly from Azure App Configuration** above the direct value.
- **Loaded from Key Vault through an Azure App Configuration reference** above the secret value.

Locally, `DefaultAzureCredential` uses your Azure CLI login to authenticate to both services.

The Development launch profile sets `ASPNETCORE_ENVIRONMENT` to `Development`. In that environment, the code tells `DefaultAzureCredential` to skip `ManagedIdentityCredential` because a managed-identity endpoint exists only when the app runs in Azure. The credential chain can then use your Azure CLI login. In deployed App Service, managed identity is not excluded.

## 12. Confirm that App Service supports .NET 9

```powershell
az webapp list-runtimes --os linux | Select-String "DOTNETCORE"
```

Confirm that `DOTNETCORE:9.0` appears.

## 13. Create an S1 App Service plan

```powershell
az appservice plan create `
  --name $planName `
  --resource-group $resourceGroup `
  --location $location `
  --sku S1 `
  --is-linux
```

The S1 Standard plan supplies one Linux worker by default for the website.

## 14. Create the App Service web app

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

This creates a code-based Linux web app without using a container.

## 15. Enable the App Service system-assigned identity

```powershell
$appPrincipalId = az webapp identity assign `
  --name $appName `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv
```

The managed identity lets the deployed application obtain Microsoft Entra tokens without storing credentials.

## 16. Grant the web app access to App Configuration

The website only reads configuration, so assign the least-privileged reader role:

```powershell
az role assignment create `
  --assignee-object-id $appPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role "App Configuration Data Reader" `
  --scope $appConfigId
```

## 17. Grant the web app access to Key Vault

The website only reads the referenced secret, so assign the secrets-user role:

```powershell
az role assignment create `
  --assignee-object-id $appPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role "Key Vault Secrets User" `
  --scope $vaultId
```

The web app identity needs both roles. The App Configuration role permits reading the keys and the Key Vault role permits resolving the referenced secret.

Allow several minutes for new role assignments to propagate.

## 18. Configure the App Configuration endpoint in App Service

```powershell
az webapp config appsettings set `
  --name $appName `
  --resource-group $resourceGroup `
  --settings "Endpoints__AppConfiguration=$appConfigEndpoint"
```

ASP.NET Core converts the double underscore in `Endpoints__AppConfiguration` to the configuration key `Endpoints:AppConfiguration`.

Only the service endpoint is stored in App Service settings. Authentication uses the system-assigned identity.

## 19. Publish and deploy the website

```powershell
dotnet publish .\AppConfigurationWeb.csproj `
  --configuration Release `
  --output .\publish

Compress-Archive `
  -Path .\publish\* `
  -DestinationPath .\appconfiguration-web.zip `
  -Force

az webapp deploy `
  --name $appName `
  --resource-group $resourceGroup `
  --src-path .\appconfiguration-web.zip `
  --type zip `
  --clean true
```

The ZIP contains the compiled application. App Service does not build a container or pull a container image.

## 20. Open and test the deployed website

```powershell
$hostName = az webapp show `
  --name $appName `
  --resource-group $resourceGroup `
  --query defaultHostName `
  --output tsv

"https://$hostName"
```

Open the URL and confirm that both configuration values appear. The same `DefaultAzureCredential` code now uses the App Service system-assigned identity.

## 21. View App Service logs

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

Press `Ctrl+C` to stop streaming.

## Troubleshooting

### App Configuration returns HTTP 403

Confirm that the local user has `App Configuration Data Owner` and that the App Service identity has `App Configuration Data Reader` at `$appConfigId`. Allow time for role propagation.

### Local startup tries to contact `169.254.169.254`

That address is the Azure Instance Metadata Service used by managed identities. Confirm that the app is running with the Development launch profile:

```powershell
$env:ASPNETCORE_ENVIRONMENT = "Development"
dotnet run
```

In Development, the sample excludes `ManagedIdentityCredential` and allows `DefaultAzureCredential` to use the identity from `az login`.

### Key Vault returns HTTP 403

Confirm that the local user has `Key Vault Secrets Officer` and that the App Service identity has `Key Vault Secrets User` at `$vaultId`.

### The endpoint setting is missing

Locally, set `$env:Endpoints__AppConfiguration = $appConfigEndpoint` before `dotnet run`. For App Service, repeat step 18 and restart the app.

### The direct value loads but the Key Vault value fails

This indicates that the identity can read App Configuration but cannot resolve the Key Vault reference. Check the Key Vault role assignment and confirm that `Demo:KeyVaultMessage` references the secret created in step 9.

## Microsoft Learn references

- [Azure App Configuration overview](https://learn.microsoft.com/azure/azure-app-configuration/overview)
- [Create an Azure App Configuration store](https://learn.microsoft.com/azure/azure-app-configuration/quickstart-azure-app-configuration-create)
- [.NET configuration provider for Azure App Configuration](https://learn.microsoft.com/azure/azure-app-configuration/reference-dotnet-provider)
- [Use Key Vault references in an ASP.NET Core app](https://learn.microsoft.com/azure/azure-app-configuration/use-key-vault-references-dotnet-core)
- [Use managed identities to access App Configuration](https://learn.microsoft.com/azure/azure-app-configuration/howto-integrate-azure-managed-service-identity)
- [Access Azure App Configuration using Microsoft Entra ID](https://learn.microsoft.com/azure/azure-app-configuration/concept-enable-rbac)
- [Use Azure RBAC to grant access to Key Vault](https://learn.microsoft.com/azure/key-vault/general/rbac-guide)
- [Authenticate .NET apps with DefaultAzureCredential](https://learn.microsoft.com/dotnet/azure/sdk/authentication/credential-chains)
- [Deploy an ASP.NET Core web app to Azure App Service](https://learn.microsoft.com/azure/app-service/quickstart-dotnetcore)
