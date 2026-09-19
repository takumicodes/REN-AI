"""
Lightweight Deterministic Benchmark Center for REN-AI Windows Control Center
Provides:
- Safe, offline CPU, Memory, and Disk I/O benchmark.
- Repeatable score indexing.
- Historical score logging to compare performance before and after optimizations.
"""

import os
import sys
import time
import json
import hashlib
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional


def get_benchmark_file_path() -> Path:
    """Returns persistent path for benchmark history."""
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        portable = exe_dir / "benchmarks.json"
        if portable.exists():
            return portable
        appdata = os.environ.get("LOCALAPPDATA")
        base = Path(appdata) / "RenDesktopAssistant" if appdata else Path.home() / ".ren_desktop_assistant"
    else:
        base = Path(__file__).parent

    try:
        os.makedirs(str(base), exist_ok=True)
    except Exception:
        pass
    return base / "benchmarks.json"


class BenchmarkCenter:
    """Executes deterministic CPU, RAM, and Disk tests and records history."""

    def __init__(self):
        self.history_file = get_benchmark_file_path()

    def run_benchmark(self) -> Dict[str, Any]:
        """
        Executes a 3-part lightweight benchmark:
        1. CPU: Hashing iterations & prime calculations.
        2. Memory: Allocation and read/write throughput.
        3. Disk: Sequential 32MB write/read in temp.
        """
        start_overall = time.time()

        # 1. CPU Test (Deterministic SHA-256 rounds)
        t0 = time.time()
        cpu_ops = 0
        target_duration = 1.0  # 1 second test
        data = b"REN-AI-BENCHMARK-PAYLOAD-V1.3.0"
        while (time.time() - t0) < target_duration:
            for _ in range(5000):
                data = hashlib.sha256(data).digest()
            cpu_ops += 5000
        cpu_score = int(cpu_ops / 100)

        # 2. Memory Test (Allocation and copy)
        t0 = time.time()
        mem_ops = 0
        buf_size = 8 * 1024 * 1024  # 8 MB buffer
        while (time.time() - t0) < target_duration:
            buf = bytearray(buf_size)
            buf[::4096] = b"\xff" * (buf_size // 4096)
            mem_ops += 1
        mem_mb_s = (mem_ops * 8) / (time.time() - t0)
        mem_score = int(mem_mb_s * 5)

        # 3. Disk Test (Sequential Write & Read)
        temp_file = Path(tempfile.gettempdir()) / "ren_bench.tmp"
        test_bytes = b"X" * (16 * 1024 * 1024)  # 16 MB

        t0 = time.time()
        try:
            with open(temp_file, "wb") as f:
                f.write(test_bytes)
                f.flush()
                os.fsync(f.fileno())
            write_duration = max(0.001, time.time() - t0)
            write_speed_mb = 16.0 / write_duration

            t1 = time.time()
            with open(temp_file, "rb") as f:
                _ = f.read()
            read_duration = max(0.001, time.time() - t1)
            read_speed_mb = 16.0 / read_duration
        finally:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass

        disk_score = int((write_speed_mb + read_speed_mb) * 3)

        # Composite score
        composite_score = int((cpu_score * 0.4) + (mem_score * 0.3) + (disk_score * 0.3))

        result = {
            "timestamp": time.time(),
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S"),
            "composite_score": composite_score,
            "cpu_score": cpu_score,
            "cpu_ops": cpu_ops,
            "memory_score": mem_score,
            "memory_speed_mb_s": round(mem_mb_s, 1),
            "disk_score": disk_score,
            "disk_write_mb_s": round(write_speed_mb, 1),
            "disk_read_mb_s": round(read_speed_mb, 1),
            "duration_seconds": round(time.time() - start_overall, 2),
        }

        self._save_result(result)
        return result

    def _save_result(self, result: Dict[str, Any]):
        """Persists benchmark result to history file."""
        history = self.get_history()
        history.insert(0, result)
        if len(history) > 30:
            history = history[:30]

        try:
            temp_path = self.history_file.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2)
            temp_path.replace(self.history_file)
        except Exception:
            pass

    def get_history(self) -> List[Dict[str, Any]]:
        """Retrieves historical benchmark runs."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []


benchmark_center = BenchmarkCenter()
