# Azure Container Apps Environments

An Azure Container Apps environment is a secure boundary that contains one or more container apps and jobs.

```text
Container Apps environment
├── Container app A
│   ├── Revision 1
│   └── Revision 2
├── Container app B
└── Container Apps job
```

Azure manages the environment infrastructure, including operating-system updates, scaling operations, failover, and resource balancing.

## Purpose of an environment

A Container Apps environment provides the shared foundation used by its container apps:

- **Network boundary:** Apps in the environment use the environment's virtual network.
- **Application grouping:** Related container apps and jobs can be placed together.
- **Internal communication:** Apps in the same environment can communicate privately by using internal names and endpoints.
- **Centralized logging:** Apps can send their logs to the same logging destination, such as a Log Analytics workspace.
- **Compute selection:** Workload profiles determine which compute resources are available to the apps.
- **Dapr configuration:** Apps in the same environment can use shared Dapr components and service invocation.

The environment does not contain the application image. Each container app specifies its own image, revisions, ingress, scaling rules, CPU, and memory.

## Environment types

Azure Container Apps has two environment types:

| Type | Description |
| --- | --- |
| Workload profiles environment | The default environment type. It supports Consumption and Dedicated workload profiles and provides the current networking capabilities. |
| Consumption-only environment | The legacy environment type. It supports only the Consumption plan. |

The environment created by this command is a workload profiles environment:

```powershell
az containerapp env create `
  --name $environmentName `
  --resource-group $resourceGroup `
  --location $location
```

## Workload profiles

A workload profile defines the compute available to container apps in the environment.

- A **Consumption** profile uses serverless compute, supports automatic scaling, and can scale an app to zero.
- A **Dedicated** profile provides dedicated compute with a selected CPU and memory size.

Different container apps in one environment can use different workload profiles when those profiles have been added to the environment.

## Networking

Every Container Apps environment has a virtual network boundary. Azure can create the network automatically, or the environment can be connected to a virtual network supplied during environment creation.

Ingress is configured separately for each container app:

- **External ingress** makes a container app available through a public endpoint.
- **Internal ingress** makes it available only within the Container Apps environment and connected network.
- **No ingress** is suitable for applications that do not accept incoming network requests.

Container apps in the same environment can communicate without exposing every service to the public internet.

## Logging

The environment controls the shared log destination for its container apps. Depending on its logging configuration, logs can be sent to:

- A Log Analytics workspace
- Azure Monitor through diagnostic settings
- No persistent log destination

Console and system logs from multiple apps in the same environment can therefore be queried centrally.

## One environment or multiple environments

A single environment can contain related applications that should share networking, logging, Dapr configuration, and environment-level infrastructure.

Separate environments provide stronger isolation when applications must not share compute or networking, or when development, testing, and production resources must be kept separate.

Container apps in different environments cannot use the built-in cross-app Dapr service invocation available inside one environment.

## Environment and container app relationship

Creating an environment does not deploy an application. After the environment exists, a container app is created inside it:

```powershell
az containerapp create `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --environment $environmentName `
  --image $image `
  --ingress external `
  --target-port 8080
```

Multiple container apps can reference the same `$environmentName`.

## View the environment

Show the environment details:

```powershell
az containerapp env show `
  --name $environmentName `
  --resource-group $resourceGroup `
  --output table
```

List all Container Apps environments in the resource group:

```powershell
az containerapp env list `
  --resource-group $resourceGroup `
  --output table
```

## Microsoft Learn references

- [Azure Container Apps environments](https://learn.microsoft.com/azure/container-apps/environment)
- [Compute and billing structures in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/structure)
- [Workload profiles in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/workload-profiles-overview)
- [Networking in an Azure Container Apps environment](https://learn.microsoft.com/azure/container-apps/networking)
- [Create and manage a Container Apps environment](https://learn.microsoft.com/cli/azure/containerapp/env)
