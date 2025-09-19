from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):
    """Simple test handler"""
    
    def do_POST(self):
        try:
            # Read request
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                request_data = json.loads(post_data.decode('utf-8'))
            else:
                request_data = {}
            
            # Test environment variables
            env_check = {
                "SALESFORCE_USERNAME": "SET" if os.getenv("SALESFORCE_USERNAME") else "MISSING",
                "SALESFORCE_PASSWORD": "SET" if os.getenv("SALESFORCE_PASSWORD") else "MISSING", 
                "SALESFORCE_SECURITY_TOKEN": "SET" if os.getenv("SALESFORCE_SECURITY_TOKEN") else "MISSING"
            }
            
            # Show ALL environment variables that start with "SALESFORCE"
            all_sf_vars = {k: "SET" for k, v in os.environ.items() if k.startswith("SALESFORCE")}
            
            # Also check for other common variations
            other_vars = {}
            for name in ["USERNAME", "PASSWORD", "SECURITY_TOKEN", "SF_USERNAME", "SF_PASSWORD", "SF_SECURITY_TOKEN"]:
                if os.getenv(name):
                    other_vars[name] = "SET"
            
            # Test Salesforce connection
            try:
                from simple_salesforce import Salesforce
                sf = Salesforce(
                    username=os.getenv("SALESFORCE_USERNAME"),
                    password=os.getenv("SALESFORCE_PASSWORD"),
                    security_token=os.getenv("SALESFORCE_SECURITY_TOKEN")
                )
                # Try a simple query
                result = sf.query("SELECT COUNT() FROM Account")
                sf_status = f"SUCCESS - Found {result['totalSize']} accounts"
            except Exception as e:
                sf_status = f"ERROR: {str(e)}"
            
            # JSON-RPC response
            response = {
                "jsonrpc": "2.0",
                "id": request_data.get("id", 1),
                "result": {
                    "environment": env_check,
                    "all_salesforce_vars": all_sf_vars,
                    "other_possible_vars": other_vars,
                    "salesforce_test": sf_status,
                    "request_received": request_data
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response, indent=2).encode('utf-8'))
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {
                    "code": -32603,
                    "message": "Internal server error",
                    "data": str(e)
                }
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(error_response, indent=2).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
