import json
import sys
import os
from typing import Any, Dict, List, Optional
from http.server import BaseHTTPRequestHandler

# Import handling with local modules for serverless environment
try:
    # Try local import first (for serverless)
    from . import salesforcemcp.sfdc_client as sfdc_client
    from . import salesforcemcp.definitions as sfmcpdef
    from . import salesforcemcp.implementations as sfmcpimpl
    print("Successfully imported Salesforce MCP modules (local)")
except ImportError:
    try:
        # Fallback to src path import (for local dev)
        current_dir = os.path.dirname(__file__)
        src_path = os.path.join(current_dir, '..', 'src')
        sys.path.insert(0, src_path)
        import salesforcemcp.sfdc_client as sfdc_client
        import salesforcemcp.definitions as sfmcpdef
        import salesforcemcp.implementations as sfmcpimpl
        print("Successfully imported Salesforce MCP modules (src)")
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

class Tool:
    def __init__(self, name: str, description: str, inputSchema: dict):
        self.name = name
        self.description = description
        self.inputSchema = inputSchema

class types:
    TextContent = TextContent
    Tool = Tool

def get_sf_client(credentials: Optional[Dict[str, str]] = None, encrypted_credentials: Optional[str] = None, request_headers: Optional[Dict[str, str]] = None):
    """Get a fresh Salesforce client connection with provided or inferred credentials.
    
    Args:
        credentials: Dict with username, password, security_token
        encrypted_credentials: Base64 encoded encrypted credentials  
        request_headers: HTTP headers that might contain credentials
        
    Returns:
        OrgHandler instance with established connection or None if failed
    """
    if not sfdc_client:
        print("ERROR: sfdc_client module not available")
        raise ValueError("Salesforce client module not initialized")
    
    client = sfdc_client.OrgHandler()
    
    try:
        # Priority order: encrypted_credentials, credentials, headers, environment variables
        if encrypted_credentials:
            print("🔐 Using encrypted credentials from request")
            if not client.establish_connection_with_encrypted_credentials(encrypted_credentials):
                print("❌ Failed to establish connection with encrypted credentials")
                return None
                
        elif credentials:
            print("🔑 Using plain credentials from request")
            if not client.establish_connection(
                username=credentials.get('username'),
                password=credentials.get('password'),
                security_token=credentials.get('security_token')
            ):
                print("❌ Failed to establish connection with provided credentials")
                return None
                
        elif request_headers:
            # Check for credentials in headers (for platform integration)
            auth_header = request_headers.get('Authorization', '')
            sf_credentials_header = request_headers.get('X-Salesforce-Credentials', '')
            sf_encrypted_header = request_headers.get('X-Salesforce-Encrypted-Credentials', '')
            
            if sf_encrypted_header:
                print("🔐 Using encrypted credentials from X-Salesforce-Encrypted-Credentials header")
                if not client.establish_connection_with_encrypted_credentials(sf_encrypted_header):
                    print("❌ Failed to establish connection with encrypted credentials from header")
                    return None
            elif sf_credentials_header:
                print("🔑 Using credentials from X-Salesforce-Credentials header")
                try:
                    header_credentials = json.loads(sf_credentials_header)
                    if not client.establish_connection(
                        username=header_credentials.get('username'),
                        password=header_credentials.get('password'),
                        security_token=header_credentials.get('security_token')
                    ):
                        print("❌ Failed to establish connection with credentials from header")
                        return None
                except json.JSONDecodeError as e:
                    print(f"❌ Invalid JSON in X-Salesforce-Credentials header: {e}")
                    return None
            else:
                # Fall back to environment variables
                print("🌍 Falling back to environment variables")
                import os
                username = os.getenv("USERNAME")
                password = os.getenv("PASSWORD") 
                security_token = os.getenv("SECURITY_TOKEN", "")
                
                print(f"Environment check - USERNAME: {'SET' if username else 'MISSING'}")
                print(f"Environment check - PASSWORD: {'SET' if password else 'MISSING'}")  
                print(f"Environment check - SECURITY_TOKEN: {'SET' if security_token else 'EMPTY (trusted IP)'}")
                
                if not client.establish_connection():
                    print("❌ Failed to establish connection with environment variables")
                    return None
        else:
            # Fall back to environment variables
            print("🌍 Using environment variables (no credentials provided)")
            if not client.establish_connection():
                print("❌ Failed to establish connection with environment variables")
                return None
                
        print("✅ Salesforce connection established successfully")
        if client.connection:
            print(f"Session ID: {client.connection.session_id[:10]}...")
            print(f"Instance: {client.connection.sf_instance}")
        return client
        
    except Exception as e:
        print(f"❌ Exception creating Salesforce client: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def send_json_rpc_response(request_id: Any, result: Any = None, error: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a JSON-RPC 2.0 response"""
    response = {
        "jsonrpc": "2.0",
        "id": request_id
    }
    
    if error:
        response["error"] = error
    else:
        response["result"] = result
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(response)
    }

def send_error(code: int, message: str, request_id: Any, data: str = None):
    """Send a JSON-RPC error response"""
    error = {
        "code": code,
        "message": message
    }
    if data:
        error["data"] = data
    
    return send_json_rpc_response(request_id, error=error)

def handle_initialize(request_id: Any, params: Dict[str, Any]):
    """Handle the initialize method"""
    result = {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "salesforce-mcp-vercel",
            "version": "1.0.0"
        }
    }
    return send_json_rpc_response(request_id, result)

def handle_health_check(request_id: Any, params: Dict[str, Any], request_headers: Optional[Dict[str, str]] = None):
    """Handle health check - useful for debugging server state"""
    import os
    
    health_data = {
        "status": "checking",
        "timestamp": str(__import__('datetime').datetime.now()),
        "environment_variables": {
            "USERNAME": "SET" if os.getenv("USERNAME") else "MISSING",
            "PASSWORD": "SET" if os.getenv("PASSWORD") else "MISSING", 
            "SECURITY_TOKEN": "SET" if os.getenv("SECURITY_TOKEN") else "EMPTY (trusted IP)",
            "ENCRYPTION_KEY": "SET" if os.getenv("ENCRYPTION_KEY") else "MISSING"
        },
        "modules": {
            "sfdc_client": sfdc_client is not None,
            "sfmcpdef": sfmcpdef is not None,
            "sfmcpimpl": sfmcpimpl is not None,
            "types": types is not None
        },
        "multi_user_support": {
            "enabled": True,
            "credential_sources": ["encrypted_credentials", "plain_credentials", "headers", "environment"]
        }
    }
    
    # Try Salesforce connection with available credentials
    try:
        # Check for credentials in params (for testing)
        credentials = params.get('credentials')
        encrypted_credentials = params.get('encrypted_credentials')
        
        client = get_sf_client(
            credentials=credentials,
            encrypted_credentials=encrypted_credentials, 
            request_headers=request_headers
        )
        if client and client.connection:
            health_data["salesforce_connection"] = {
                "status": "connected",
                "instance": client.connection.sf_instance,
                "session_id": client.connection.session_id[:10] + "..." if client.connection.session_id else "none"
            }
        else:
            health_data["salesforce_connection"] = {"status": "failed", "error": "No client returned"}
        health_data["status"] = "healthy"
    except Exception as e:
        health_data["salesforce_connection"] = {"status": "error", "error": str(e)}
        health_data["status"] = "unhealthy"
    
    return send_json_rpc_response(request_id, health_data)

def handle_list_tools(request_id: Any, params: Dict[str, Any], request_headers: Optional[Dict[str, str]] = None):
    """Handle the tools/list method"""
    if not sfmcpdef:
        return send_error(-32603, "Server not properly initialized", request_id)
        
    try:
        all_tools = sfmcpdef.get_tools()
        
        # For multi-user MCP server, return all tools since each request can have its own credentials
        # Tools that require connection will fail gracefully if no valid credentials are provided
        tools_dict = []
        for tool in all_tools:
            tools_dict.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        
        result = {"tools": tools_dict}
        return send_json_rpc_response(request_id, result)
        
    except Exception as e:
        return send_error(-32603, "Error listing tools", request_id, str(e))

def handle_call_tool(request_id: Any, params: Dict[str, Any], request_headers: Optional[Dict[str, str]] = None):
    """Handle the tools/call method"""
    if not sfmcpimpl:
        return send_error(-32603, "Server not properly initialized", request_id)
        
    try:
        name = params.get('name')
        arguments = params.get('arguments', {}).copy()  # Copy to avoid modifying original
        
        if not name:
            return send_error(-32602, "Invalid params", request_id)
        
        # Extract credentials from arguments or params if provided
        credentials = arguments.pop('_sf_credentials', None) or params.get('credentials')
        encrypted_credentials = arguments.pop('_sf_encrypted_credentials', None) or params.get('encrypted_credentials')
        
        # Get a fresh Salesforce client for this request with appropriate credentials
        client = get_sf_client(
            credentials=credentials,
            encrypted_credentials=encrypted_credentials,
            request_headers=request_headers
        )
        
        if not client:
            return send_error(-32603, "Unable to establish Salesforce connection. Please check credentials.", request_id)
        
        # Call the appropriate tool implementation
        if name == "create_object":
            result = sfmcpimpl.create_object_impl(client, arguments)
        elif name == "create_object_with_fields":
            result = sfmcpimpl.create_object_with_fields_impl(client, arguments)
        elif name == "delete_object_fields":
            result = sfmcpimpl.delete_object_fields_impl(client, arguments)
        elif name == "create_tab":
            result = sfmcpimpl.create_tab_impl(client, arguments)
        elif name == "create_custom_app":
            result = sfmcpimpl.create_custom_app_impl(client, arguments)
        elif name == "run_soql_query":
            result = sfmcpimpl.run_soql_query_impl(client, arguments)
        elif name == "run_sosl_search":
            result = sfmcpimpl.run_sosl_search_impl(client, arguments)
        elif name == "get_object_fields":
            result = sfmcpimpl.get_object_fields_impl(client, arguments)
        elif name == "create_record":
            result = sfmcpimpl.create_record_impl(client, arguments)
        elif name == "update_record":
            result = sfmcpimpl.update_record_impl(client, arguments)
        elif name == "delete_record":
            result = sfmcpimpl.delete_record_impl(client, arguments)
        elif name == "create_custom_fields":
            result = sfmcpimpl.create_custom_fields_impl(client, arguments)
        elif name == "define_tabs_on_app":
            result = sfmcpimpl.define_tabs_on_app_impl(client, arguments)
        elif name == "create_report_folder":
            result = sfmcpimpl.create_report_folder_impl(client, arguments)
        elif name == "create_dashboard_folder":
            result = sfmcpimpl.create_dashboard_folder_impl(client, arguments)
        elif name == "create_validation_rule":
            result = sfmcpimpl.create_validation_rule_impl(client, arguments)
        elif name == "create_custom_metadata_type":
            result = sfmcpimpl.create_custom_metadata_type_impl(client, arguments)
        elif name == "create_lightning_page":
            result = sfmcpimpl.create_lightning_page_impl(client, arguments)
        elif name == "describe_object":
            result = sfmcpimpl.describe_object_impl(client, arguments)
        elif name == "describe_relationship_fields":
            result = sfmcpimpl.describe_relationship_fields_impl(client, arguments)
        elif name == "get_fields_by_type":
            result = sfmcpimpl.get_fields_by_type_impl(client, arguments)
        elif name == "get_picklist_values":
            result = sfmcpimpl.get_picklist_values_impl(client, arguments)
        elif name == "get_validation_rules":
            result = sfmcpimpl.get_validation_rules_impl(client, arguments)
        elif name == "create_einstein_model":
            result = sfmcpimpl.create_einstein_model_impl(client, arguments)
        else:
            return send_error(-32601, f"Unknown tool: {name}", request_id)
        
        # Convert TextContent objects to dictionaries
        content_list = []
        for item in result:
            if hasattr(item, 'type') and hasattr(item, 'text'):
                content_list.append({
                    "type": item.type,
                    "text": item.text
                })
            else:
                content_list.append(item)
        
        response_result = {"content": content_list}
        return send_json_rpc_response(request_id, response_result)
        
    except ValueError as e:
        print(f"❌ ValueError in handle_call_tool: {str(e)}")
        return send_error(-32602, f"Invalid params: {str(e)}", request_id, str(e))
    except Exception as e:
        print(f"❌ Exception in handle_call_tool: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return send_error(-32603, f"Internal server error: {str(e)}", request_id, str(e))

class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler compatible with Python runtime"""
    
    def do_POST(self):
        try:
            # Read the request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
            else:
                post_data = b'{}'
            
            # Parse JSON-RPC request
            try:
                request_data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                response = send_error(-32700, "Parse error", None)
                self._send_vercel_response(response)
                return
            
            # Validate JSON-RPC format
            if not isinstance(request_data, dict) or request_data.get('jsonrpc') != '2.0':
                response = send_error(-32600, "Invalid Request", request_data.get('id'))
                self._send_vercel_response(response)
                return
            
            method = request_data.get('method')
            request_id = request_data.get('id')
            params = request_data.get('params', {})
            
            if not method:
                response = send_error(-32600, "Invalid Request", request_id)
                self._send_vercel_response(response)
                return
            
            # Extract headers for credential handling
            headers_dict = {key: value for key, value in self.headers.items()}
            
            # Handle different methods
            if method == 'initialize':
                response = handle_initialize(request_id, params)
            elif method == 'tools/list':
                response = handle_list_tools(request_id, params, headers_dict)
            elif method == 'tools/call':
                response = handle_call_tool(request_id, params, headers_dict)
            elif method == 'health/check':
                response = handle_health_check(request_id, params, headers_dict)
            else:
                response = send_error(-32601, "Method not found", request_id)
            
            self._send_vercel_response(response)
                
        except Exception as e:
            print(f"Error handling request: {e}")
            response = send_error(-32603, "Internal server error", None, str(e))
            self._send_vercel_response(response)
    
    def do_GET(self):
        """Handle GET requests for health checks"""
        try:
            if self.path == '/health' or self.path == '/':
                # Simple health check via GET
                headers_dict = {key: value for key, value in self.headers.items()}
                health_result = handle_health_check("health-check", {}, headers_dict)
                response = {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': health_result['body']
                }
                self._send_vercel_response(response)
            else:
                # Not found
                response = {
                    'statusCode': 404,
                    'headers': {'Content-Type': 'text/plain'},
                    'body': 'Not Found'
                }
                self._send_vercel_response(response)
        except Exception as e:
            response = {
                'statusCode': 500,
                'headers': {'Content-Type': 'text/plain'},
                'body': f'Health check error: {str(e)}'
            }
            self._send_vercel_response(response)

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        response = {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            },
            'body': ''
        }
        self._send_vercel_response(response)
    
    def _send_vercel_response(self, response):
        """Send response in Vercel format"""
        self.send_response(response.get('statusCode', 200))
        
        headers = response.get('headers', {})
        for key, value in headers.items():
            self.send_header(key, value)
        
        self.end_headers()
        
        body = response.get('body', '')
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.wfile.write(body)

# For local testing
if __name__ == '__main__':
    # Simple test
    import http.server
    import socketserver
    
    PORT = 8000
    
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"MCP Server running on http://localhost:{PORT}")
        httpd.serve_forever()