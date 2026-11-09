"""Automatischer Pairing-Beacon und Netzwerk-Erkennung für SCHOENI DIGITAL & Orca."""
from __future__ import annotations

import concurrent.futures
import http.server
import json
import socket
import subprocess
import threading
import urllib.request
from typing import Any

BEACON_PORT = 6769
ORCA_PORT = 6768


def get_tailscale_peers() -> list[dict[str, Any]]:
    """Ermittelt alle Peers aus dem aktuellen Tailscale-Netzwerk."""
    try:
        res = subprocess.run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=3)
        if res.returncode != 0 or not res.stdout.strip():
            return []
        data = json.loads(res.stdout)
        peers = []
        for _, peer in (data.get("Peer") or {}).items():
            ips = peer.get("TailscaleIPs") or []
            if not ips:
                continue
            peers.append({
                "hostname": peer.get("HostName", "unbekannt"),
                "dns_name": peer.get("DNSName", "").rstrip("."),
                "os": peer.get("OS", "unbekannt"),
                "online": peer.get("Online", False),
                "ip": ips[0],
            })
        return peers
    except Exception:
        return []


def probe_beacon(ip: str, port: int = BEACON_PORT, timeout: float = 1.0) -> dict[str, Any] | None:
    """Prüft, ob unter der IP ein sdc Pairing-Beacon aktiv ist."""
    url = f"http://{ip}:{port}/sdc-pair"
    req = urllib.request.Request(url, headers={"User-Agent": "sdc-cli-scanner"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    data["discovered_ip"] = ip
                    return data
    except Exception:
        pass
    return None


def scan_beacons(timeout: float = 1.0) -> list[dict[str, Any]]:
    """Scannt Tailscale-Peers und Localhost parallel nach aktiven Pairing-Beacons."""
    candidate_ips: set[str] = {"127.0.0.1"}

    for peer in get_tailscale_peers():
        candidate_ips.add(peer["ip"])

    discovered: list[dict[str, Any]] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(candidate_ips) or 1, 10)) as executor:
        futures = {executor.submit(probe_beacon, ip, BEACON_PORT, timeout): ip for ip in candidate_ips}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                discovered.append(res)

    return discovered


def notify_paired(beacon_ip: str, client_name: str, port: int = BEACON_PORT, timeout: float = 3.0) -> bool:
    """Sendet eine Bestätigung an den Beacon, dass die Kopplung erfolgt ist."""
    url = f"http://{beacon_ip}:{port}/sdc-paired"
    payload = json.dumps({"paired_by": client_name}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "sdc-cli"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


class PairingRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP-Handler für den sdc Pairing-Beacon."""

    device_data: dict[str, Any] = {}
    paired_event: threading.Event = threading.Event()
    paired_by: str = ""

    def log_message(self, format: str, *args: Any) -> None:
        # Standard HTTP-Logs stumm schalten für saubere CLI-Ausgabe
        pass

    def do_GET(self) -> None:
        if self.path in ("/", "/sdc-pair"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(self.device_data).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/sdc-paired":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length > 0 else b"{}"
            try:
                data = json.loads(body.decode("utf-8"))
                PairingRequestHandler.paired_by = data.get("paired_by", "Remote-Gerät")
            except Exception:
                PairingRequestHandler.paired_by = "Remote-Gerät"

            PairingRequestHandler.paired_event.set()

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


class BeaconServer:
    """Startet und verwaltet den lokalen Pairing-Beacon-Server."""

    def __init__(self, device_data: dict[str, Any], port: int = BEACON_PORT, host: str = "0.0.0.0") -> None:
        self.port = port
        self.host = host
        PairingRequestHandler.device_data = device_data
        PairingRequestHandler.paired_event.clear()
        PairingRequestHandler.paired_by = ""
        self.server = http.server.ThreadingHTTPServer((host, port), PairingRequestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def wait_for_paired(self, timeout: float | None = None) -> bool:
        return PairingRequestHandler.paired_event.wait(timeout=timeout)

    @property
    def paired_by(self) -> str:
        return PairingRequestHandler.paired_by
