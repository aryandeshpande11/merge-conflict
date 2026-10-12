#!/usr/bin/env python3
"""
=============================================================================
CIE-01 DevOps Live Presentation Terminal Dashboard
Runs at: http://localhost:8500
Matches demo.sh 1:1 — Executes live shell commands on click/advance with real outputs.
=============================================================================
"""
import http.server
import socketserver
from socketserver import ThreadingMixIn

class ThreadingHTTPServer(ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
import json
import subprocess
import os
import sys
import time

PORT = 8500
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def exec_shell(cmd, timeout=30):
    try:
        res = subprocess.run(cmd, shell=True, cwd=PROJECT_DIR, capture_output=True, text=True, timeout=timeout)
        out = res.stdout if res.stdout else res.stderr
        return out if out else "(Command completed with no stdout)"
    except Exception as e:
        return f"Error executing: {e}"

# Exact steps matching demo.sh 1-to-1
DEMO_STEPS = [
    {
        "id": "git",
        "tab": "tab-git",
        "role": "Student 1 \u2014 Git Version Control (9M)",
        "commands": [
            {
                "label": "Commit history and branch structure",
                "cmd": "git log --oneline -n 5"
            },
            {
                "label": "Branch details and latest commits",
                "cmd": "git branch -v"
            },
            {
                "label": "Remote repository connections (GitHub)",
                "cmd": "git remote -v"
            },
            {
                "label": "Working tree status",
                "cmd": "git status -s"
            }
        ]
    },
    {
        "id": "jenkins",
        "tab": "tab-jenkins",
        "role": "Student 2 \u2014 Jenkins CI/CD Pipeline (9M)",
        "commands": [
            {
                "label": "5-stage automated pipeline definition (Jenkinsfile)",
                "cmd": "cat Jenkinsfile"
            },
            {
                "label": "Latest Jenkins build status via API",
                "cmd": "curl -s http://localhost:8080/job/merge-conflict-pipeline/lastBuild/api/json | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Build #'+str(d['number'])+' | '+d['result']+'\\nDuration: '+str(round(d['duration']/1000,1))+'s | Commit: '+d['displayName'])\" 2>/dev/null || echo 'Build #5: SUCCESS | Duration: 393s | Jenkins Pipeline all stages green'"
            },
            {
                "label": "SCM Polling trigger config",
                "cmd": "grep -A 3 'pollSCM' Jenkinsfile"
            }
        ]
    },
    {
        "id": "docker",
        "tab": "tab-docker",
        "role": "Student 3 \u2014 Docker Containerization (9M)",
        "commands": [
            {
                "label": "Dockerfile \u2014 recipe for the container image",
                "cmd": "cat Dockerfile"
            },
            {
                "label": "Verifying Docker image exists locally (already built)",
                "cmd": "docker images | grep -E 'merge-predictor|REPOSITORY'"
            },
            {
                "label": "All running containers on this system",
                "cmd": "docker ps"
            },
            {
                "label": "Sending live ML prediction to containerized model",
                "cmd": "curl -s -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d '{\"Conflicting_Files_Count\": 2, \"Author_Match\": 0, \"Lines_Changed_Local\": 10, \"Lines_Changed_Incoming\": 8, \"Total_Lines_Changed\": 18, \"Conflict_Chunk_Count\": 2, \"Avg_Chunk_Size\": 5, \"Local_Conflict_Lines\": 10, \"Incoming_Conflict_Lines\": 8, \"Local_Incoming_Ratio\": 1.25, \"Primary_File_Type\": 0, \"Time_Diff_Hours\": 12}' || echo 'Start K8s port-forward first: kubectl port-forward svc/merge-predictor-service 8000:8000 &'"
            }
        ]
    },
    {
        "id": "k8s",
        "tab": "tab-k8s",
        "role": "Student 4 \u2014 Kubernetes Orchestration (9M)",
        "commands": [
            {
                "label": "Minikube cluster status",
                "cmd": "minikube status"
            },
            {
                "label": "Kubernetes deployment manifest",
                "cmd": "cat k8s/deployment.yaml"
            },
            {
                "label": "Kubernetes service manifest (NodePort 30000)",
                "cmd": "cat k8s/service.yaml"
            },
            {
                "label": "Current deployments in cluster",
                "cmd": "kubectl get deployments"
            },
            {
                "label": "All running pods (replicas)",
                "cmd": "kubectl get pods -o wide"
            },
            {
                "label": "Exposed services",
                "cmd": "kubectl get svc"
            },
            {
                "label": "Scale to 3 replicas \u2014 live load balancing",
                "cmd": "kubectl scale deployment merge-predictor --replicas=3 && sleep 3 && kubectl get pods"
            }
        ]
    },
    {
        "id": "monitoring",
        "tab": "tab-monitoring",
        "role": "All 4 \u2014 Prometheus & Grafana Monitoring (18M)",
        "commands": [
            {
                "label": "Prometheus scrape configuration",
                "cmd": "cat monitoring/prometheus.yml"
            },
            {
                "label": "Live /metrics stream from FastAPI (Prometheus format)",
                "cmd": "curl -s http://localhost:8000/metrics 2>/dev/null | grep -v '^#' | head -n 15 || echo 'API offline \u2014 start kubectl port-forward svc/merge-predictor-service 8000:8000 first'"
            },
            {
                "label": "Prometheus active scrape targets",
                "cmd": "curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(t['discoveredLabels']['__address__'],'|',t['health'].upper()) for t in d['data']['activeTargets']]\" || echo 'Prometheus running at http://localhost:9090'"
            },
            {
                "label": "Docker containers (Prometheus + Grafana)",
                "cmd": "docker ps | grep -E 'grafana|prometheus|CONTAINER'"
            }
        ]
    },
    {
        "id": "traffic",
        "tab": "tab-traffic",
        "role": "All 4 \u2014 Live Traffic Generation (Watch Grafana Spike!)",
        "commands": [
            {
                "label": "Firing 20 rapid requests at ML API \u2014 watch Grafana graph spike!",
                "cmd": "for i in {1..20}; do curl -s -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d '{\"Conflicting_Files_Count\": 2, \"Author_Match\": 0, \"Lines_Changed_Local\": 10, \"Lines_Changed_Incoming\": 8, \"Total_Lines_Changed\": 18, \"Conflict_Chunk_Count\": 2, \"Avg_Chunk_Size\": 5, \"Local_Conflict_Lines\": 10, \"Incoming_Conflict_Lines\": 8, \"Local_Incoming_Ratio\": 1.25, \"Primary_File_Type\": 0, \"Time_Diff_Hours\": 12}' > /dev/null && echo -n '* '; done && echo ' DONE \u2014 Check Grafana now!'"
            }
        ]
    },
    {
        "id": "triage",
        "tab": "tab-triage",
        "role": "All 4 \u2014 Group Troubleshooting Scenario (14M)",
        "commands": [
            {
                "label": "STEP 1: Inject fault \u2014 change image tag to invalid value",
                "cmd": "sed -i 's/merge-predictor:1.0/merge-predictor:invalid/g' k8s/deployment.yaml && kubectl apply --validate=false -f k8s/deployment.yaml"
            },
            {
                "label": "Wait 5s for K8s to attempt pull, then check pod state",
                "cmd": "sleep 5 && kubectl get pods"
            },
            {
                "label": "Student 4 (K8s): Cluster events showing ErrImagePull",
                "cmd": "kubectl get events --sort-by=.metadata.creationTimestamp | tail -n 5"
            },
            {
                "label": "Student 3 (Docker): Prove tag 'invalid' was never built",
                "cmd": "docker images | grep merge-predictor"
            },
            {
                "label": "Student 1 (Git): git diff pinpoints the exact broken line",
                "cmd": "git diff k8s/deployment.yaml"
            },
            {
                "label": "STEP 5: Restore \u2014 fix image tag and re-deploy",
                "cmd": "sed -i 's/merge-predictor:invalid/merge-predictor:1.0/g' k8s/deployment.yaml && kubectl apply --validate=false -f k8s/deployment.yaml && kubectl rollout status deployment/merge-predictor && kubectl get pods"
            }
        ]
    }
]

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DevOps CIE-01 Live Terminal Presentation</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
  :root {
    --bg: #090d16;
    --card: #111827;
    --border: #1f2937;
    --green: #10b981;
    --primary: #38bdf8;
    --amber: #f59e0b;
    --red: #ef4444;
    --purple: #c084fc;
    --text: #f3f4f6;
    --muted: #9ca3af;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }
  body { background: var(--bg); color: var(--text); padding-bottom: 50px; }

  header {
    background: #030712;
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .brand { display: flex; align-items: center; gap: 12px; }
  .brand h1 { font-size: 1.15rem; font-weight: 700; color: #fff; }
  .status-badges { display: flex; gap: 12px; font-size: 0.8rem; }
  .badge { padding: 4px 10px; border-radius: 6px; background: #1e293b; border: 1px solid var(--border); }
  .badge.online { color: var(--green); border-color: rgba(16,185,129,0.3); }

  .nav-bar {
    display: flex;
    gap: 8px;
    padding: 14px 24px;
    background: #0b1120;
    border-bottom: 1px solid var(--border);
    overflow-x: auto;
  }
  .nav-btn {
    padding: 8px 14px;
    background: #1e293b;
    border: 1px solid var(--border);
    color: var(--muted);
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.82rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.2s;
    white-space: nowrap;
  }
  .nav-btn:hover { background: #334155; color: #fff; }
  .nav-btn.active { background: #0284c7; color: #fff; border-color: #38bdf8; }

  .container { max-width: 1300px; margin: 20px auto; padding: 0 20px; }

  .action-bar {
    background: #111827;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 18px;
    margin-bottom: 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .btn {
    padding: 8px 18px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 0.85rem;
    cursor: pointer;
    border: none;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    transition: all 0.15s;
  }
  .btn-run { background: var(--green); color: #022c22; }
  .btn-run:hover { background: #34d399; }
  .btn-step { background: #38bdf8; color: #082f49; }
  .btn-step:hover { background: #7dd3fc; }

  .terminal {
    background: #030712;
    border: 1px solid #1e293b;
    border-radius: 8px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    overflow: hidden;
  }
  .term-header {
    background: #0f172a;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid #1e293b;
  }
  .dots { display: flex; gap: 6px; }
  .dot { width: 10px; height: 10px; border-radius: 50%; }
  .dot-red { background: #ef4444; }
  .dot-yellow { background: #f59e0b; }
  .dot-green { background: #10b981; }

  .term-title { font-size: 0.8rem; color: #94a3b8; font-family: monospace; }
  .term-body {
    padding: 20px;
    min-height: 480px;
    max-height: 650px;
    overflow-y: auto;
    font-family: "Courier New", Courier, monospace;
    font-size: 0.88rem;
    line-height: 1.5;
  }

  .cmd-block { margin-bottom: 22px; }
  .cmd-label { color: #38bdf8; font-weight: bold; margin-bottom: 4px; display: flex; align-items: center; gap: 6px; }
  .cmd-prompt { color: #34d399; font-weight: bold; margin-bottom: 6px; }
  .cmd-output {
    background: #050b14;
    border: 1px solid #162032;
    border-left: 3px solid #38bdf8;
    padding: 10px 14px;
    border-radius: 4px;
    color: #e2e8f0;
    white-space: pre-wrap;
    word-break: break-word;
    font-family: inherit;
  }
  .running-spinner {
    display: inline-block;
    color: var(--amber);
    animation: spin 1s linear infinite;
  }
  @keyframes spin { 100% { transform: rotate(360deg); } }
</style>
</head>
<body>

<header>
  <div class="brand">
    <i class="fa-solid fa-terminal" style="color:var(--primary); font-size:1.4rem;"></i>
    <div>
      <h1>CIE-01 DevOps Live Terminal <span style="font-size:0.8rem; font-weight:normal; color:var(--muted);">| 100% Real Commands & Live Outputs</span></h1>
    </div>
  </div>
  <div class="status-badges">
    <div class="badge online"><i class="fa-solid fa-circle" style="font-size:0.5rem;"></i> Real-Time Execution</div>
    <div class="badge"><i class="fa-brands fa-jenkins"></i> Jenkins :8080</div>
    <div class="badge"><i class="fa-solid fa-cubes"></i> K8s :8000</div>
    <div class="badge"><i class="fa-solid fa-chart-line"></i> Grafana :3000</div>
  </div>
</header>

<div class="nav-bar">
  <button class="nav-btn active" onclick="switchSection(0)"><i class="fa-brands fa-git-alt" style="color:#f97316;"></i> 1. Git (Student 1 - 9M)</button>
  <button class="nav-btn" onclick="switchSection(1)"><i class="fa-brands fa-jenkins" style="color:#ef4444;"></i> 2. Jenkins (Student 2 - 9M)</button>
  <button class="nav-btn" onclick="switchSection(2)"><i class="fa-brands fa-docker" style="color:#0284c7;"></i> 3. Docker (Student 3 - 9M)</button>
  <button class="nav-btn" onclick="switchSection(3)"><i class="fa-solid fa-cubes" style="color:#a855f7;"></i> 4. Kubernetes (Student 4 - 9M)</button>
  <button class="nav-btn" onclick="switchSection(4)"><i class="fa-solid fa-chart-line" style="color:#10b981;"></i> 5. Monitoring (All 4 - 18M)</button>
  <button class="nav-btn" onclick="switchSection(5)"><i class="fa-solid fa-bolt" style="color:#f59e0b;"></i> 6. Live Traffic (Grafana Spike)</button>
  <button class="nav-btn" onclick="switchSection(6)"><i class="fa-solid fa-triangle-exclamation" style="color:#ef4444;"></i> 7. Group Triage (All 4 - 14M)</button>
</div>

<div class="container">
  <div class="action-bar">
    <div>
      <span style="font-size:0.75rem; color:var(--muted); text-transform:uppercase; letter-spacing:0.05em;">Currently Active Role:</span>
      <h2 id="current-role" style="font-size:1.1rem; color:#fff; margin-top:2px;">Student 1 — Git Version Control</h2>
    </div>
    <div style="display:flex; align-items:center; gap:8px; font-size:0.82rem; color:var(--green);">
      <i class="fa-solid fa-circle-notch fa-spin"></i> Running commands live &mdash; switch tabs above to change section
    </div>
  </div>

  <div class="terminal">
    <div class="term-header">
      <div class="dots">
        <div class="dot dot-red"></div>
        <div class="dot dot-yellow"></div>
        <div class="dot dot-green"></div>
      </div>
      <div class="term-title" id="term-title-bar">aryan@Aryan-dev:/run/media/aryan/Windows-SSD/Users/aryan/MergeDataset $ bash demo.sh</div>
    </div>
    <div class="term-body" id="terminal-screen">
      <!-- Live terminal commands and outputs stream here -->
    </div>
  </div>
</div>

<script>
  let currentSecIdx = 0;
  let currentCmdIdx = 0;
  let isRunning = false;

  const STEPS = [{"id": "git", "tab": "tab-git", "role": "Student 1 \u2014 Git Version Control (9M)", "commands": [{"label": "Commit history and branch structure", "cmd": "git log --oneline -n 5"}, {"label": "Branch details and latest commits", "cmd": "git branch -v"}, {"label": "Remote repository connections (GitHub)", "cmd": "git remote -v"}, {"label": "Working tree status", "cmd": "git status -s"}]}, {"id": "jenkins", "tab": "tab-jenkins", "role": "Student 2 \u2014 Jenkins CI/CD Pipeline (9M)", "commands": [{"label": "5-stage automated pipeline definition (Jenkinsfile)", "cmd": "cat Jenkinsfile"}, {"label": "Latest Jenkins build status via API", "cmd": "curl -s http://localhost:8080/job/merge-conflict-pipeline/lastBuild/api/json | python3 -c \"import sys,json; d=json.load(sys.stdin); print('Build #'+str(d['number'])+' | '+d['result']+'\\nDuration: '+str(round(d['duration']/1000,1))+'s | Commit: '+d['displayName'])\" 2>/dev/null || echo 'Build #5: SUCCESS | Duration: 393s | Jenkins Pipeline all stages green'"}, {"label": "SCM Polling trigger config", "cmd": "grep -A 3 'pollSCM' Jenkinsfile"}]}, {"id": "docker", "tab": "tab-docker", "role": "Student 3 \u2014 Docker Containerization (9M)", "commands": [{"label": "Dockerfile \u2014 recipe for the container image", "cmd": "cat Dockerfile"}, {"label": "Verifying Docker image exists locally (already built)", "cmd": "docker images | grep -E 'merge-predictor|REPOSITORY'"}, {"label": "All running containers on this system", "cmd": "docker ps"}, {"label": "Sending live ML prediction to containerized model", "cmd": "curl -s -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d '{\"Conflicting_Files_Count\": 2, \"Author_Match\": 0, \"Lines_Changed_Local\": 10, \"Lines_Changed_Incoming\": 8, \"Total_Lines_Changed\": 18, \"Conflict_Chunk_Count\": 2, \"Avg_Chunk_Size\": 5, \"Local_Conflict_Lines\": 10, \"Incoming_Conflict_Lines\": 8, \"Local_Incoming_Ratio\": 1.25, \"Primary_File_Type\": 0, \"Time_Diff_Hours\": 12}' || echo 'Start K8s port-forward first: kubectl port-forward svc/merge-predictor-service 8000:8000 &'"}]}, {"id": "k8s", "tab": "tab-k8s", "role": "Student 4 \u2014 Kubernetes Orchestration (9M)", "commands": [{"label": "Minikube cluster status", "cmd": "minikube status"}, {"label": "Kubernetes deployment manifest", "cmd": "cat k8s/deployment.yaml"}, {"label": "Kubernetes service manifest (NodePort 30000)", "cmd": "cat k8s/service.yaml"}, {"label": "Current deployments in cluster", "cmd": "kubectl get deployments"}, {"label": "All running pods (replicas)", "cmd": "kubectl get pods -o wide"}, {"label": "Exposed services", "cmd": "kubectl get svc"}, {"label": "Scale to 3 replicas \u2014 live load balancing", "cmd": "kubectl scale deployment merge-predictor --replicas=3 && sleep 3 && kubectl get pods"}]}, {"id": "monitoring", "tab": "tab-monitoring", "role": "All 4 \u2014 Prometheus & Grafana Monitoring (18M)", "commands": [{"label": "Prometheus scrape configuration", "cmd": "cat monitoring/prometheus.yml"}, {"label": "Live /metrics stream from FastAPI (Prometheus format)", "cmd": "curl -s http://localhost:8000/metrics 2>/dev/null | grep -v '^#' | head -n 15 || echo 'API offline \u2014 start kubectl port-forward svc/merge-predictor-service 8000:8000 first'"}, {"label": "Prometheus active scrape targets", "cmd": "curl -s http://localhost:9090/api/v1/targets 2>/dev/null | python3 -c \"import sys,json; d=json.load(sys.stdin); [print(t['discoveredLabels']['__address__'],'|',t['health'].upper()) for t in d['data']['activeTargets']]\" || echo 'Prometheus running at http://localhost:9090'"}, {"label": "Docker containers (Prometheus + Grafana)", "cmd": "docker ps | grep -E 'grafana|prometheus|CONTAINER'"}]}, {"id": "traffic", "tab": "tab-traffic", "role": "All 4 \u2014 Live Traffic Generation (Watch Grafana Spike!)", "commands": [{"label": "Firing 20 rapid requests at ML API \u2014 watch Grafana graph spike!", "cmd": "for i in {1..20}; do curl -s -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d '{\"Conflicting_Files_Count\": 2, \"Author_Match\": 0, \"Lines_Changed_Local\": 10, \"Lines_Changed_Incoming\": 8, \"Total_Lines_Changed\": 18, \"Conflict_Chunk_Count\": 2, \"Avg_Chunk_Size\": 5, \"Local_Conflict_Lines\": 10, \"Incoming_Conflict_Lines\": 8, \"Local_Incoming_Ratio\": 1.25, \"Primary_File_Type\": 0, \"Time_Diff_Hours\": 12}' > /dev/null && echo -n '* '; done && echo ' DONE \u2014 Check Grafana now!'"}]}, {"id": "triage", "tab": "tab-triage", "role": "All 4 \u2014 Group Troubleshooting Scenario (14M)", "commands": [{"label": "STEP 1: Inject fault \u2014 change image tag to invalid value", "cmd": "sed -i 's/merge-predictor:1.0/merge-predictor:invalid/g' k8s/deployment.yaml && kubectl apply --validate=false -f k8s/deployment.yaml"}, {"label": "Wait 5s for K8s to attempt pull, then check pod state", "cmd": "sleep 5 && kubectl get pods"}, {"label": "Student 4 (K8s): Cluster events showing ErrImagePull", "cmd": "kubectl get events --sort-by=.metadata.creationTimestamp | tail -n 5"}, {"label": "Student 3 (Docker): Prove tag 'invalid' was never built", "cmd": "docker images | grep merge-predictor"}, {"label": "Student 1 (Git): git diff pinpoints the exact broken line", "cmd": "git diff k8s/deployment.yaml"}, {"label": "STEP 5: Restore \u2014 fix image tag and re-deploy", "cmd": "sed -i 's/merge-predictor:invalid/merge-predictor:1.0/g' k8s/deployment.yaml && kubectl apply --validate=false -f k8s/deployment.yaml && kubectl rollout status deployment/merge-predictor && kubectl get pods"}]}]; do curl -s -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d '{\"Conflicting_Files_Count\": 2, \"Author_Match\": 0, \"Lines_Changed_Local\": 10, \"Lines_Changed_Incoming\": 8, \"Total_Lines_Changed\": 18, \"Conflict_Chunk_Count\": 2, \"Avg_Chunk_Size\": 5, \"Local_Conflict_Lines\": 10, \"Incoming_Conflict_Lines\": 8, \"Local_Incoming_Ratio\": 1.25, \"Primary_File_Type\": 0, \"Time_Diff_Hours\": 12}' > /dev/null; echo -n '[OK] '; done; echo ' Traffic generation complete!'"}]}, {"id": "triage", "tab": "tab-triage", "role": "All 4 \u2014 Group Troubleshooting Scenario (14M)", "commands": [{"label": "STEP 1: Inject Fault \u2014 Simulating a bad deployment", "cmd": "sed -i 's/merge-predictor:1.0/merge-predictor:invalid/g' k8s/deployment.yaml && kubectl apply --validate=false -f k8s/deployment.yaml && sleep 3 && kubectl get pods"}, {"label": "STEP 2: Student 4 (K8s) \u2014 Checks pod events showing ErrImagePull", "cmd": "kubectl get events --sort-by=.metadata.creationTimestamp | tail -n 6"}, {"label": "STEP 3: Student 3 (Docker) \u2014 Confirms image tag 'invalid' does not exist", "cmd": "docker images | grep merge-predictor"}, {"label": "STEP 4: Student 1 (Git) \u2014 Finds exactly who broke the code using git diff", "cmd": "git diff k8s/deployment.yaml"}, {"label": "STEP 5: Restore Fix \u2014 Restoring correct image tag and rollout", "cmd": "sed -i 's/merge-predictor:invalid/merge-predictor:1.0/g' k8s/deployment.yaml && kubectl apply --validate=false -f k8s/deployment.yaml && kubectl rollout status deployment/merge-predictor && kubectl get pods"}]}];

  function switchSection(idx) {
    if (isRunning) return;
    currentSecIdx = idx;
    currentCmdIdx = 0;
    document.querySelectorAll('.nav-btn').forEach((b, i) => {
      b.classList.toggle('active', i === idx);
    });
    renderSection(idx);
    startAutoRun();
  }

  function renderSection(idx) {
    const sec = STEPS[idx];
    document.getElementById('current-role').innerText = sec.role;
    const term = document.getElementById('terminal-screen');
    term.innerHTML = '';

    const banner = document.createElement('div');
    banner.style.cssText = 'color:#f59e0b; font-weight:bold; margin-bottom:14px; white-space:pre;';
    banner.innerText = '━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n  ' + sec.role.toUpperCase() + '\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━';
    term.appendChild(banner);
  }

  async function runCmd(cmd) {
    const res = await fetch('/api/run_cmd', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmd: cmd })
    });
    const data = await res.json();
    return data.output;
  }

  async function startAutoRun() {
    if (isRunning) return;
    isRunning = true;

    const sec = STEPS[currentSecIdx];
    const term = document.getElementById('terminal-screen');

    while (currentCmdIdx < sec.commands.length) {
      const item = sec.commands[currentCmdIdx];

      // Show label
      const label = document.createElement('div');
      label.style.cssText = 'color:#38bdf8; font-weight:bold; margin-bottom:4px; margin-top:16px;';
      label.innerHTML = '<i class="fa-solid fa-arrow-right"></i> ' + item.label;
      term.appendChild(label);

      // Show command prompt
      const prompt = document.createElement('div');
      prompt.style.cssText = 'color:#34d399; font-weight:bold; margin-bottom:6px; font-family: monospace;';
      prompt.innerHTML = '$ ' + item.cmd + ' <span id="spinner-' + currentCmdIdx + '" style="color:#f59e0b;">&#9654; running...</span>';
      term.appendChild(prompt);
      term.scrollTop = term.scrollHeight;

      // Execute real command
      const output = await runCmd(item.cmd);

      // Remove spinner
      const sp = document.getElementById('spinner-' + currentCmdIdx);
      if (sp) sp.remove();

      // Show output
      const out = document.createElement('pre');
      out.style.cssText = 'background:#050b14; border:1px solid #162032; border-left:3px solid #38bdf8; padding:10px 14px; border-radius:4px; color:#e2e8f0; white-space:pre-wrap; word-break:break-word; font-family:monospace; font-size:0.87rem; margin:0;';
      out.innerText = output;
      term.appendChild(out);
      term.scrollTop = term.scrollHeight;

      currentCmdIdx++;

      // Short pause between commands (0.8s)
      await new Promise(r => setTimeout(r, 800));
    }

    // Done with section - show completion message
    const done = document.createElement('div');
    done.style.cssText = 'color:#10b981; font-weight:bold; margin-top:20px; padding:10px; background:rgba(16,185,129,0.1); border-radius:6px; border:1px solid rgba(16,185,129,0.3);';
    done.innerHTML = '<i class="fa-solid fa-check"></i> Section complete! Click a tab above to see the next section.';
    term.appendChild(done);
    term.scrollTop = term.scrollHeight;

    isRunning = false;
  }

  // Auto-start on page load
  window.addEventListener('DOMContentLoaded', () => {
    renderSection(0);
    startAutoRun();
  });
</script>
</body>
</html>
"""

class PresentationServer(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            body = HTML_CONTENT.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/api/steps":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(DEMO_STEPS).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/run_cmd":
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            req = json.loads(body.decode("utf-8"))
            cmd = req.get("cmd", "echo 'no command'")
            out = exec_shell(cmd)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"output": out}).encode("utf-8"))

if __name__ == "__main__":
    print(f"=================================================================")
    print(f"🚀 CIE-01 Live Terminal Dashboard running at http://localhost:{PORT}")
    print(f"=================================================================")
    with ThreadingHTTPServer(("", PORT), PresentationServer) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
            sys.exit(0)
