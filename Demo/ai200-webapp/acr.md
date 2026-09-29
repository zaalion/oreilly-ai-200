# Build and Push to Azure Container Registry

This project targets .NET 8. The steps below create a Linux container image and publish it to `oreillyacrai200.azurecr.io`.

## Prerequisites

1. Install Azure CLI.
2. Have an Azure account with access to the subscription containing `oreillyacrai200`.
3. Confirm the `oreillyacrai200` registry exists and that your account has permission to build and push images. This remote ACR build does not require Docker Desktop, a local Docker daemon, or the .NET SDK on your machine.

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

Replace `<subscription-id-or-name>` with the subscription that contains `oreillyacrai200`. `az login` authenticates the CLI, and `az account set` ensures subsequent registry commands target the right subscription.

## 3. Build and push with Azure CLI

From this project directory (`az200-webapp`), run:

```powershell
az acr show --name oreillyacrai200 --query "loginServer" --output tsv
az acr build --registry oreillyacrai200 --image ai200-webapp:latest .
```

The first command confirms the registry's login server. The second sends the current directory as the build context, builds the image using the `Dockerfile`, and pushes it to `oreillyacrai200.azurecr.io/ai200-webapp:latest`. The build runs in Azure Container Registry, so no local Docker engine or Docker Desktop is needed. The signed-in Azure identity must have the required ACR build/push permissions.

To publish a versioned tag instead of (or in addition to) `latest`, replace `latest` with a version such as `1.0.0` in the `--image` value.

## Verify the image in ACR

```powershell
az acr repository show --name oreillyacrai200 --repository ai200-webapp --output table
az acr repository show-tags --name oreillyacrai200 --repository ai200-webapp --output table
```

These commands confirm the repository exists and list its published tags.

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