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

def serialize_response(obj):
    """Convert TextContent objects and other non-serializable objects to JSON-serializable format"""
    if hasattr(obj, 'type') and hasattr(obj, 'text'):
        # Handle individual TextContent objects
        return {"type": obj.type, "text": obj.text}
    elif isinstance(obj, list):
        # Handle arrays of TextContent objects (most common case from implementations)
        serialized_items = []
        for item in obj:
            if hasattr(item, 'type') and hasattr(item, 'text'):
                # TextContent object in list
                serialized_items.append({"type": item.type, "text": item.text})
            else:
                # Other objects
                serialized_items.append(str(item))
        return serialized_items
    elif isinstance(obj, dict):
        if "content" in obj and isinstance(obj["content"], list):
            # Handle tool call response with content array
            return {
                **obj,
                "content": [serialize_response(item) for item in obj["content"]]
            }
        else:
            return {key: serialize_response(value) for key, value in obj.items()}
    elif isinstance(obj, str):
        return obj
    else:
        return str(obj)

def get_sf_client(credentials: Optional[Dict[str, str]] = None, encrypted_credentials: Optional[str] = None, request_headers: Optional[Dict[str, str]] = None):
    """Get a fresh Salesforce client connection with provided or inferred credentials."""
    if not sfdc_client:
        return None
    
    client = sfdc_client.OrgHandler()
    
    try:
        # Add timeout protection for all connection attempts  
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError("Salesforce connection timeout")
            
        # Set 15-second timeout for entire connection process
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(15)
        
        # Priority order: encrypted_credentials, credentials, headers, environment variables
        if encrypted_credentials:
            if not client.establish_connection_with_encrypted_credentials(encrypted_credentials):
                signal.alarm(0)  # Cancel timeout
                return None
        elif credentials:
            if not client.establish_connection(
                username=credentials.get('username'),
                password=credentials.get('password'),
                security_token=credentials.get('security_token')
            ):
                signal.alarm(0)  # Cancel timeout
                return None
        elif request_headers:
            sf_encrypted_header = request_headers.get('X-Salesforce-Encrypted-Credentials', '')
            sf_credentials_header = request_headers.get('X-Salesforce-Credentials', '')
            
            if sf_encrypted_header:
                if not client.establish_connection_with_encrypted_credentials(sf_encrypted_header):
                    signal.alarm(0)  # Cancel timeout
                    return None
            elif sf_credentials_header:
                try:
                    creds = json.loads(sf_credentials_header)
                    if not client.establish_connection(
                        username=creds.get('username'),
                        password=creds.get('password'),
                        security_token=creds.get('security_token')
                    ):
                        signal.alarm(0)  # Cancel timeout
                        return None
                except json.JSONDecodeError:
                    signal.alarm(0)  # Cancel timeout
                    return None
            else:
                # Use environment variables
                if not client.establish_connection():
                    signal.alarm(0)  # Cancel timeout
                    return None
        else:
            # Use environment variables as fallback
            if not client.establish_connection():
                signal.alarm(0)  # Cancel timeout
                return None
                
        signal.alarm(0)  # Cancel timeout on success
        return client
        
    except TimeoutError as e:
        signal.alarm(0)  # Cancel timeout
        print(f"Salesforce connection timeout: {e}")
        return None
    except Exception as e:
        signal.alarm(0)  # Cancel timeout
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
            # Handle save-credentials endpoint (multiple paths for compatibility)
            if self.path in ['/save-credentials', '/api/salesforce/save-credentials']:
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
            # Handle save-credentials endpoint (multiple paths for compatibility)
            if self.path in ['/save-credentials', '/api/salesforce/save-credentials']:
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    print(f"[DEBUG] Save credentials request - Content-Length: {content_length}")
                    print(f"[DEBUG] Headers: {dict(self.headers.items())}")
                    
                    if content_length > 0:
                        post_data = self.rfile.read(content_length)
                        print(f"[DEBUG] Raw request data: {post_data}")
                        
                        try:
                            credential_data = json.loads(post_data.decode('utf-8'))
                            print(f"[DEBUG] Parsed credentials: {list(credential_data.keys())}")
                            
                            # Always return success for debugging - don't test actual SF connection
                            response = {
                                "status": "success",
                                "message": "Credentials received successfully",
                                "connection_test": "skipped_for_debug",
                                "debug_info": {
                                    "has_credentials": "credentials" in credential_data,
                                    "has_encrypted_credentials": "encrypted_credentials" in credential_data,
                                    "request_size": len(post_data),
                                    "path": self.path
                                }
                            }
                            
                            self._set_response(json.dumps(response, indent=2))
                            return
                            
                        except json.JSONDecodeError as e:
                            print(f"[DEBUG] JSON decode error: {e}")
                            error_response = {
                                "status": "error",
                                "message": f"Invalid JSON in request body: {str(e)}",
                                "raw_data": post_data.decode('utf-8', errors='replace')[:200]
                            }
                            self._set_response(json.dumps(error_response), status=200)  # Return 200 for debugging
                            return
                    else:
                        print("[DEBUG] No request body provided")
                        response = {
                            "status": "success",
                            "message": "Empty request body received (GET request?)",
                            "debug_info": {
                                "method": "POST",
                                "path": self.path,
                                "content_length": content_length
                            }
                        }
                        self._set_response(json.dumps(response), status=200)
                        return
                        
                except Exception as e:
                    print(f"[DEBUG] Exception in save-credentials: {e}")
                    error_response = {
                        "status": "error",
                        "message": f"Server error: {str(e)}",
                        "debug_info": {
                            "exception_type": str(type(e).__name__),
                            "path": self.path
                        }
                    }
                    self._set_response(json.dumps(error_response), status=200)  # Return 200 for debugging
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
                # Convert TextContent objects to JSON-serializable format
                serialized_result = serialize_response(result)
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": serialized_result
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
