# Pre-Demo Technical Setup Guide

Before you can perform the demo script, you actually need to install and configure the DevOps tools on your laptop. This guide tells you exactly **how** to set up the environment.

---

## 1. CI/CD Setup (Highly Recommended: Use GitHub Actions)
Your rubric explicitly says **"Jenkins CI/CD or GitHub Actions"**. 
* **Do not use Jenkins** if you haven't set it up yet. Jenkins requires downloading Java, configuring a local server, installing plugins, and exposing your localhost to the internet. It takes hours.
* **Use GitHub Actions instead.** It requires **zero installation**. Because your code is already on GitHub, you just create a `.github/workflows/main.yml` file, and GitHub automatically provides a free server to build your Docker image whenever you push code.

---

## 2. Docker & Kubernetes Setup (Localhost)

Since you are running this demo on your laptop, you need a local Kubernetes cluster.
1. **Install Docker Desktop:** Download and install it from [docker.com](https://www.docker.com/). Leave it running in the background.
2. **Install Minikube:** This gives you a free, local Kubernetes cluster. Download it from [minikube.sigs.k8s.io](https://minikube.sigs.k8s.io/docs/start/).
3. **Start Kubernetes:** Open CMD and run:
   ```bash
   minikube start
   ```
4. **Link Docker to Minikube:** By default, Kubernetes can't see images you build locally. Run this in your CMD so Minikube shares your Docker images:
   ```bash
   @FOR /f "tokens=*" %i IN ('minikube -p minikube docker-env') DO @%i
   ```

---

## 3. Prometheus & Grafana Setup

The absolute easiest way to install Prometheus and Grafana on your local Minikube cluster is using **Helm** (the package manager for Kubernetes).

1. **Install Helm:** Download from [helm.sh](https://helm.sh/docs/intro/install/) (or via chocolatey: `choco install kubernetes-helm`).
2. **Add the Prometheus repository:**
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo update
   ```
3. **Install the entire monitoring stack automatically:**
   ```bash
   helm install monitoring prometheus-community/kube-prometheus-stack
   ```
   *(This automatically installs Prometheus and Grafana inside your Kubernetes cluster).*
4. **Access Grafana:**
   ```bash
   kubectl port-forward svc/monitoring-grafana 3000:80
   ```
   Now you can open `http://localhost:3000` in your browser. (Default login is usually `admin` / `prom-operator`).

---

## 4. The Application Files You Need to Create

To actually deploy your ML model, you need to create these files in your `MergeDataset` folder. (You can split this work among the 4 team members):

### File 1: `requirements.txt`
```text
fastapi
uvicorn
xgboost==2.0.3
pandas
scikit-learn
```

### File 2: `api/app.py`
```python
from fastapi import FastAPI
from pydantic import BaseModel
import pickle
import pandas as pd

app = FastAPI()

# Load the V3 model
with open('xgboost_merge_model_v3.pkl', 'rb') as f:
    data = pickle.load(f)
    model = data['model']
    encoder = data['encoder']
    features = data['features']

class ConflictData(BaseModel):
    Conflicting_Files_Count: int
    Author_Match: int
    Lines_Changed_Local: int
    Lines_Changed_Incoming: int
    Total_Lines_Changed: int
    Conflict_Chunk_Count: int
    Avg_Chunk_Size: float
    Local_Conflict_Lines: int
    Incoming_Conflict_Lines: int
    Local_Incoming_Ratio: float
    Primary_File_Type: int
    Time_Diff_Hours: float

@app.post("/predict")
def predict_resolution(data: ConflictData):
    # Convert input to DataFrame
    input_df = pd.DataFrame([data.dict()])
    
    # Predict
    pred_idx = model.predict(input_df)[0]
    prediction = encoder.inverse_transform([pred_idx])[0]
    
    return {"prediction": prediction}
```

### File 3: `Dockerfile`
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY xgboost_merge_model_v3.pkl .
COPY api/ api/
EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### File 4: `k8s/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: merge-predictor
spec:
  replicas: 1
  selector:
    matchLabels:
      app: merge-predictor
  template:
    metadata:
      labels:
        app: merge-predictor
    spec:
      containers:
      - name: merge-predictor
        image: merge-predictor:latest
        imagePullPolicy: Never # Forces k8s to use your local docker image
        ports:
        - containerPort: 8000
```

### File 5: `k8s/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: merge-predictor-service
spec:
  type: NodePort
  selector:
    app: merge-predictor
  ports:
    - port: 8000
      targetPort: 8000
      nodePort: 30007
```

---

## 5. How to Run the Demo Locally

1. **Build the Docker Image:**
   ```bash
   docker build -t merge-predictor:latest .
   ```
2. **Deploy to Kubernetes:**
   ```bash
   kubectl apply -f k8s/deployment.yaml
   kubectl apply -f k8s/service.yaml
   ```
3. **Test the API:**
   Because Minikube runs inside a virtual machine, you need to expose the service to your localhost:
   ```bash
   minikube service merge-predictor-service
   ```
   This will open the API in your browser, and you can now run the `curl` command from the demo script!
