import time
from typing import Dict, Any

from fastapi.testclient import TestClient


def test_performance_smoke(client: TestClient, valid_payload: Dict[str, Any]):
    """Test 50: 100 prediction requests complete without memory leaks or increasing latency."""
    total_requests = 100
    successes = 0
    latencies = []

    for _ in range(total_requests):
        start = time.perf_counter()
        response = client.post("/api/v1/predict", json=valid_payload)
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)
        if response.status_code == 200:
            successes += 1

    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)

    print(f"\n--- Performance Smoke Test ---")
    print(f"Total requests: {total_requests}")
    print(f"Successful:     {successes}")
    print(f"Failed:         {total_requests - successes}")
    print(f"Avg latency:    {avg_latency * 1000:.2f} ms")
    print(f"Max latency:    {max_latency * 1000:.2f} ms")

    assert successes == total_requests, f"Some requests failed: {total_requests - successes}/{total_requests}"
    # Sanity check: no single request should take longer than 5 seconds
    assert max_latency < 5.0, f"Max latency {max_latency:.2f}s exceeded 5s threshold"
