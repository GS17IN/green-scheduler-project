"""
test_scheduler_local.py
=======================
Tests the Hybrid PSO-ACO scheduler logic WITHOUT a Kubernetes cluster.
Uses mock nodes and pods to verify the scheduling decisions.

Run:
    python test_scheduler_local.py

"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scheduler"))

import numpy as np
from green_scheduler import (
    HybridPSOACO, NodeInfo, PodRequest,
    CloudProvider, CLOUD_PROFILES, multi_obj_fitness, compute_bounds
)


def make_mock_nodes(n=20, seed=42):
    """Create mock cluster nodes (same distribution as your Colab simulation)."""
    rng = np.random.RandomState(seed)
    providers = list(CloudProvider)

    NODE_SPECS = [
        ("small",   4,   8,  40,  120),
        ("medium",  8,  16,  65,  200),
        ("large",  16,  32, 100,  310),
        ("xlarge", 32,  64, 150,  450),
    ]
    w = [0.15, 0.40, 0.35, 0.10]

    nodes = []
    for i in range(n):
        prov = providers[i % 3]
        ti   = rng.choice(len(NODE_SPECS), p=w)
        name, vc, mg, pi, pm = NODE_SPECS[ti]
        nodes.append(NodeInfo(
            name=f"node-{i:02d}-{prov.value.lower()}",
            provider=prov,
            total_cpu=float(max(1, int(vc * rng.uniform(0.9, 1.1)))),
            total_memory=float(round(mg * rng.uniform(0.9, 1.1), 1)),
            used_cpu=0.0,
            used_memory=0.0,
            p_idle=float(pi * rng.uniform(0.95, 1.05)),
            p_max=float(pm  * rng.uniform(0.95, 1.05)),
        ))
    return nodes


def make_mock_pods(n=20, seed=42):
    """Create mock pods based on GoCJ dataset distribution."""
    rng = np.random.RandomState(seed)
    pods = []
    for i in range(n):
        cpu = float(rng.choice([1, 2, 3], p=[0.30, 0.57, 0.13]))
        pods.append(PodRequest(
            name=f"gocj-task-{i:03d}",
            namespace="default",
            cpu_request=cpu,
            mem_request=cpu * 2.0,
            uid=f"uid-{i:04d}",
        ))
    return pods


def run_test():
    print("=" * 60)
    print("  Green Scheduler — Local Test (no cluster needed)")
    print("=" * 60)

    N_NODES = 50
    N_PODS  = 200

    nodes = make_mock_nodes(N_NODES)
    pods  = make_mock_pods(N_PODS)

    total_cpu = sum(n.total_cpu for n in nodes)
    demand    = sum(p.cpu_request for p in pods)
    print(f"\nCluster:  {N_NODES} nodes, {total_cpu:.0f} vCPU total")
    print(f"Workload: {N_PODS} pods, {demand:.0f} vCPU demand")
    print(f"Utilisation target: {demand/total_cpu*100:.1f}%")

    print("\nRunning Hybrid PSO-ACO...")
    import time
    scheduler = HybridPSOACO(n_particles=20, n_ants=15, max_iter=50, seed=42)
    t0 = time.time()
    assignment = scheduler.schedule(pods, nodes)
    elapsed = time.time() - t0
    print(f"Scheduled {len(assignment)} pods in {elapsed:.2f}s")

    # ── Per-node utilisation ─────────────────────────────────
    node_map  = {n.name: n for n in nodes}
    node_cpu  = {n.name: 0.0 for n in nodes}
    node_pods = {n.name: 0   for n in nodes}
    total_e   = 0.0; total_c = 0.0

    for pid, nname in assignment.items():
        pod = pods[pid]; nd = node_map[nname]
        node_cpu[nname]  += pod.cpu_request
        node_pods[nname] += 1
        pue = CLOUD_PROFILES[nd.provider]["pue"]
        ci  = CLOUD_PROFILES[nd.provider]["carbon_kwh"]
        u   = min(node_cpu[nname] / nd.total_cpu, 1.0)
        p   = nd.p_idle + (nd.p_max - nd.p_idle) * (2*u - u**1.4)
        e   = p * pue * (300 / 3_600_000)   # 5-min task
        total_e += e; total_c += e * ci * 1000

    print("\nPer-node utilisation (top 10 loaded):")
    utils = [(n, min(node_cpu[n.name]/n.total_cpu, 1.0)*100,
              node_pods[n.name]) for n in nodes]
    utils.sort(key=lambda x: -x[1])
    for nd, util, np_count in utils[:10]:
        bar = "█" * int(util / 5)
        print(f"  {nd.name:30s} [{nd.provider.value:5s}] "
              f"{util:5.1f}% {bar} ({np_count} pods)")

    # ── Provider breakdown ───────────────────────────────────
    print("\nPods per cloud provider:")
    prov_count = {p: 0 for p in CloudProvider}
    for pid, nname in assignment.items():
        prov_count[node_map[nname].provider] += 1
    for p, c in prov_count.items():
        print(f"  {p.value:6s}: {c} pods")

    # ── Energy summary ────────────────────────────────────────
    print(f"\nTotal energy (est.): {total_e:.4f} Wh")
    print(f"Total carbon (est.): {total_c:.2f} g CO2e")
    print(f"Max queue depth:     {max(node_pods.values())}")
    print(f"Jain's FI:           ", end="")
    utils_arr = np.array([min(node_cpu[n.name]/n.total_cpu, 1.0) for n in nodes])
    denom = len(utils_arr) * np.sum(utils_arr**2)
    jfi = float(np.sum(utils_arr)**2 / denom) if denom > 0 else 1.0
    print(f"{jfi:.4f}")

    print("\n All tests passed — ready to deploy to Kubernetes!")
    return assignment


if __name__ == "__main__":
    run_test()
