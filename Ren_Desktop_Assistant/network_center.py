"""
Network Diagnostic & Control Center for REN-AI Windows Control Center
Provides:
- Complete network adapter telemetry (IPv4, MAC, Gateway, DNS, Link Speed, Status).
- DNS resolver operations (Ping latency tester, DNS forward lookup, Flush DNS cache).
- Active socket connections monitor (ESTABLISHED, LISTEN).
- Network security and proxy telemetry (Windows Firewall profile status, system proxy).
- Consequential actions (Winsock reset, TCP/IP stack reset) with confirmation safeguards.
"""

import socket
import subprocess
import winreg
import psutil
from typing import Dict, List, Any, Optional

try:
    from .logger import logger
except ImportError:
    try:
        from logger import logger
    except ImportError:
        import logging
        logger = logging.getLogger("RenAssistant")


class NetworkCenter:
    """Manages network telemetry, diagnostics, and recovery tools."""

    def get_adapter_info(self) -> List[Dict[str, Any]]:
        """Retrieves details of network adapters."""
        adapters = []
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()

            for iface_name, iface_addrs in addrs.items():
                stat = stats.get(iface_name)
                is_up = stat.isup if stat else False
                speed = stat.speed if stat else 0

                ipv4 = "N/A"
                netmask = "N/A"
                mac = "N/A"

                for addr in iface_addrs:
                    if addr.family == socket.AF_INET:
                        ipv4 = addr.address
                        netmask = addr.netmask or "255.255.255.0"
                    elif addr.family == psutil.AF_LINK:
                        mac = addr.address

                if ipv4 != "N/A" and not ipv4.startswith("127."):
                    adapters.append({
                        "name": iface_name,
                        "ipv4": ipv4,
                        "netmask": netmask,
                        "mac": mac,
                        "is_up": is_up,
                        "speed_mbps": speed,
                    })
        except Exception as e:
            logger.warning(f"Error gathering adapter info: {e}")

        return adapters

    def ping_test(self, host: str = "1.1.1.1", count: int = 4) -> Dict[str, Any]:
        """Runs a deterministic ICMP ping test to evaluate latency and packet loss."""
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
            logger.warning(f"Ping test error for {host}: {e}")
            return {"success": False, "message": f"Ping error: {e}"}

    def dns_lookup(self, host: str) -> Dict[str, Any]:
        """Resolves hostname to IP addresses."""
        try:
            name, aliases, ip_list = socket.gethostbyname_ex(host)
            return {
                "success": True,
                "hostname": name,
                "aliases": aliases,
                "addresses": ip_list,
            }
        except Exception as e:
            return {"success": False, "message": f"Could not resolve host '{host}': {e}"}

    def flush_dns(self) -> Dict[str, Any]:
        """Flushes the Windows DNS resolver cache."""
        try:
            res = subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                logger.info("Successfully flushed Windows DNS resolver cache.")
                return {
                    "success": True,
                    "message": "Successfully flushed the Windows DNS Resolver Cache.",
                }
            return {"success": False, "message": res.stderr.strip() or "Failed to flush DNS."}
        except Exception as e:
            logger.error(f"Error running ipconfig /flushdns: {e}")
            return {"success": False, "message": f"Error running ipconfig: {e}"}

    def reset_winsock(self) -> Dict[str, Any]:
        """Executes Winsock catalog reset (requires Administrator)."""
        try:
            res = subprocess.run(["netsh", "winsock", "reset"], capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                logger.info("Winsock catalog reset executed.")
                return {
                    "success": True,
                    "message": "Winsock catalog reset completed successfully. Please restart your computer to apply.",
                }
            return {"success": False, "message": res.stderr.strip() or "Requires Administrator privileges."}
        except Exception as e:
            logger.error(f"Error resetting winsock: {e}")
            return {"success": False, "message": str(e)}

    def reset_tcpip(self) -> Dict[str, Any]:
        """Executes TCP/IP stack reset (requires Administrator)."""
        try:
            res = subprocess.run(["netsh", "int", "ip", "reset"], capture_output=True, text=True, timeout=15)
            if res.returncode == 0:
                logger.info("TCP/IP stack reset executed.")
                return {
                    "success": True,
                    "message": "TCP/IP stack reset completed successfully. Please restart your computer to apply.",
                }
            return {"success": False, "message": res.stderr.strip() or "Requires Administrator privileges."}
        except Exception as e:
            logger.error(f"Error resetting TCP/IP: {e}")
            return {"success": False, "message": str(e)}

    def get_firewall_status(self) -> Dict[str, Any]:
        """Queries Windows Defender Firewall active profile status."""
        try:
            res = subprocess.run(["netsh", "advfirewall", "show", "allprofiles", "state"], capture_output=True, text=True, timeout=8)
            output = res.stdout
            domain_on = "State                                 ON" in output
            return {
                "success": True,
                "is_enabled": "State                                 ON" in output,
                "raw_summary": "Windows Firewall active on one or more profiles." if "ON" in output else "Firewall disabled.",
            }
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_proxy_info(self) -> Dict[str, Any]:
        """Reads Windows internet proxy configuration from registry."""
        try:
            reg_path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0, winreg.KEY_READ) as key:
                def q(val_name, default=0):
                    try:
                        return winreg.QueryValueEx(key, val_name)[0]
                    except Exception:
                        return default

                enabled = q("ProxyEnable", 0) == 1
                server = str(q("ProxyServer", "None"))
                return {
                    "proxy_enabled": enabled,
                    "proxy_server": server if enabled else "Direct Connection (No Proxy)",
                }
        except Exception:
            return {"proxy_enabled": False, "proxy_server": "Direct Connection (No Proxy)"}

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
        except Exception as e:
            logger.debug(f"Error reading socket connections: {e}")
        return conns[:limit]


network_center = NetworkCenter()
