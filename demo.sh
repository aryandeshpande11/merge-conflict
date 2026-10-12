#!/bin/bash
# ================================================================
#  CIE-01 DevOps Showcase — Full Live Demo Script
#  Usage: bash demo.sh
#  Press ENTER to advance to the next section at your own pace.
# ================================================================

# Colours
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

# Helpers
section() {
  echo -e "\n${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
  echo -e "${CYAN}${BOLD}  $1${RESET}"
  echo -e "${YELLOW}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}\n"
}
run()   { echo -e "${GREEN}\$ $1${RESET}"; eval "$1"; echo ""; }
pause() { echo -e "\n${BOLD}▶  Press ENTER for next section...${RESET}"; read -r; }
label() { echo -e "${CYAN}${BOLD}  → $1${RESET}\n"; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/k8s" ]; then
  PROJECT="$SCRIPT_DIR"
else
  PROJECT="/run/media/aryan/Windows-SSD/Users/aryan/MergeDataset"
fi
cd "$PROJECT" || exit 1

# ================================================================
section "STUDENT 1 — GIT VERSION CONTROL  (9 Marks)"
# ================================================================
label "Showing commit history and branch structure"
run "git log --oneline -n 5"
sleep 1
run "git branch -v"
sleep 1
label "Showing remote repository connections"
run "git remote -v"
sleep 1
label "Checking working tree status"
run "git status -s"
pause

# ================================================================
section "STUDENT 2 — JENKINS CI/CD PIPELINE  (9 Marks)"
# ================================================================
label "Showing the 5-stage automated pipeline definition"
run "cat Jenkinsfile"
pause

# ================================================================
section "STUDENT 3 — DOCKER CONTAINERIZATION  (9 Marks)"
# ================================================================
label "Showing the Dockerfile — recipe for the container"
run "cat Dockerfile"
sleep 1
label "Building the Docker image from Dockerfile"
run "docker build -t merge-predictor:1.0 ."
sleep 1
label "Verifying image was created locally"
run "docker images | grep merge-predictor"
sleep 1
label "Running the container on port 8000"
run "docker run -d --name merge-predictor -p 8000:8000 merge-predictor:1.0"
sleep 2
label "Confirming container is live"
run "docker ps"
sleep 1
label "Sending a live ML prediction request to the containerized model"
echo -e "${GREEN}\$ curl -X POST http://localhost:8000/predict  [12-feature payload]${RESET}"
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Conflicting_Files_Count": 2,
    "Author_Match": 0,
    "Lines_Changed_Local": 10,
    "Lines_Changed_Incoming": 8,
    "Total_Lines_Changed": 18,
    "Conflict_Chunk_Count": 2,
    "Avg_Chunk_Size": 5,
    "Local_Conflict_Lines": 10,
    "Incoming_Conflict_Lines": 8,
    "Local_Incoming_Ratio": 1.25,
    "Primary_File_Type": 0,
    "Time_Diff_Hours": 12
  }'
echo ""
sleep 1
label "Stopping standalone container — Kubernetes will take over"
run "docker stop merge-predictor && docker rm merge-predictor"
pause

# ================================================================
section "STUDENT 4 — KUBERNETES ORCHESTRATION  (9 Marks)"
# ================================================================
label "Starting local Minikube cluster"
run "minikube start"
sleep 2
label "Loading Docker image into Minikube's registry"
run "minikube image load merge-predictor:1.0"
sleep 1
label "Showing Kubernetes deployment manifest"
run "cat k8s/deployment.yaml"
sleep 1
label "Showing Kubernetes service manifest (NodePort 30000)"
run "cat k8s/service.yaml"
sleep 1
label "Applying deployment and service to the cluster"
run "kubectl apply -f k8s/deployment.yaml"
run "kubectl apply -f k8s/service.yaml"
sleep 2
label "Checking deployment status"
run "kubectl get deployments"
sleep 1
run "kubectl get pods"
sleep 1
run "kubectl get svc"
sleep 1
label "Scaling to 3 replicas for load balancing"
run "kubectl scale deployment merge-predictor --replicas=3"
sleep 4
run "kubectl get pods"
sleep 1
label "Port-forwarding Kubernetes service to localhost"
echo -e "${GREEN}\$ kubectl port-forward svc/merge-predictor-service 8000:8000 &${RESET}"
kubectl port-forward svc/merge-predictor-service 8000:8000 &
sleep 3
echo ""
label "Testing ML prediction via Kubernetes cluster service"
echo -e "${GREEN}\$ curl -X POST http://localhost:8000/predict  [via Kubernetes]${RESET}"
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Conflicting_Files_Count": 2,
    "Author_Match": 0,
    "Lines_Changed_Local": 10,
    "Lines_Changed_Incoming": 8,
    "Total_Lines_Changed": 18,
    "Conflict_Chunk_Count": 2,
    "Avg_Chunk_Size": 5,
    "Local_Conflict_Lines": 10,
    "Incoming_Conflict_Lines": 8,
    "Local_Incoming_Ratio": 1.25,
    "Primary_File_Type": 0,
    "Time_Diff_Hours": 12
  }'
echo ""
pause

# ================================================================
section "ALL 4 — PROMETHEUS MONITORING  (9 Marks)"
# ================================================================
label "Starting Prometheus container with project scrape config"
run "docker rm -f prometheus 2>/dev/null; true"
run "docker run -d --name prometheus -p 9090:9090 --add-host=host.docker.internal:host-gateway -v \$(pwd)/monitoring/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus"
sleep 3
label "Showing scrape configuration"
run "cat monitoring/prometheus.yml"
sleep 1
label "Showing live /metrics output from FastAPI"
echo -e "${GREEN}\$ curl -s http://localhost:8000/metrics | grep -v '^#' | head -15${RESET}"
curl -s http://localhost:8000/metrics 2>/dev/null | grep -v "^#" | head -15
echo ""
echo -e "${CYAN}  → Open browser: http://localhost:9090 → Status → Targets → merge-predictor: UP${RESET}"
pause

# ================================================================
section "ALL 4 — GRAFANA DASHBOARD  (9 Marks)"
# ================================================================
label "Starting Grafana container"
run "docker rm -f grafana 2>/dev/null; true"
run "docker run -d --name grafana -p 3000:3000 --add-host=host.docker.internal:host-gateway grafana/grafana"
sleep 2
run "docker ps"
echo -e "${CYAN}  → Open browser: http://localhost:3000  (admin / admin)${RESET}"
echo -e "${CYAN}  → Add Prometheus source: http://host.docker.internal:9090${RESET}"
echo -e "${CYAN}  → Panel 1: up  |  Panel 2: rate(prediction_requests_total[5m])  |  Panel 3: http latency${RESET}"
pause

# ================================================================
# ================================================================

section "ALL 4 — LIVE TRAFFIC GENERATION (Watch Grafana Spike!)"

# ================================================================

label "Sending 30 rapid requests to the ML API to generate live Grafana graphs"

echo -e "${GREEN}\$ for i in {1..30}; do curl -X POST http://localhost:8000/predict ... done${RESET}"

for i in {1..30}; do

  curl -s -X POST http://localhost:8000/predict -H "Content-Type: application/json" -d "{\"Conflicting_Files_Count\": 2, \"Author_Match\": 0, \"Lines_Changed_Local\": 10, \"Lines_Changed_Incoming\": 8, \"Total_Lines_Changed\": 18, \"Conflict_Chunk_Count\": 2, \"Avg_Chunk_Size\": 5, \"Local_Conflict_Lines\": 10, \"Incoming_Conflict_Lines\": 8, \"Local_Incoming_Ratio\": 1.25, \"Primary_File_Type\": 0, \"Time_Diff_Hours\": 12}" > /dev/null

  echo -n "🟢 "

  sleep 0.1

done

echo -e "\n\n${CYAN}  → Check your Grafana dashboard! You should see a massive spike in Prediction Requests.\n${RESET}"

pause


section "ALL 4 — GROUP TROUBLESHOOTING SCENARIO  (14 Marks)"
# ================================================================
echo -e "${RED}${BOLD}  STEP 1: Inject Fault — Simulating a bad deployment${RESET}\n"
run "sed -i 's/merge-predictor:1.0/merge-predictor:invalid/g' k8s/deployment.yaml"
run "kubectl apply -f k8s/deployment.yaml"
sleep 4

label "Notice the pods fail with ErrImagePull"
run "kubectl get pods"
sleep 1

echo -e "${RED}${BOLD}  STEP 2: Diagnose the failure${RESET}\n"
label "Student 4 (Kubernetes): Checks pod events"
FAIL_POD=$(kubectl get pods -l app=merge-predictor --field-selector=status.phase!=Running -o jsonpath="{.items[0].metadata.name}" 2>/dev/null)
if [ -z "$FAIL_POD" ]; then FAIL_POD=$(kubectl get pods -l app=merge-predictor -o jsonpath="{.items[0].metadata.name}" 2>/dev/null); fi
run "kubectl describe pod $FAIL_POD | grep -A 3 Events"
sleep 1

label "Student 3 (Docker): Confirms image tag 'invalid' does not exist locally"
run "docker images | grep merge-predictor"
sleep 1

label "Student 1 (Git): Finds exactly who broke the code and where"
run "git diff k8s/deployment.yaml"
pause

# ================================================================
section "ALL 4 — RESTORE & FULL RECOVERY"
# ================================================================
echo -e "${GREEN}${BOLD}  STEP 3: Applying Fix — Restoring correct image tag${RESET}\n"
run "sed -i 's/merge-predictor:invalid/merge-predictor:1.0/g' k8s/deployment.yaml"
run "kubectl apply -f k8s/deployment.yaml"
sleep 1

label "Watching rollout complete successfully"
run "kubectl rollout status deployment/merge-predictor"
sleep 1

run "kubectl get pods"
echo -e "\n${GREEN}${BOLD}  ✅ All pods Running — System fully recovered!${RESET}\n"
pause

# ================================================================
section "LAUNCH PRESENTATION DASHBOARD  (http://localhost:8500)"
# ================================================================
label "Starting the live CIE-01 showcase dashboard"
fuser -k 8500/tcp 2>/dev/null; sleep 1
python3 dashboard.py
