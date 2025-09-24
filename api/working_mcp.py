import json
import sys
import os
from typing import Any, Dict, List, Optional
from http.server import BaseHTTPRequestHandler

# Import handling with local modules for serverless environment
try:
    from .salesforcemcp import sfdc_client
    from .salesforcemcp import definitions as sfmcpdef
    from .salesforcemcp import implementations as sfmcpimpl
    print("Successfully imported Salesforce MCP modules")
except ImportError as e:
    print(f"Import error for MCP modules: {e}")
    sfdc_client = None
    sfmcpdef = None
    sfmcpimpl = None

# Minimal types for MCP compatibility
class TextContent:
    def __init__(self, type: str, text: str):
        self.type = type
        self.text = text

def get_sf_client(credentials: Optional[Dict[str, str]] = None, encrypted_credentials: Optional[str] = None, request_headers: Optional[Dict[str, str]] = None):
    """Get a fresh Salesforce client connection with provided or inferred credentials."""
    if not sfdc_client:
        return None
    
    client = sfdc_client.OrgHandler()
    
    try:
        # Priority order: encrypted_credentials, credentials, headers, environment variables
        if encrypted_credentials:
            if not client.establish_connection_with_encrypted_credentials(encrypted_credentials):
                return None
        elif credentials:
            if not client.establish_connection(
                username=credentials.get('username'),
                password=credentials.get('password'),
                security_token=credentials.get('security_token')
            ):
                return None
        elif request_headers:
            sf_encrypted_header = request_headers.get('X-Salesforce-Encrypted-Credentials', '')
            sf_credentials_header = request_headers.get('X-Salesforce-Credentials', '')
            
            if sf_encrypted_header:
                if not client.establish_connection_with_encrypted_credentials(sf_encrypted_header):
                    return None
            elif sf_credentials_header:
                try:
                    creds = json.loads(sf_credentials_header)
                    if not client.establish_connection(
                        username=creds.get('username'),
                        password=creds.get('password'),
                        security_token=creds.get('security_token')
                    ):
                        return None
                except json.JSONDecodeError:
                    return None
            else:
                # Use environment variables
                if not client.establish_connection():
                    return None
        else:
            # Use environment variables as fallback
            if not client.establish_connection():
                return None
                
        return client
        
    except Exception as e:
        print(f"Error establishing connection: {e}")
        return None

def handle_health_check(request_id: Any, params: Dict[str, Any], request_headers: Optional[Dict[str, str]] = None):
    """Handle health check requests"""
    import datetime
    
    try:
        client = get_sf_client(request_headers=request_headers)
        connection_status = "healthy" if client else "no_connection"
        
        return {
            "status": connection_status,
            "timestamp": datetime.datetime.now().isoformat(),
            "modules": {
                "sfdc_client": sfdc_client is not None,
                "sfmcpdef": sfmcpdef is not None,
                "sfmcpimpl": sfmcpimpl is not None
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.datetime.now().isoformat()
        }

def handle_list_tools(request_id: Any, params: Dict[str, Any], request_headers: Optional[Dict[str, str]] = None):
    """Handle tools list requests"""
    try:
        if not sfmcpdef:
            return {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "Test tool - modules not loaded",
                        "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}}
                    }
                ]
            }
        
        tools = sfmcpdef.get_tools()
        tools_list = []
        for tool in tools:
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        
        return {"tools": tools_list}
        
    except Exception as e:
        return {
            "tools": [
                {
                    "name": "error_tool",
                    "description": f"Error loading tools: {str(e)}",
                    "inputSchema": {"type": "object"}
                }
            ]
        }

def handle_call_tool(name: str, arguments: dict[str, Any], request_headers: Optional[Dict[str, str]] = None):
    """Handle tool call requests"""
    try:
        # Extract credentials from arguments
        credentials = arguments.pop('_sf_credentials', None)
        encrypted_credentials = arguments.pop('_sf_encrypted_credentials', None)
        
        # Get SF client 
        client = get_sf_client(
            credentials=credentials,
            encrypted_credentials=encrypted_credentials,
            request_headers=request_headers
        )
        
        if not client:
            return {
                "content": [TextContent("text", "Error: Could not establish Salesforce connection. Please provide valid credentials.")]
            }
        
        if not sfmcpimpl:
            return {
                "content": [TextContent("text", f"Error: Implementation modules not available for tool: {name}")]
            }
        
        # Call the appropriate implementation
        if name == "create_object":
            return sfmcpimpl.create_object_impl(client, arguments)
        elif name == "create_einstein_model":
            return sfmcpimpl.create_einstein_model_impl(client, arguments)
        elif name == "create_tab":
            return sfmcpimpl.create_tab_impl(client, arguments)
        elif name == "create_custom_app":
            return sfmcpimpl.create_custom_app_impl(client, arguments)
        elif name == "query_salesforce":
            return sfmcpimpl.query_salesforce_impl(client, arguments)
        elif name == "create_record":
            return sfmcpimpl.create_record_impl(client, arguments)
        elif name == "update_record":
            return sfmcpimpl.update_record_impl(client, arguments)
        elif name == "delete_record":
            return sfmcpimpl.delete_record_impl(client, arguments)
        elif name == "search_salesforce":
            return sfmcpimpl.search_salesforce_impl(client, arguments)
        elif name == "create_folder":
            return sfmcpimpl.create_folder_impl(client, arguments)
        else:
            return {
                "content": [TextContent("text", f"Unknown tool: {name}")]
            }
            
    except Exception as e:
        return {
            "content": [TextContent("text", f"Error calling tool {name}: {str(e)}")]
        }

class handler(BaseHTTPRequestHandler):
    def _set_response(self, content: str = "", content_type: str = "application/json", status: int = 200):
        """Helper to set HTTP response headers"""
        try:
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Salesforce-Credentials, X-Salesforce-Encrypted-Credentials')
            self.end_headers()
            if content:
                self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            print(f"Error in _set_response: {e}")

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self._set_response()

    def do_GET(self):
        """Handle GET requests - health check and SSE connection"""
        try:
            # Handle save-credentials endpoint
            if self.path == '/save-credentials':
                # This endpoint is used by clients to test credential saving
                response = {
                    "status": "success",
                    "message": "Credentials endpoint ready for POST requests"
                }
                self._set_response(json.dumps(response, indent=2))
                return
            
            # Check if client is requesting SSE connection
            accept_header = self.headers.get('Accept', '')
            if 'text/event-stream' in accept_header or self.path == '/sse':
                # Set up SSE connection
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Salesforce-Credentials, X-Salesforce-Encrypted-Credentials')
                self.end_headers()
                
                # Send initial SSE message
                headers_dict = dict(self.headers.items())
                result = handle_health_check("health_check", {}, headers_dict)
                
                # Format as SSE
                sse_data = json.dumps({
                    "jsonrpc": "2.0",
                    "id": "health-check",
                    "result": result
                })
                
                self.wfile.write(f"data: {sse_data}\n\n".encode('utf-8'))
                self.wfile.flush()
                return
            
            # Regular health check
            headers_dict = dict(self.headers.items())
            result = handle_health_check("health_check", {}, headers_dict)
            
            response = {
                "jsonrpc": "2.0",
                "id": "health-check",
                "result": result
            }
            
            self._set_response(json.dumps(response, indent=2))
            
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": "health-check-error",
                "error": {"code": -32603, "message": str(e)}
            }
            self._set_response(json.dumps(error_response, indent=2), status=500)

    def do_POST(self):
        """Handle POST requests - MCP JSON-RPC and credential saving"""
        try:
            # Handle save-credentials endpoint
            if self.path == '/save-credentials':
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length > 0:
                    post_data = self.rfile.read(content_length)
                    try:
                        credential_data = json.loads(post_data.decode('utf-8'))
                        
                        # Test the provided credentials by creating a client
                        client = get_sf_client(
                            credentials=credential_data.get('credentials'),
                            encrypted_credentials=credential_data.get('encrypted_credentials')
                        )
                        
                        if client:
                            response = {
                                "status": "success",
                                "message": "Credentials validated successfully",
                                "connection_test": "passed"
                            }
                        else:
                            response = {
                                "status": "error", 
                                "message": "Invalid credentials - could not establish Salesforce connection",
                                "connection_test": "failed"
                            }
                        
                        self._set_response(json.dumps(response, indent=2))
                        return
                        
                    except json.JSONDecodeError:
                        error_response = {
                            "status": "error",
                            "message": "Invalid JSON in request body"
                        }
                        self._set_response(json.dumps(error_response), status=400)
                        return
                else:
                    # No body provided
                    response = {
                        "status": "error",
                        "message": "No credentials provided in request body"
                    }
                    self._set_response(json.dumps(response), status=400)
                    return
            
            # Read request body for MCP JSON-RPC
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                raise ValueError("Empty request body")
                
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # Extract headers
            headers_dict = dict(self.headers.items())
            
            # Check if client expects SSE response
            accept_header = self.headers.get('Accept', '')
            is_sse_request = 'text/event-stream' in accept_header
            
            # Handle MCP method calls
            method = request_data.get("method", "")
            request_id = request_data.get("id", "unknown")
            params = request_data.get("params", {})
            
            if method == "tools/list":
                result = handle_list_tools(request_id, params, headers_dict)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            elif method == "tools/call":
                name = params.get("name", "")
                arguments = params.get("arguments", {})
                result = handle_call_tool(name, arguments, headers_dict)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
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
            
            # Send response in appropriate format
            if is_sse_request:
                # Send as SSE
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Connection', 'keep-alive')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                sse_data = json.dumps(response)
                self.wfile.write(f"data: {sse_data}\n\n".encode('utf-8'))
                self.wfile.flush()
            else:
                # Send as regular JSON
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
            
            # Check if SSE response is expected for error too
            accept_header = self.headers.get('Accept', '')
            is_sse_request = 'text/event-stream' in accept_header
            
            if is_sse_request:
                self.send_response(200)  # Still send 200 for SSE, error is in data
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                sse_data = json.dumps(error_response)
                self.wfile.write(f"data: {sse_data}\n\n".encode('utf-8'))
                self.wfile.flush()
            else:
                self._set_response(json.dumps(error_response), status=500)
