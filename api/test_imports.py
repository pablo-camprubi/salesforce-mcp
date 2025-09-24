import json
import sys
import os
from typing import Any, Dict, List, Optional
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def _set_response(self, content: str = "", content_type: str = "application/json", status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        if content:
            self.wfile.write(content.encode('utf-8'))

    def do_GET(self):
        try:
            # Test progressive imports
            import_results = {
                "basic_imports": True,
                "import_tests": {}
            }
            
            # Test 1: Basic simple-salesforce
            try:
                import simple_salesforce
                import_results["import_tests"]["simple_salesforce"] = "SUCCESS"
            except Exception as e:
                import_results["import_tests"]["simple_salesforce"] = f"ERROR: {str(e)}"
            
            # Test 2: Cryptography
            try:
                from cryptography.fernet import Fernet
                import_results["import_tests"]["cryptography"] = "SUCCESS"
            except Exception as e:
                import_results["import_tests"]["cryptography"] = f"ERROR: {str(e)}"
            
            # Test 3: Requests
            try:
                import requests
                import_results["import_tests"]["requests"] = "SUCCESS"
            except Exception as e:
                import_results["import_tests"]["requests"] = f"ERROR: {str(e)}"
            
            # Test 4: Local salesforcemcp modules (one by one)
            try:
                from .salesforcemcp import sfdc_client
                import_results["import_tests"]["sfdc_client"] = "SUCCESS"
            except Exception as e:
                import_results["import_tests"]["sfdc_client"] = f"ERROR: {str(e)}"
                
            try:
                from .salesforcemcp import definitions
                import_results["import_tests"]["definitions"] = "SUCCESS"
            except Exception as e:
                import_results["import_tests"]["definitions"] = f"ERROR: {str(e)}"
            
            try:
                from .salesforcemcp import implementations
                import_results["import_tests"]["implementations"] = "SUCCESS"
            except Exception as e:
                import_results["import_tests"]["implementations"] = f"ERROR: {str(e)}"
            
            # Show environment info
            import_results["environment"] = {
                "python_version": sys.version,
                "python_path": sys.path[:5],  # First 5 entries
                "current_dir": os.path.dirname(__file__),
                "files_in_api": os.listdir(os.path.dirname(__file__)) if os.path.exists(os.path.dirname(__file__)) else "N/A"
            }
            
            self._set_response(json.dumps(import_results, indent=2))
            
        except Exception as e:
            error_response = {
                "status": "error",
                "message": f"Test failed: {str(e)}",
                "python_version": sys.version
            }
            self._set_response(json.dumps(error_response, indent=2), status=500)

    def do_POST(self):
        # Simple echo for POST requests
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            response = {
                "jsonrpc": "2.0",
                "id": request_data.get("id", "test"),
                "result": {
                    "status": "Import test server is working",
                    "method": request_data.get("method", "unknown")
                }
            }
            self._set_response(json.dumps(response))
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": "error",
                "error": {"code": -32603, "message": str(e)}
            }
            self._set_response(json.dumps(error_response), status=500)
