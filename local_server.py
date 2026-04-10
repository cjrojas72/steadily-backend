"""Local dev server — translates HTTP requests into Lambda events and calls the handler."""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from lambda_handler import handler


class LambdaRequestHandler(BaseHTTPRequestHandler):
    def _build_event(self, method):
        parsed = urlparse(self.path)
        # Flatten query params (parse_qs returns lists)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()} or None

        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else None

        # Build headers dict (lowercase keys like API Gateway v2)
        headers = {k.lower(): v for k, v in self.headers.items()}

        return {
            "rawPath": parsed.path,
            "requestContext": {"http": {"method": method, "path": parsed.path}},
            "headers": headers,
            "queryStringParameters": query,
            "body": body,
            "isBase64Encoded": False,
        }

    def _handle(self, method):
        event = self._build_event(method)
        result = handler(event, None)

        self.send_response(result["statusCode"])
        for key, value in result.get("headers", {}).items():
            self.send_header(key, value)
        self.end_headers()

        body = result.get("body", "")
        if body:
            self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_DELETE(self):
        self._handle("DELETE")

    def do_OPTIONS(self):
        self._handle("OPTIONS")


if __name__ == "__main__":
    port = 5000
    server = HTTPServer(("0.0.0.0", port), LambdaRequestHandler)
    print(f"Local dev server running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    server.serve_forever()
