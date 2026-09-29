# AKS Authentication and Authorization

The AKS authentication and authorization setting controls two separate questions:

1. **Authentication:** Who are you?
2. **Authorization:** What are you allowed to do inside the Kubernetes cluster?

## Available options

| Option | Authentication: who are you? | Authorization: what can you do? |
| --- | --- | --- |
| Local accounts with Kubernetes RBAC | AKS-issued local credentials and certificates | Kubernetes `Role`, `ClusterRole`, `RoleBinding`, and `ClusterRoleBinding` objects |
| Microsoft Entra ID authentication with Kubernetes RBAC | Microsoft Entra user, group, or application identity | Kubernetes RBAC objects stored inside the cluster |
| Microsoft Entra ID authentication with Azure RBAC | Microsoft Entra identity | Azure role assignments |

## Local accounts with Kubernetes RBAC

Users obtain AKS-generated Kubernetes credentials. These are cluster-local credentials rather than individual Microsoft Entra identities. Kubernetes checks permissions using native Kubernetes RBAC resources.

A local administrator credential can provide direct cluster-admin access and bypass Microsoft Entra authentication. In this context, **local** refers to credentials belonging to the cluster, not to a Windows or Linux local user account.

## Microsoft Entra ID authentication with Kubernetes RBAC

Users authenticate using their organizational Microsoft Entra identities, normally through `kubelogin`.

After authentication, Kubernetes decides what each identity can do. Administrators create Kubernetes role bindings that associate Microsoft Entra users or groups with Kubernetes roles.

```yaml
kind: RoleBinding
subjects:
  - kind: Group
    name: "<Microsoft-Entra-group-object-ID>"
```

The identities are centrally managed in Microsoft Entra ID, but permissions are configured inside each Kubernetes cluster.

## Microsoft Entra ID authentication with Azure RBAC

Users authenticate with Microsoft Entra ID, and authorization is managed through Azure role assignments.

AKS provides roles including:

- Azure Kubernetes Service RBAC Reader
- Azure Kubernetes Service RBAC Writer
- Azure Kubernetes Service RBAC Admin
- Azure Kubernetes Service RBAC Cluster Admin

Assignments can be scoped to an individual namespace or cluster, or inherited from a resource group, subscription, or management group. This supports centralized access management across multiple clusters.

AKS Automatic uses Microsoft Entra authentication with Azure RBAC as its preconfigured model.

## Azure resource access and Kubernetes API access

Permission to manage the AKS resource in Azure is separate from permission to use the Kubernetes API. For example, Azure `Contributor` access might allow someone to update the AKS resource without allowing that person to create pods through `kubectl`.

## Selection for a simple starter demo

For a simple starter demo, choose **Local accounts with Kubernetes RBAC**.

This option has the fewest prerequisites:

- No Microsoft Entra groups or Kubernetes-specific Azure role assignments
- A simple `az aks get-credentials` workflow
- A standard `kubectl` experience
- The ability to introduce native Kubernetes RBAC later

Use local accounts for temporary, nonproduction clusters. If multiple students share one cluster and should sign in using their own identities, use **Microsoft Entra ID authentication with Kubernetes RBAC** instead.

## References

- [Access and identity options for AKS](https://learn.microsoft.com/azure/aks/concepts-identity)
- [AKS cluster authorization concepts](https://learn.microsoft.com/azure/aks/concepts-cluster-authorization)
- [Use Kubernetes RBAC with Microsoft Entra ID in AKS](https://learn.microsoft.com/azure/aks/azure-ad-rbac)
