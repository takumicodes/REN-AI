"""
REN-AI Performance & Latency Benchmark
Measures Time-To-First-Token (TTFT), tokens/sec, memory retrieval speed,
web search latency, and hardware utilization.
"""

import sys
import time
import json
import psutil
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from ren.core.agent import agent_runtime
from ren.memory.manager import memory_manager
from ren.tools.registry import tool_registry
from ren.monitoring.performance import perf_monitor


def run_benchmark():
    print("\n" + "=" * 64)
    print(" [*] REN-AI PERFORMANCE & LATENCY BENCHMARK")
    print("=" * 64)

    # 1. System Hardware Baseline
    hw = perf_monitor.get_system_snapshot()
    initial_cpu = hw.get("cpu_percent", 0.0)
    initial_ram_mb = hw.get("ram_used_mb", 0.0)
    print(f"\n[Hardware Baseline]")
    print(f"  CPU Utilization : {initial_cpu}%")
    print(f"  RAM Allocated   : {initial_ram_mb:.1f} MB (Available: {hw.get('ram_available_mb', 0):.1f} MB)")

    # 2. Fast Path Latency
    t0 = time.perf_counter()
    resp_fast = agent_runtime.process_input("who are you")
    t_fast = (time.perf_counter() - t0) * 1000.0
    print(f"\n[1. Fast-Path Shortcut Latency]")
    print(f"  Latency         : {t_fast:.2f} ms")
    print(f"  Response Sample : '{resp_fast[:60]}...'")

    # 3. User-Scoped Memory Retrieval & BM25 Ranking Latency
    t0 = time.perf_counter()
    mem_ctx = memory_manager.get_relevant_memory_context("What projects are active?", user_id="benchmark_usr")
    t_mem = (time.perf_counter() - t0) * 1000.0
    print(f"\n[2. Memory Ranking & Context Assembly Latency]")
    print(f"  Latency         : {t_mem:.2f} ms")
    print(f"  Context Size    : {len(mem_ctx)} characters")

    # 4. Live Web Search Latency
    search_tool = tool_registry.get_tool("web_search")
    t0 = time.perf_counter()
    search_res = search_tool.run(query="gold price USD")
    t_search = (time.perf_counter() - t0) * 1000.0
    print(f"\n[3. Live Web Search Latency]")
    print(f"  Latency         : {t_search:.2f} ms")
    print(f"  Success         : {search_res.success}")

    # 5. Full Agent Reasoning & Streaming (TTFT & Tokens/sec)
    tokens_received = []
    first_token_time = None
    t_start = time.perf_counter()

    def token_cb(token):
        nonlocal first_token_time
        if first_token_time is None:
            first_token_time = time.perf_counter()
        tokens_received.append(token)

    resp_agent = agent_runtime.process_input(
        "Give a concise 2-sentence summary of the Python GIL.",
        token_callback=token_cb,
        session_id="benchmark_session_1",
        user_id="benchmark_usr"
    )
    t_end = time.perf_counter()

    total_time = (t_end - t_start) * 1000.0
    ttft = ((first_token_time - t_start) * 1000.0) if first_token_time else 0.0
    gen_time_sec = (t_end - first_token_time) if first_token_time else (total_time / 1000.0)
    tokens_count = len(tokens_received)
    tokens_per_sec = (tokens_count / gen_time_sec) if gen_time_sec > 0 else 0.0

    print(f"\n[4. Agent LLM Generation Metrics]")
    print(f"  Time To First Token (TTFT) : {ttft:.2f} ms")
    print(f"  Total Response Time        : {total_time:.2f} ms")
    print(f"  Tokens Streamed            : {tokens_count} chunks")
    print(f"  Generation Throughput      : {tokens_per_sec:.1f} tokens/sec")

    # Final Hardware Utilization
    hw_post = perf_monitor.get_system_snapshot()
    print(f"\n[5. Post-Benchmark Hardware Utilization]")
    print(f"  CPU Utilization : {hw_post.get('cpu_percent', 0.0)}%")
    print(f"  RAM Allocated   : {hw_post.get('ram_used_mb', 0.0):.1f} MB")

    print("\n" + "=" * 64)
    print(" [PASS] BENCHMARK COMPLETE")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    run_benchmark()
