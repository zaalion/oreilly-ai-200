# Azure Container Apps Revisions

An Azure Container Apps revision is an immutable snapshot of a container app version.

When a container app is created, Azure automatically creates its first revision. When a revision-level setting changes, Azure creates another revision instead of modifying the existing revision.

Examples of changes that create a revision include:

- Changing the container image or image tag
- Adding or changing an environment variable
- Changing CPU or memory settings
- Changing scaling rules
- Changing a container command or arguments

For example, this command changes an environment variable and therefore creates a new revision:

```powershell
az containerapp update `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --set-env-vars "AZURE_CLIENT_ID=$identityClientId"
```

## Why revisions are useful

Revisions allow Azure Container Apps to:

- Keep the previous version while a new version starts
- Return to an earlier version if a deployment fails
- Run multiple versions at the same time
- Divide incoming traffic between versions
- Give a specific revision its own label and URL

## Single revision mode

Single revision mode is the default.

When a new revision becomes ready, Azure sends traffic to it and deactivates the previous revision. If the new revision fails to become ready, traffic remains on the previous working revision.

```text
Container app
├── Revision 1: inactive
└── Revision 2: active and receiving traffic
```

Set single revision mode with:

```powershell
az containerapp revision set-mode `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --mode single
```

## Multiple revision mode

Multiple revision mode allows more than one revision to remain active. Incoming traffic can be divided between the active revisions.

```text
Container app
├── Revision 1: active, receives 80% of traffic
└── Revision 2: active, receives 20% of traffic
```

This mode can be used to test a new version with part of the traffic before sending all users to it.

Set multiple revision mode with:

```powershell
az containerapp revision set-mode `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --mode multiple
```

## View revisions

List all revisions for the container app:

```powershell
az containerapp revision list `
  --name $containerAppName `
  --resource-group $resourceGroup `
  --output table
```

The output shows information such as the revision name, whether it is active, and when it was created.

## Active and inactive revisions

- An active revision can run replicas and receive traffic.
- An inactive revision does not run containers or receive traffic, but it can be activated again.

Activate a revision:

```powershell
az containerapp revision activate `
  --name <revision-name> `
  --resource-group $resourceGroup
```

Deactivate a revision:

```powershell
az containerapp revision deactivate `
  --name <revision-name> `
  --resource-group $resourceGroup
```

## Restart a revision

Restarting a revision restarts its replicas. It does not create a new revision because the application configuration has not changed.

```powershell
az containerapp revision restart `
  --name <revision-name> `
  --resource-group $resourceGroup
```

## Application-level changes

Some settings apply to the entire container app and do not create a revision. These include:

- Revision mode
- Ingress configuration
- Traffic-splitting rules
- Revision labels
- Registry credentials
- Secret values

Although changing a secret value does not create a revision, existing revisions must be restarted before their containers read the new value.

## Microsoft Learn references

- [Update and deploy changes in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/revisions)
- [Manage revisions in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/revisions-manage)
- [Traffic splitting in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/traffic-splitting)
- [Application lifecycle management in Azure Container Apps](https://learn.microsoft.com/azure/container-apps/application-lifecycle-management)
