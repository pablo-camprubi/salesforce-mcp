import json
import os
from typing import Any, Dict, List, Optional
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def _set_response(self, content: str = "", content_type: str = "application/json", status: int = 200):
        """Helper to set HTTP response headers"""
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Salesforce-Credentials, X-Salesforce-Encrypted-Credentials')
        self.end_headers()
        if content:
            self.wfile.write(content.encode('utf-8'))

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._set_response()

    def do_GET(self):
        """Handle GET requests - health check"""
        try:
            if self.path == "/debug":
                debug_info = {
                    "status": "minimal_server",
                    "environment": {
                        "VERCEL": os.environ.get("VERCEL", "not_set"),
                        "LAMBDA_TASK_ROOT": os.environ.get("LAMBDA_TASK_ROOT", "not_set"),
                        "PYTHONPATH": os.environ.get("PYTHONPATH", "not_set")
                    },
                    "message": "Running minimal MCP server to test deployment"
                }
                self._set_response(json.dumps(debug_info, indent=2))
                return
                
            # Basic health check
            response = {
                "status": "healthy",
                "message": "Minimal Salesforce MCP server is running", 
                "timestamp": "2025-09-24T17:30:00Z",
                "server_type": "minimal_test"
            }
            self._set_response(json.dumps(response, indent=2))
            
        except Exception as e:
            error_response = {
                "status": "error", 
                "message": f"Health check failed: {str(e)}"
            }
            self._set_response(json.dumps(error_response, indent=2), status=500)

    def do_POST(self):
        """Handle POST requests - MCP JSON-RPC"""
        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                raise ValueError("Empty request body")
                
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Handle MCP method calls
            method = request_data.get("method", "")
            request_id = request_data.get("id", "unknown")
            
            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "tools": [
                            {
                                "name": "test_tool",
                                "description": "Test tool to verify server is working",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string"}
                                    }
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                response = {
                    "jsonrpc": "2.0", 
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": "Minimal server is working! Full functionality will be restored once dependencies are resolved."
                            }
                        ]
                    }
                }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            self._set_response(json.dumps(response))
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": request_data.get("id", "unknown") if 'request_data' in locals() else "unknown",
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}"
                }
            }
            self._set_response(json.dumps(error_response), status=500)
