#!/bin/bash
# ============================================================
# COMPLETE SETUP GUIDE
# Green Multi-Cloud Kubernetes Scheduler
# Run this on your machine that has kubectl + Docker installed
# ============================================================

# Install minikube: https://minikube.sigs.k8s.io/docs/start/

echo "======================================================"
echo " STEP 1: Start minikube with multiple nodes"
echo "======================================================"
# Start cluster with 4 worker nodes to simulate multi-cloud
minikube start \
  --nodes=5 \
  --cpus=2 \
  --memory=2048 \
  --driver=docker

# Verify cluster
kubectl get nodes

echo ""
echo "======================================================"
echo " STEP 2: Label nodes with cloud providers"
echo "======================================================"
bash k8s/label-nodes.sh

echo ""
echo "======================================================"
echo " STEP 3: Build the scheduler Docker image"
echo "======================================================"
# Build the image inside minikube's Docker daemon
# so it doesn't need to be pushed to a registry
eval $(minikube docker-env)

docker build \
  -f docker/Dockerfile \
  -t green-scheduler:latest \
  .

echo "Image built: green-scheduler:latest"

echo ""
echo "======================================================"
echo " STEP 4: Deploy RBAC + Scheduler"
echo "======================================================"
kubectl apply -f k8s/rbac.yaml
kubectl apply -f k8s/scheduler-deployment.yaml

echo "Waiting for green-scheduler pod to be ready..."
kubectl -n kube-system wait \
  --for=condition=ready pod \
  --selector=app=green-scheduler \
  --timeout=60s

echo ""
echo "======================================================"
echo " STEP 5: Watch scheduler logs"
echo "======================================================"
echo "Run in a separate terminal:"
echo "  kubectl -n kube-system logs -f -l app=green-scheduler"

echo ""
echo "======================================================"
echo " STEP 6: Submit workloads"
echo "======================================================"
kubectl apply -f k8s/sample-workload.yaml

kubectl get pods -w &
WATCH_PID=$!

sleep 30
kill $WATCH_PID 2>/dev/null

echo ""
echo "======================================================"
echo " STEP 7: Verify scheduling decisions"
echo "======================================================"
echo "Pods and their assigned nodes:"
kubectl get pods -o wide \
  --selector='app in (gocj-workload,gocj-batch)'

echo ""
echo "Scheduling events (shows energy estimates):"
kubectl get events \
  --field-selector reason=Scheduled \
  --sort-by='.lastTimestamp'

echo ""
echo "======================================================"
echo " CLEANUP"
echo "======================================================"
echo "To delete workloads:   kubectl delete -f k8s/sample-workload.yaml"
echo "To delete scheduler:   kubectl delete -f k8s/scheduler-deployment.yaml"
echo "To delete RBAC:        kubectl delete -f k8s/rbac.yaml"
echo "To stop minikube:      minikube stop"
echo "To delete minikube:    minikube delete"
