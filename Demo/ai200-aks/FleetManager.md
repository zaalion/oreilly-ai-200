# Azure Kubernetes Fleet Manager

Azure Kubernetes Fleet Manager is an optional management layer for operating multiple Kubernetes clusters as one fleet.

It provides capabilities such as:

- Grouping AKS clusters across subscriptions and regions
- Coordinating Kubernetes and node-image upgrades
- Rolling upgrades through cluster groups and stages
- Deploying Kubernetes resources across selected clusters
- Managing namespaces and policies across clusters
- Centralized monitoring
- Multi-cluster DNS load balancing and networking

## Why Fleet Manager is not mandatory

An AKS cluster is fully functional by itself. AKS already provides its own Kubernetes control plane, nodes, networking, scaling, security, and upgrades.

Fleet Manager does not provide a dependency required for normal cluster operation. It coordinates multiple independent clusters.

## Fleet Manager configurations

| Configuration | Capabilities |
| --- | --- |
| Without a hub cluster | Groups clusters and coordinates upgrades; currently no additional Fleet Manager charge |
| With a hub cluster | Adds workload placement, managed namespaces, and multi-cluster networking; provisions a separate single-node Standard-tier AKS hub with associated costs |

For a single AKS cluster, Fleet Manager generally adds no necessary functionality. It becomes relevant when several clusters must be operated consistently as a group.

## References

- [Azure Kubernetes Fleet Manager overview](https://learn.microsoft.com/azure/kubernetes-fleet/overview)
- [Choosing an Azure Kubernetes Fleet Manager option](https://learn.microsoft.com/azure/kubernetes-fleet/concepts-choosing-fleet)
