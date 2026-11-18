#!/usr/bin/env python3
"""Exercise the real Caddy binary using synthetic loopback-only requests."""

import argparse
import json
import os
import socket
import subprocess
import tempfile
import time
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

PROFILE = Path(__file__).resolve().parents[2] / "compose/caddy-public/Caddyfile"


class Echo(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(dict(self.headers)).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def unused_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def request(port, *, host="chat.example.com", scheme="https"):
    connection = HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        connection.request("GET", "/sample?test=1", headers={
            "Host": host, "CF-Connecting-IP": "203.0.113.9",
            "X-Forwarded-Proto": scheme, "X-Forwarded-For": "198.51.100.9",
        })
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        connection.close()


def exercise(binary, peer, backend):
    port = unused_port()
    config = PROFILE.read_text().replace("{\n", "{\n\tadmin off\n", 1)
    config = config.replace(":8080 {", f":{port} {{\n\tbind 127.0.0.1")
    with tempfile.TemporaryDirectory(prefix="caddy-proxy-smoke-") as directory:
        path = Path(directory) / "Caddyfile"
        path.write_text(config)
        env = os.environ.copy()
        env.update(ZULIP_FQDN="chat.example.com", ZULIP_UPSTREAM=f"http://127.0.0.1:{backend}",
                   CLOUDFLARED_CONTAINER_IP=peer, XDG_DATA_HOME=directory, XDG_CONFIG_HOME=directory)
        with (Path(directory) / "process.log").open("w+") as output:
            process = subprocess.Popen([binary, "run", "--config", str(path), "--adapter", "caddyfile"],
                                       env=env, stdout=output, stderr=output)
            try:
                deadline = time.monotonic() + 10
                while True:
                    if process.poll() is not None:
                        raise AssertionError("Caddy exited before the synthetic smoke test")
                    try:
                        response = request(port)
                        break
                    except (OSError, TimeoutError):
                        if time.monotonic() >= deadline:
                            raise AssertionError("Caddy did not become ready") from None
                        time.sleep(0.05)
                if peer != "127.0.0.1":
                    assert response[0] == 403, "Untrusted peer reached the proxy"
                    return
                assert response[0] == 200, "Trusted tunnel request failed"
                headers = {key.lower(): value for key, value in json.loads(response[2]).items()}
                assert headers["x-forwarded-proto"] == "https", "HTTPS scheme was lost"
                assert headers["x-forwarded-for"] == "203.0.113.9", "Client IP was spoofed or lost"
                assert headers["host"] == "chat.example.com", "Public Host was lost"
                assert request(port, host="unconfigured.example.com")[0] == 404, "Unknown hostname was routed"
                status, headers, _ = request(port, scheme="http")
                assert status == 308 and headers["Location"] == "https://chat.example.com/sample?test=1"
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--caddy", required=True)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", 0), Echo)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        exercise(args.caddy, "127.0.0.1", server.server_port)
        exercise(args.caddy, "127.0.0.2", server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print("Proxy smoke passed: HTTPS, real client IP, redirects, hostname isolation and peer rejection.")


if __name__ == "__main__":
    main()
