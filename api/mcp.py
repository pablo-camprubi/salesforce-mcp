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
        print("sfdc_client module not available")
        return None
    
    import os
    # Debug environment variables - use working variable names
    username = os.getenv("USERNAME")
    password = os.getenv("PASSWORD") 
    security_token = os.getenv("SECURITY_TOKEN")
    
    print(f"Environment check - USERNAME: {'SET' if username else 'MISSING'}")
    print(f"Environment check - PASSWORD: {'SET' if password else 'MISSING'}")  
    print(f"Environment check - SECURITY_TOKEN: {'SET' if security_token else 'MISSING'}")
    
    if not all([username, password, security_token]):
        print("Missing required Salesforce credentials in environment variables")
        return None
    
    try:
        client = sfdc_client.OrgHandler()
        print("OrgHandler created, attempting connection...")
        if client.establish_connection():
            print("Salesforce connection established successfully")
            return client
        else:
            print("Failed to establish Salesforce connection - establish_connection returned False")
            return None
    except Exception as e:
        print(f"Exception creating Salesforce client: {str(e)}")
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
                "create_record", "delete_object_fields", "create_tab", "create_custom_app"
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
            else:
                response = send_error(-32601, "Method not found", request_id)
            
            self._send_vercel_response(response)
                
        except Exception as e:
            print(f"Error handling request: {e}")
            response = send_error(-32603, "Internal server error", None, str(e))
            self._send_vercel_response(response)
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        response = {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'POST, OPTIONS',
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