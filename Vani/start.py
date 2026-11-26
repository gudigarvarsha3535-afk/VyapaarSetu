import sys
import subprocess
import time
import os
from pathlib import Path
import threading
import uvicorn
from http.server import SimpleHTTPRequestHandler
import socketserver

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT_DIR / "frontend"

class SPAHandler(SimpleHTTPRequestHandler):
    """Serves frontend directory, routing unknown routes to index.html for SPA support."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        # Map /seller or root to index.html
        if self.path in ("/", "/seller", "/seller/"):
            self.path = "/index.html"
        return super().do_GET()

def run_frontend_server(port=5173):
    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True
    
    try:
        with ReusableTCPServer(("", port), SPAHandler) as httpd:
            print(f"[Frontend Dev Server] Running at http://localhost:{port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"[Frontend Dev Server Warning] Port {port} could not be bound ({e}); frontend is still accessible directly via backend at http://localhost:8000")

def run_backend_server(port=8000):
    print(f"[Backend API Server] Running at http://localhost:{port}")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False, log_level="info")

if __name__ == "__main__":
    t_fe = threading.Thread(target=run_frontend_server, args=(5173,), daemon=True)
    t_fe.start()

    time.sleep(0.5)
    run_backend_server(8000)
