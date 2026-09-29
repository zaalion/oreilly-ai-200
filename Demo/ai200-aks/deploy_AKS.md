# Deploy `ai200-webapp` from ACR to AKS

This guide deploys the following container image to the existing AKS cluster:

| Resource | Value |
| --- | --- |
| Resource group | `AI-200` |
| AKS cluster | `oreilly-aks-ai200` |
| ACR name | `oreillyacrai200` |
| ACR login server | `oreillyacrai200.azurecr.io` |
| Image | `oreillyacrai200.azurecr.io/ai200-webapp:latest` |

The cluster kubelet identity already has the `AcrPull` role on this registry, so the cluster is authorized to pull the image.

Run the commands in this guide from `C:\Data\Repo\oreilly-ai-200\Demo\ai200-aks`.

## 1. Sign in to Azure

```powershell
az login
az account set --subscription "19969c81-e8ff-4585-8c2f-3f196b588227"
az account show --output table
```

## 2. Confirm that the image exists in ACR

```powershell
az acr repository show `
  --name oreillyacrai200 `
  --repository ai200-webapp `
  --output table

az acr repository show-tags `
  --name oreillyacrai200 `
  --repository ai200-webapp `
  --detail `
  --output table
```

The tag list should include `latest`.

## 3. Verify AKS access to ACR

The AKS kubelet identity needs permission to pull images from ACR. Verify its role assignment:

```powershell
$kubeletObjectId = az aks show `
  --resource-group AI-200 `
  --name oreilly-aks-ai200 `
  --query "identityProfile.kubeletidentity.objectId" `
  --output tsv

$acrId = az acr show `
  --name oreillyacrai200 `
  --query id `
  --output tsv

az role assignment list `
  --assignee-object-id $kubeletObjectId `
  --scope $acrId `
  --query "[].roleDefinitionName" `
  --output table
```

The output should include `AcrPull`. If it is missing, attach the existing registry to the cluster:

```powershell
az aks update `
  --resource-group AI-200 `
  --name oreilly-aks-ai200 `
  --attach-acr oreillyacrai200
```

The identity running this command must be allowed to create Azure role assignments.

## 4. Connect `kubectl` to the cluster

```powershell
az aks get-credentials `
  --resource-group AI-200 `
  --name oreilly-aks-ai200 `
  --overwrite-existing

kubectl config current-context
kubectl get nodes
```

Confirm that the current context and nodes belong to `oreilly-aks-ai200` before applying the deployment.

## 5. Configure a workload identity for Foundry access

The application uses `DefaultAzureCredential` to call the Foundry model. In AKS, the pod therefore needs a Microsoft Entra workload identity with the `Cognitive Services OpenAI User` role on the Foundry resource.

Create a user-assigned managed identity:

```powershell
$identityName = "oreilly-aks-ai200-webapp-id"

az identity create `
  --resource-group AI-200 `
  --name $identityName

$identityClientId = az identity show `
  --resource-group AI-200 `
  --name $identityName `
  --query clientId `
  --output tsv

$identityPrincipalId = az identity show `
  --resource-group AI-200 `
  --name $identityName `
  --query principalId `
  --output tsv
```

Assign model-inference permission to the identity:

```powershell
$foundryResourceId = az cognitiveservices account show `
  --resource-group AI-200 `
  --name oreilly-foundry-ai200 `
  --query id `
  --output tsv

az role assignment create `
  --assignee-object-id $identityPrincipalId `
  --assignee-principal-type ServicePrincipal `
  --role "Cognitive Services OpenAI User" `
  --scope $foundryResourceId
```

Create a federated credential that connects the Kubernetes service account to the managed identity:

```powershell
$oidcIssuer = az aks show `
  --resource-group AI-200 `
  --name oreilly-aks-ai200 `
  --query "oidcIssuerProfile.issuerUrl" `
  --output tsv

az identity federated-credential create `
  --resource-group AI-200 `
  --identity-name $identityName `
  --name ai200-webapp-federated `
  --issuer $oidcIssuer `
  --subject "system:serviceaccount:ai200:ai200-webapp" `
  --audiences "api://AzureADTokenExchange"
```

Keep `$identityClientId` available for the manifest in the next step.

## 6. Create the Kubernetes manifest

Create a file named `ai200-webapp.yaml`. Replace `<identity-client-id>` with the value stored in `$identityClientId`.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ai200
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai200-webapp
  namespace: ai200
  annotations:
    azure.workload.identity/client-id: "<identity-client-id>"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai200-webapp
  namespace: ai200
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai200-webapp
  template:
    metadata:
      labels:
        app: ai200-webapp
        azure.workload.identity/use: "true"
    spec:
      serviceAccountName: ai200-webapp
      containers:
        - name: ai200-webapp
          image: oreillyacrai200.azurecr.io/ai200-webapp:latest
          imagePullPolicy: Always
          ports:
            - name: http
              containerPort: 8080
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /
              port: http
            initialDelaySeconds: 15
            periodSeconds: 20
---
apiVersion: v1
kind: Service
metadata:
  name: ai200-webapp
  namespace: ai200
spec:
  type: LoadBalancer
  selector:
    app: ai200-webapp
  ports:
    - name: http
      port: 80
      targetPort: http
```

`imagePullPolicy: Always` makes Kubernetes check ACR for the current digest assigned to the mutable `latest` tag whenever a new pod starts.

## 7. Deploy the application

```powershell
kubectl apply -f .\ai200-webapp.yaml

kubectl rollout status `
  deployment/ai200-webapp `
  --namespace ai200

kubectl get pods `
  --namespace ai200 `
  --output wide
```

The pod should reach the `Running` state and show `1/1` in the `READY` column.

## 8. Access the website

The `LoadBalancer` service requests a public IP address from Azure. Watch the service until `EXTERNAL-IP` changes from `<pending>` to an IP address:

```powershell
kubectl get service ai200-webapp `
  --namespace ai200 `
  --watch
```

Press `Ctrl+C` after the external IP appears. Retrieve it again if needed:

```powershell
$externalIp = kubectl get service ai200-webapp `
  --namespace ai200 `
  --output jsonpath="{.status.loadBalancer.ingress[0].ip}"

Write-Output "http://$externalIp"
```

Open the displayed URL in a browser:

```text
http://<external-ip>
```

The service accepts traffic on port `80` and forwards it to port `8080` in the application container.

## 9. Deploy a newer `latest` image

After building and pushing an updated image to the same ACR tag, restart the Kubernetes deployment so new pods resolve the current `latest` digest:

```powershell
az acr build `
  --registry oreillyacrai200 `
  --image ai200-webapp:latest `
  ..\ai200-webapp

kubectl rollout restart `
  deployment/ai200-webapp `
  --namespace ai200

kubectl rollout status `
  deployment/ai200-webapp `
  --namespace ai200
```

The `LoadBalancer` service remains in place, so the website continues to use the same external IP while the deployment replaces its pod.

## Troubleshooting

View the application state:

```powershell
kubectl get all --namespace ai200
kubectl describe pod --namespace ai200 --selector app=ai200-webapp
kubectl logs --namespace ai200 --selector app=ai200-webapp --tail 100
kubectl get events --namespace ai200 --sort-by=.metadata.creationTimestamp
```

Common states include:

- `ImagePullBackOff`: AKS can't authenticate to ACR, or the repository or tag doesn't exist.
- `CrashLoopBackOff`: The image starts and then exits. Inspect the pod logs.
- `EXTERNAL-IP` remains `<pending>`: Azure is still provisioning the public load balancer address, or the cluster has a load-balancer configuration problem.
- The page loads but model requests fail: Verify the service-account annotation, workload-identity pod label, federated credential subject, and `Cognitive Services OpenAI User` role assignment.

## References

- [Integrate Azure Container Registry with AKS](https://learn.microsoft.com/azure/aks/cluster-container-registry-integration)
- [Deploy an application to AKS](https://learn.microsoft.com/azure/aks/tutorial-kubernetes-deploy-application)
- [Use Microsoft Entra Workload ID with AKS](https://learn.microsoft.com/azure/aks/workload-identity-deploy-cluster)
- [Use a public load balancer with AKS](https://learn.microsoft.com/azure/aks/load-balancer-standard)
