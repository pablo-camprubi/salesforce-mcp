import json
import sys
import os
from typing import Any, Dict, List
from http.server import BaseHTTPRequestHandler

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    import salesforcemcp.sfdc_client as sfdc_client
    import salesforcemcp.definitions as sfmcpdef
    import salesforcemcp.implementations as sfmcpimpl
    import mcp.types as types
except ImportError as e:
    print(f"Import error: {e}")
    # For development/testing when modules might not be available
    sfdc_client = None
    sfmcpdef = None
    sfmcpimpl = None
    types = None

# Salesforce client will be initialized per request
def get_sf_client():
    """Get a fresh Salesforce client connection"""
    if not sfdc_client:
        print("ERROR: sfdc_client module not available")
        raise ValueError("Salesforce client module not initialized")
    
    import os
    # Debug environment variables - use working variable names
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD") 
    security_token = os.getenv("SECURITY_TOKEN")
    
    # Enhanced debugging
    print(f"=== Salesforce Connection Debug ===")
    print(f"Environment check - USERNAME: {'SET' if username else 'MISSING'}")
    print(f"Environment check - PASSWORD: {'SET' if password else 'MISSING'}")  
    print(f"Environment check - SECURITY_TOKEN: {'SET' if security_token else 'EMPTY (trusted IP)'}")
    
    if not username:
        raise ValueError("USERNAME environment variable is required but not set")
    if not password:
        raise ValueError("PASSWORD environment variable is required but not set")
    
    # SECURITY_TOKEN can be empty for trusted IP ranges
    if security_token is None:
        security_token = ""
        print("  SECURITY_TOKEN not set, using empty string (for trusted IP ranges)")
    elif security_token == "":
        print("  SECURITY_TOKEN is empty (for trusted IP ranges)")
    
    try:
        print("Creating OrgHandler...")
        client = sfdc_client.OrgHandler()
        print("OrgHandler created, attempting connection...")
        
        connection_result = client.establish_connection()
        if connection_result:
            print("✅ Salesforce connection established successfully")
            print(f"Session ID: {client.connection.session_id[:10]}...")
            print(f"Instance: {client.connection.sf_instance}")
            return client
        else:
            print("❌ Failed to establish Salesforce connection - establish_connection returned False")
            raise ValueError("Salesforce authentication failed - check credentials")
            
    except Exception as e:
        print(f"❌ Exception creating Salesforce client: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise ValueError(f"Salesforce connection failed: {str(e)}")

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

def handle_health_check(request_id: Any, params: Dict[str, Any]):
    """Handle health check - useful for debugging server state"""
    import os
    
    health_data = {
        "status": "checking",
        "timestamp": str(__import__('datetime').datetime.now()),
        "environment_variables": {
            "USERNAME": "SET" if os.getenv("USERNAME") else "MISSING",
            "PASSWORD": "SET" if os.getenv("PASSWORD") else "MISSING", 
            "SECURITY_TOKEN": "SET" if os.getenv("SECURITY_TOKEN") else "EMPTY (trusted IP)"
        },
        "modules": {
            "sfdc_client": sfdc_client is not None,
            "sfmcpdef": sfmcpdef is not None,
            "sfmcpimpl": sfmcpimpl is not None,
            "types": types is not None
        }
    }
    
    # Try Salesforce connection
    try:
        client = get_sf_client()
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

def handle_list_tools(request_id: Any, params: Dict[str, Any]):
    """Handle the tools/list method"""
    if not sfmcpdef:
        return send_error(-32603, "Server not properly initialized", request_id)
        
    try:
        all_tools = sfmcpdef.get_tools()
        client = get_sf_client()
        is_connected = client and client.metadata_cache is not None
        
        if is_connected:
            tools = all_tools
        else:
            print("Salesforce connection inactive. Filtering available tools.")
            live_connection_tools = {
                "create_record", "delete_object_fields", "create_tab", "create_custom_app", "create_object_with_fields",
                "create_custom_fields", "define_tabs_on_app", "create_report_folder", "create_dashboard_folder",
                "create_validation_rule", "create_custom_metadata_type", "create_lightning_page", "describe_object",
                "describe_relationship_fields", "get_fields_by_type", "get_picklist_values", "get_validation_rules"
            }
            tools = [tool for tool in all_tools if tool.name not in live_connection_tools]
        
        # Convert tools to dictionary format
        tools_dict = []
        for tool in tools:
            tools_dict.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            })
        
        result = {"tools": tools_dict}
        return send_json_rpc_response(request_id, result)
        
    except Exception as e:
        return send_error(-32603, "Error listing tools", request_id, str(e))

def handle_call_tool(request_id: Any, params: Dict[str, Any]):
    """Handle the tools/call method"""
    if not sfmcpimpl:
        return send_error(-32603, "Server not properly initialized", request_id)
        
    try:
        name = params.get('name')
        arguments = params.get('arguments', {})
        
        if not name:
            return send_error(-32602, "Invalid params", request_id)
        
        # Get a fresh Salesforce client for this request
        client = get_sf_client()
        
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
        return send_error(-32602, "Invalid params", request_id, str(e))
    except Exception as e:
        return send_error(-32603, "Internal server error", request_id, str(e))

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
            
            # Handle different methods
            if method == 'initialize':
                response = handle_initialize(request_id, params)
            elif method == 'tools/list':
                response = handle_list_tools(request_id, params)
            elif method == 'tools/call':
                response = handle_call_tool(request_id, params)
            elif method == 'health/check':
                response = handle_health_check(request_id, params)
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
                health_result = handle_health_check("health-check", {})
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