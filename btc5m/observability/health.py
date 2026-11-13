"""
HTTP Health check and metrics server.
"""
import http.server
import json
import socketserver
import threading
from typing import Optional
from btc5m.observability.metrics import ObservabilityManager

class MetricsHandler(http.server.SimpleHTTPRequestHandler):
    obs_manager: Optional[ObservabilityManager] = None

    def do_GET(self):
        if self.path == "/health" or self.path == "/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = self.obs_manager.get_system_health() if self.obs_manager else {"status": "ok"}
            self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))
        elif self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            text = self.obs_manager.format_prometheus_metrics() if self.obs_manager else ""
            self.wfile.write(text.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress routine health check logs
        pass

def run_health_server(obs_manager: ObservabilityManager, port: int = 9102) -> socketserver.TCPServer:
    handler = MetricsHandler
    handler.obs_manager = obs_manager
    httpd = socketserver.TCPServer(("", port), handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd
