# DevOps for Scalable System - Group Demo Plan & Script

**Project Context:** We have a working ML project (Merge Conflict Predictor trained with XGBoost on 12 features). We are demonstrating our DevOps skills by building the deployment, CI/CD, and monitoring pipeline *around* this existing ML project.

---

## 👥 Person 1 (P1): Git & Setup

**Goal:** Create the deployment branch, generate all the deployment files using AI tools, and commit/push to show Git workflow.

### Instructions:
1. Open your terminal in the `MergeDataset` folder.
2. Show current Git status: `git status`, `git log --oneline`
3. Create the deployment branch: `git checkout -b deployment`
4. **Use your AI Tool (Cursor/Copilot/ChatGPT) to generate the files.**

> **🤖 Prompt for your AI Tool:**
> *"I have an ML project with a saved XGBoost model `xgboost_merge_model_v3.pkl` in the root folder. Please generate the following deployment files for me:
> 1. `api/app.py`: A FastAPI application that loads the .pkl model and exposes a POST `/predict` endpoint taking 12 integer/float features (Conflicting_Files_Count, Author_Match, etc.) and returning the string prediction ('keep_local', 'keep_incoming', or 'combine_both').
> 2. `requirements.txt`: Include fastapi, uvicorn, xgboost, pandas, scikit-learn.
> 3. `Dockerfile`: Use `python:3.11-slim`, copy the model and api folder, install requirements, and run uvicorn on port 8000.
> 4. `k8s/deployment.yaml` and `k8s/service.yaml`: Kubernetes manifests to deploy the docker image `yourusername/merge-predictor:latest` on port 8000.
> 5. `Jenkinsfile`: A declarative pipeline with stages: Checkout, Build Image, Push Image, Deploy to Kubernetes.
> 6. `monitoring/prometheus.yml`: A basic scrape config targeting `localhost:8000`."*

5. Once the files are created, commit and push:
   ```bash
   git add api/ Dockerfile k8s/ monitoring/ requirements.txt Jenkinsfile
   git commit -m "Add ML model deployment configuration"
   git checkout main
   git merge deployment
   ```
6. **Viva Script:** *"Our ML project is already version-controlled. For this demo, we kept the ML code unchanged and used Git branching to safely introduce our deployment configuration (Dockerfile, Kubernetes, Jenkinsfile). Now that it's merged, P2 will show how Jenkins automates the build."*

---

## 👥 Person 2 (P2): Jenkins CI/CD

**Goal:** Explain how Jenkins automates the manual deployment steps.

### Instructions:
1. Open your Jenkins Dashboard (Localhost or Cloud) where the pipeline is configured.
2. Show the `Jenkinsfile` code to the professor.
3. Manually trigger a build (or show the triggered build from P1's push).
4. Walk through the UI showing the green checkboxes for: **Checkout -> Build Docker Image -> Push Image -> Deploy to Kubernetes.**
5. **Viva Script:** *"Instead of manually copying our ML model to a server, this Jenkins pipeline automates the entire process. When P1 merged the code, Jenkins automatically checked it out, packaged the FastAPI app and XGBoost model into a Docker image, pushed it to our registry, and updated Kubernetes."*

---

## 👥 Person 3 (P3): Docker & ML Verification

**Goal:** Explain the Dockerfile and prove the ML model is actually running inside the container by sending a real prediction request.

### Instructions:
1. Open the `Dockerfile` and explain the layers.
2. Run `docker images` to show the built image (`merge-predictor:latest`).
3. Run `docker ps` to show the container is running.
4. **The crucial ML Test:** Send a `curl` request to the API with the 12 features.

> **💻 Command to run:**
> ```bash
> curl -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"Conflicting_Files_Count\": 2, \"Author_Match\": 0, \"Lines_Changed_Local\": 10, \"Lines_Changed_Incoming\": 8, \"Total_Lines_Changed\": 18, \"Conflict_Chunk_Count\": 2, \"Avg_Chunk_Size\": 5, \"Local_Conflict_Lines\": 10, \"Incoming_Conflict_Lines\": 8, \"Local_Incoming_Ratio\": 1.25, \"Primary_File_Type\": 0, \"Time_Diff_Hours\": 12}"
> ```

5. **Viva Script:** *"Our Dockerfile packages the XGBoost model along with its Python dependencies. As you can see from this curl request, we are passing in the 12 engineered features from our ML dataset, and the Docker container successfully returns the prediction 'keep_local'. This proves our actual ML engine is running, not a dummy app."*

---

## 👥 Person 4 (P4): Kubernetes, Monitoring & Troubleshooting

**Goal:** Demonstrate Kubernetes scaling, Prometheus/Grafana monitoring, and execute the troubleshooting scenario to score full integration marks.

### Instructions:
1. Show Kubernetes resources:
   ```bash
   kubectl get deployments
   kubectl get pods
   kubectl get svc
   ```
2. Demonstrate scaling the ML service:
   ```bash
   kubectl scale deployment merge-predictor --replicas=3
   kubectl get pods
   ```
3. Open Grafana in the browser and show the 3 panels (API health, Prediction Requests rate, API latency).
4. **The Troubleshooting Demo (Do this live):**
   - Open `k8s/deployment.yaml` and purposely change the image tag to an invalid one: `image: merge-predictor:invalid`
   - Apply it: `kubectl apply -f k8s/deployment.yaml`
   - Run `kubectl get pods`. Point out the `ImagePullBackOff` error.
   - Trace it back: Run `kubectl describe pod <pod-name>` to show Kubernetes can't find the image.
   - P1 can jump in and say: *"Let's check git history: `git log --oneline` shows someone changed the deployment image tag."*
   - Change `invalid` back to `latest` in the yaml, reapply, and show `kubectl get pods` returning to `Running`.
   - Show Grafana recovering to a healthy state.
5. **Viva Script:** *"Kubernetes provides us with a stable, scalable endpoint for our model. Prometheus scrapes the metrics from our FastAPI pods, and Grafana visualizes them. By deliberately breaking the image tag, we demonstrated how our monitoring alerts us to failures, and how we use Kubernetes events and Git history to diagnose and instantly roll back the fault."*

---

## 🎤 Final Group Conclusion (All 4 together)

*"This demonstrates the complete end-to-end lifecycle: Git version control, Jenkins CI/CD, Docker containerization, Kubernetes orchestration, and Prometheus/Grafana monitoring—applied directly to our custom Machine Learning project."*
