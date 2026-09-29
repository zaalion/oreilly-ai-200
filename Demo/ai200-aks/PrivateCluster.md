# Private AKS Clusters

The **Enable private cluster** option controls network access to the Kubernetes API server. The API server is the endpoint used by `kubectl`, CI/CD pipelines, and cluster-management tools.

## Public AKS cluster

When private-cluster access is disabled, the Kubernetes API server has a public endpoint.

```text
Your computer -> Internet -> AKS API server
```

After obtaining credentials, a user can run `kubectl` from a computer with Internet connectivity. The **Set authorized IP ranges** option can restrict the public endpoint to specific IP addresses or CIDR ranges.

## Private AKS cluster

When private-cluster access is enabled, the API server receives a private endpoint and private IP address inside the Azure virtual network.

```text
Connected network -> Private endpoint -> AKS API server
```

The API server has no public IP address. A client running `kubectl` must have network access to the cluster virtual network through a supported connection method, such as:

- A virtual machine in the same or a peered virtual network
- A self-hosted CI/CD agent in the connected network
- VPN or ExpressRoute
- Azure Bastion
- Azure Cloud Shell deployed into a connected virtual network
- `az aks command invoke` for supported operations

Private DNS is used so the API server hostname resolves to its private IP address.

## Scope of private-cluster access

The private-cluster option makes the **Kubernetes API server** private. It does not automatically make applications deployed in the cluster private.

For example, a Kubernetes `Service` with type `LoadBalancer` can still receive a public IP address unless it is configured as an internal load balancer.

A private cluster reduces exposure of the cluster-management endpoint and requires private networking and DNS connectivity for administrators and automation.

## References

- [Create a private AKS cluster](https://learn.microsoft.com/azure/aks/private-clusters)
- [Connect to a private AKS cluster](https://learn.microsoft.com/azure/aks/private-cluster-connect)
