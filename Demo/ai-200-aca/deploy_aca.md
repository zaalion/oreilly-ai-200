# Deploy `ai200-webapp` to Azure Container Apps

This guide creates an Azure Container Apps environment, deploys a public container app, pulls the `ai200-webapp:latest` image from the existing Azure Container Registry, and retrieves the application URL.

| Resource | Value |
| --- | --- |
| Resource group | `AI-200` |
| Container registry | `oreillyacrai200` |
| Registry server | `oreillyacrai200.azurecr.io` |
| Container image | `oreillyacrai200.azurecr.io/ai200-webapp:latest` |
| Application target port | `8080` |

## 1. Sign in and prepare Azure CLI

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"

az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights
```

Define the values used by the remaining commands. Replace the two names enclosed in angle brackets.

```powershell
$resourceGroup = "AI-200"
$location = "canadacentral"
$environmentName = "oreilly-acae-ai200-cc"
$containerAppName = "oreilly-aca-ai200-cc"

$registryName = "oreillyacrai200"
$registryServer = "oreillyacrai200.azurecr.io"
$imageName = "ai200-webapp"
$imageTag = "latest"
$image = "${registryServer}/${imageName}:${imageTag}"
$identityName = "${containerAppName}-acr-pull-id"
```

Example names are `oreilly-aca-ai200-env` for the environment and `ai200-webapp` for the container app. A container app name must be unique within its Container Apps environment.

## 2. Confirm that the image exists in ACR

```powershell
az acr repository show `
  --name $registryName `
  --repository $imageName `
  --output table

az acr repository show-tags `
  --name $registryName `
  --repository $imageName `
  --detail `
  --output table
```

Confirm that the tag list includes `latest`.

## 3. Create the Container Apps environment

A Container Apps environment is the boundary that contains one or more container apps.

```powershell
az containerapp env create `
  --name $environmentName `
  --resource-group $resourceGroup `
  --location $location
```

Verify that the environment was created:

```powershell
az containerapp env show `
  --name $environmentName `
  --resource-group $resourceGroup `
  --output table
```

## 4. Create an identity that can pull from ACR

Create a user-assigned managed identity:

```powershell
$identityId = az identity create `
  --name $identityName `
  --resource-group $resourceGroup `
  --location $location `
  --query id `
  --output tsv

$identityPrincipalId = az identity show `
  --name $identityName `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv
```

Get the registry resource ID and grant the identity permission to pull images:

```powershell
$registryId = az acr show `
  --name $registryName `
  --query id `
  --output tsv

az role assignment create `
  --assignee-object-id $identityPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role AcrPull `
  --scope $registryId
```

The person running this command must have permission to create Azure role assignments.

Verify that ACR accepts Azure Resource Manager authentication tokens:

```powershell
az acr config authentication-as-arm show `
  --registry $registryName `
  --query status `
  --output tsv
```

If the result is `disabled`, enable it:

```powershell
az acr config authentication-as-arm update `
  --registry $registryName `
  --status enabled
```

## 5. Create the public container app

The image listens on port `8080`. The `--ingress external` option makes the container app accessible from the public internet.

```powershell
az containerapp create `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --environment $environmentName `
  --image $image `
  --ingress external `
  --target-port 8080 `
  --user-assigned $identityId `
  --registry-server $registryServer `
  --registry-identity $identityId `
  --min-replicas 1
```

The managed identity authenticates to ACR, so registry usernames and passwords are not stored in the container app.

## 6. Verify the deployment

Check the container app and its revisions:

```powershell
az containerapp show `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --output table

az containerapp revision list `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --output table
```

View the application logs if the revision does not become healthy:

```powershell
az containerapp logs show `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --type console `
  --follow
```

Press `Ctrl+C` to stop following the logs.

## 7. Grant Foundry access to ACA

Use the `$identityName` value defined in Step 1 to retrieve the identity details:

```powershell
$identityClientId = az identity show `
  --name $identityName `
  --resource-group $resourceGroup `
  --query clientId `
  --output tsv

$identityPrincipalId = az identity show `
  --name $identityName `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv

$foundryId = az cognitiveservices account show `
  --resource-group $resourceGroup `
  --name oreilly-foundry-ai200 `
  --query id `
  --output tsv

az role assignment create `
  --assignee-object-id $identityPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role "Cognitive Services OpenAI User" `
  --scope $foundryId

az containerapp update `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --set-env-vars "AZURE_CLIENT_ID=$identityClientId"
```

## 8. Get the public application URL

Retrieve the fully qualified domain name assigned to the container app:

```powershell
$fqdn = az containerapp show `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --query properties.configuration.ingress.fqdn `
  --output tsv

$appUrl = "https://$fqdn"
Write-Output $appUrl
```

Open the displayed HTTPS URL in a web browser.

## Troubleshooting

Check the configured image, ingress, and registry settings:

```powershell
az containerapp show `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --query "{image:properties.template.containers[0].image, ingress:properties.configuration.ingress, registries:properties.configuration.registries}" `
  --output json
```

Common problems include:

- The revision cannot pull the image: verify the image name, the `latest` tag, the managed identity, and its `AcrPull` role assignment.
- The app is unavailable: verify that ingress is external and the target port is `8080`.
- The container starts and then stops: inspect the console logs for application errors.

## References

- [Create an Azure Container Apps environment](https://learn.microsoft.com/cli/azure/containerapp/env)
- [Pull an ACR image with a managed identity](https://learn.microsoft.com/azure/container-apps/managed-identity-image-pull)
- [Configure ingress in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/ingress-how-to)
