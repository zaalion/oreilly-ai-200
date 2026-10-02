# Build and Push to Azure Container Registry

This project targets .NET 8. The steps below create a Linux container image and publish it to `oreillyacrai200.azurecr.io`.

## Prerequisites

1. Install Azure CLI.
2. Have an Azure account with permission to create resources and build images in Azure Container Registry.
3. This remote ACR build does not require Docker Desktop, a local Docker daemon, or the .NET SDK on your machine.

## 1. Add the Dockerfile

Create a file named `Dockerfile` in this project directory, next to `ai200-webapp.csproj`, with the following contents:

```dockerfile
FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

COPY ["ai200-webapp.csproj", "./"]
RUN dotnet restore "ai200-webapp.csproj"

COPY . .
RUN dotnet publish "ai200-webapp.csproj" -c Release -o /app/publish /p:UseAppHost=false

FROM mcr.microsoft.com/dotnet/aspnet:8.0 AS final
WORKDIR /app
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
COPY --from=build /app/publish .
ENTRYPOINT ["dotnet", "ai200-webapp.dll"]
```

The first stage restores and publishes the application. The smaller ASP.NET runtime image is used to run the published output, listening on container port `8080`.

## 2. Sign in and select the subscription

Run these Azure CLI commands in PowerShell or another terminal:

```powershell
az login
az account set --subscription "<subscription-id-or-name>"
az account show --output table
```

Replace `<subscription-id-or-name>` with the subscription where the registry will be created. `az login` authenticates the CLI, and `az account set` ensures subsequent registry commands target the right subscription.

Define the resource values used by the remaining commands:

```powershell
$resourceGroup = "AI-200"
$location = "eastus"
$acrName = "oreillyacrai200"
$suffix = Get-Random -Minimum 100000 -Maximum 999999
$planName = "oreilly-ai200-container-s1-plan"
$webAppName = "oreilly-ai200-webapp-$suffix"
```

## 3. Create Azure Container Registry

Create the resource group if it does not already exist:

```powershell
az group create `
  --name $resourceGroup `
  --location $location
```

Create a Basic-tier Azure Container Registry:

```powershell
az acr create `
  --name $acrName `
  --resource-group $resourceGroup `
  --location $location `
  --sku Basic
```

Azure Container Registry names must be globally unique and contain only letters and numbers. If `oreillyacrai200` already exists in `AI-200`, skip the `az acr create` command and continue. If the name belongs to another Azure customer, choose a different globally unique registry name and use it throughout the remaining commands.

Confirm the registry and its login server:

```powershell
az acr show `
  --name $acrName `
  --resource-group $resourceGroup `
  --query "{name:name,loginServer:loginServer,sku:sku.name}" `
  --output table
```

## 4. Build and push with Azure CLI

From this project directory (`ai200-webapp`), run:

```powershell
az acr show --name $acrName --query "loginServer" --output tsv
az acr build --registry $acrName --image ai200-webapp:latest .
```

The first command confirms the registry's login server. The second sends the current directory as the build context, builds the image using the `Dockerfile`, and pushes it to `oreillyacrai200.azurecr.io/ai200-webapp:latest`. The build runs in Azure Container Registry, so no local Docker engine or Docker Desktop is needed. The signed-in Azure identity must have the required ACR build/push permissions.

To publish a versioned tag instead of (or in addition to) `latest`, replace `latest` with a version such as `1.0.0` in the `--image` value.

## 5. Verify the image in ACR

```powershell
az acr repository show --name $acrName --repository ai200-webapp --output table
az acr repository show-tags --name $acrName --repository ai200-webapp --output table
```

These commands confirm the repository exists and list its published tags.

## 6. Create an App Service plan and web app

Create a Linux S1 App Service plan:

```powershell
az appservice plan create `
  --name $planName `
  --resource-group $resourceGroup `
  --location $location `
  --sku S1 `
  --is-linux
```

Create the web app initially with the .NET 8 Linux runtime. A later step changes it to use the private container image:

```powershell
az webapp create `
  --name $webAppName `
  --resource-group $resourceGroup `
  --plan $planName `
  --runtime "DOTNETCORE:8.0"
```

App Service app names must be globally unique. The random suffix makes `$webAppName` unique and becomes part of the website URL.

## 7. Give the web app permission to pull from ACR

Enable the web app's system-assigned managed identity and save its principal ID:

```powershell
$webAppPrincipalId = az webapp identity assign `
  --name $webAppName `
  --resource-group $resourceGroup `
  --query principalId `
  --output tsv
```

Read the registry resource ID:

```powershell
$acrId = az acr show `
  --name $acrName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv
```

Assign the `AcrPull` role to the web app identity at the registry scope:

```powershell
az role assignment create `
  --assignee-object-id $webAppPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role "AcrPull" `
  --scope $acrId
```

`AcrPull` allows the web app identity to download images but does not allow it to push or delete images.

App Service uses Azure Resource Manager audience tokens when it authenticates to ACR. Check the registry setting and enable it if necessary:

```powershell
az acr config authentication-as-arm show `
  --registry $acrName

az acr config authentication-as-arm update `
  --registry $acrName `
  --status enabled
```

## 8. Configure App Service to pull and run the image

Tell App Service to use its managed identity when it authenticates to ACR:

```powershell
$webAppConfigId = az webapp config show `
  --name $webAppName `
  --resource-group $resourceGroup `
  --query id `
  --output tsv

az resource update `
  --ids $webAppConfigId `
  --set properties.acrUseManagedIdentityCreds=true
```

Read the registry login server and build the complete image name:

```powershell
$acrLoginServer = az acr show `
  --name $acrName `
  --resource-group $resourceGroup `
  --query loginServer `
  --output tsv

$imageName = "$acrLoginServer/ai200-webapp:latest"
```

Configure the web app to pull this private image:

```powershell
az webapp config container set `
  --name $webAppName `
  --resource-group $resourceGroup `
  --container-image-name $imageName `
  --container-registry-url "https://$acrLoginServer"
```

The Dockerfile configures the application to listen on port `8080`. Tell App Service to route website traffic to that container port:

```powershell
az webapp config appsettings set `
  --name $webAppName `
  --resource-group $resourceGroup `
  --settings WEBSITES_PORT=8080
```

Restart the web app so App Service starts a container and pulls the image:

```powershell
az webapp restart `
  --name $webAppName `
  --resource-group $resourceGroup
```

The first container start downloads all image layers. On later restarts, App Service checks the configured tag and downloads only layers that changed.

## 9. Open the website and inspect the container logs

Get the website URL:

```powershell
$hostName = az webapp show `
  --name $webAppName `
  --resource-group $resourceGroup `
  --query defaultHostName `
  --output tsv

"https://$hostName"
```

Enable container logging and stream the startup output:

```powershell
az webapp log config `
  --name $webAppName `
  --resource-group $resourceGroup `
  --docker-container-logging filesystem

az webapp log tail `
  --name $webAppName `
  --resource-group $resourceGroup
```

The logs show whether App Service authenticated to ACR, pulled the image, created the container, and started the ASP.NET Core application. Press `Ctrl+C` to stop streaming logs.

## 10. Pull a newly built `latest` image

After changing the application, build and push a new image with the same tag:

```powershell
az acr build `
  --registry $acrName `
  --image ai200-webapp:latest `
  .
```

Restart the web app to make it check ACR and pull the updated `latest` image:

```powershell
az webapp restart `
  --name $webAppName `
  --resource-group $resourceGroup
```

App Service does not continuously poll ACR for changes. Restarting creates a new container startup, which causes App Service to check the configured image tag and retrieve changed layers.

## Azure Container Registry Tasks

Azure Container Registry (ACR) Tasks is ACR's cloud-based service for building and managing container images. It can build images from source in Azure without requiring a local Docker engine, then push the images to a registry.

The `az acr build` command above used an ACR Task as a one-off quick build: Azure uploaded this project's build context, built the image from its Dockerfile, and pushed `ai200-webapp:latest` to the registry. This command runs a quick task; it does not create a persistent named task.

Other common ACR Task use cases include:

- Automatically rebuild and push an image when source code changes in a Git repository.
- Build and publish images on a schedule, such as regularly refreshing a base image.
- Run multi-step build workflows that test, build, and publish one or more images.
- Trigger image builds when a base image is updated, helping keep derived images current.

## References

- [Introduction to Azure Container Registry](https://learn.microsoft.com/azure/container-registry/container-registry-intro)
- [Tutorial: Build and run a custom image in Azure App Service](https://learn.microsoft.com/azure/app-service/tutorial-custom-container)
- [ACR Tasks overview](https://learn.microsoft.com/azure/container-registry/container-registry-tasks-overview)
- [Quick task: Build and push an image using Azure CLI](https://learn.microsoft.com/azure/container-registry/container-registry-tutorial-quick-task)
