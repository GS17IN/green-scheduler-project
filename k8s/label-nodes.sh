#!/bin/bash
# label-nodes.sh
# ============================================================
# Labels your Kubernetes nodes to simulate multi-cloud providers.
# Run this once after cluster setup to set up cloud-provider labels.
#
# Usage: bash label-nodes.sh
# ============================================================

echo "Labelling nodes with cloud-provider simulation labels..."

# Get all worker nodes
NODES=$(kubectl get nodes --no-headers \
        --selector='!node-role.kubernetes.io/control-plane' \
        -o custom-columns=NAME:.metadata.name)

NODE_ARRAY=($NODES)
COUNT=${#NODE_ARRAY[@]}

echo "Found $COUNT worker nodes"

# Distribute nodes across AWS / Azure / GCP in round-robin
PROVIDERS=("aws" "azure" "gcp")

for i in "${!NODE_ARRAY[@]}"; do
    NODE="${NODE_ARRAY[$i]}"
    PROVIDER="${PROVIDERS[$((i % 3))]}"

    kubectl label node "$NODE" \
        cloud-provider="$PROVIDER" \
        --overwrite

    echo "Node $NODE → $PROVIDER"
done

echo ""
echo "Node layout:"
kubectl get nodes \
    --selector='!node-role.kubernetes.io/control-plane' \
    -o custom-columns=\
'NODE:.metadata.name,PROVIDER:.metadata.labels.cloud-provider,CPU:.status.capacity.cpu,MEM:.status.capacity.memory'
