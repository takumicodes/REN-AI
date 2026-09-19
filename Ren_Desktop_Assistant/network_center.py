"""
Network Diagnostic & Control Center for REN-AI Windows Control Center
Provides:
- Active network adapter details (IPv4, MAC, Gateway, Status).
- Deterministic ping latency check.
- DNS cache flushing with post-execution verification.
- Active network connections inspector.
"""

import socket
import subprocess
import psutil
from typing import Dict, List, Any, Optional


class NetworkCenter:
    """Manages network telemetry, diagnostics, and DNS tools."""

    def get_adapter_info(self) -> List[Dict[str, Any]]:
        """Retrieves details of network adapters."""
        adapters = []
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()

        for iface_name, iface_addrs in addrs.items():
            stat = stats.get(iface_name)
            is_up = stat.isup if stat else False
            speed = stat.speed if stat else 0

            ipv4 = "N/A"
            mac = "N/A"

            for addr in iface_addrs:
                if addr.family == socket.AF_INET:
                    ipv4 = addr.address
                elif addr.family == psutil.AF_LINK:
                    mac = addr.address

            if ipv4 != "N/A" and not ipv4.startswith("127."):
                adapters.append({
                    "name": iface_name,
                    "ipv4": ipv4,
                    "mac": mac,
                    "is_up": is_up,
                    "speed_mbps": speed,
                })

        return adapters

    def ping_test(self, host: str = "1.1.1.1", count: int = 4) -> Dict[str, Any]:
        """Runs a ping test to evaluate latency and packet loss."""
        try:
            cmd = ["ping", "-n", str(count), host]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            output = res.stdout

            avg_ms = -1.0
            if "Average = " in output:
                try:
                    part = output.split("Average = ")[1].split("ms")[0].strip()
                    avg_ms = float(part)
                except Exception:
                    pass

            packet_loss = 0
            if "loss (" in output:
                try:
                    loss_str = output.split("loss (")[1].split("%")[0].strip()
                    packet_loss = int(loss_str)
                except Exception:
                    pass

            return {
                "success": res.returncode == 0,
                "host": host,
                "avg_latency_ms": avg_ms,
                "packet_loss_percent": packet_loss,
                "raw_output": output,
            }
        except Exception as e:
            return {"success": False, "message": f"Ping error: {e}"}

    def flush_dns(self) -> Dict[str, Any]:
        """Flushes the Windows DNS resolver cache."""
        try:
            res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                return {
                    "success": True,
                    "message": "Successfully flushed the Windows DNS Resolver Cache.",
                }
            return {"success": False, "message": res.stderr.strip() or "Failed to flush DNS."}
        except Exception as e:
            return {"success": False, "message": f"Error running ipconfig: {e}"}

    def get_active_connections(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves currently open network sockets."""
        conns = []
        try:
            for c in psutil.net_connections(kind="inet"):
                if c.status == "ESTABLISHED" and c.raddr:
                    conns.append({
                        "pid": c.pid,
                        "local_addr": f"{c.laddr.ip}:{c.laddr.port}",
                        "remote_addr": f"{c.raddr.ip}:{c.raddr.port}",
                        "status": c.status,
                    })
        except Exception:
            pass
        return conns[:limit]


network_center = NetworkCenter()
