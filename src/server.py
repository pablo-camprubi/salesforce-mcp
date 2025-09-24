import asyncio
from typing import Any, Optional, Dict

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

import mcp.server.stdio

import salesforcemcp.sfdc_client as sfdc_client
import salesforcemcp.definitions as sfmcpdef
import salesforcemcp.implementations as sfmcpimpl
    
server = Server("salesforce-mcp")

def create_sf_client(credentials: Optional[Dict[str, str]] = None, encrypted_credentials: Optional[str] = None) -> Optional[sfdc_client.OrgHandler]:
    """Create a Salesforce client with provided credentials or fall back to environment variables.
    
    Args:
        credentials: Dict with username, password, security_token
        encrypted_credentials: Base64 encoded encrypted credentials
        
    Returns:
        OrgHandler instance with established connection or None if failed
    """
    client = sfdc_client.OrgHandler()
    
    try:
        if encrypted_credentials:
            # Use encrypted credentials
            if not client.establish_connection_with_encrypted_credentials(encrypted_credentials):
                print("Failed to establish connection with encrypted credentials")
                return None
        elif credentials:
            # Use provided credentials
            if not client.establish_connection(
                username=credentials.get('username'),
                password=credentials.get('password'),
                security_token=credentials.get('security_token')
            ):
                print("Failed to establish connection with provided credentials")
                return None
        else:
            # Fall back to environment variables
            if not client.establish_connection():
                print("Failed to establish connection with environment variables")
                return None
                
        return client
    except Exception as e:
        print(f"Exception creating Salesforce client: {str(e)}")
        return None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    For multi-user support, we'll return all tools since connection state is per-request.
    """
    all_tools = sfmcpdef.get_tools()
    
    # For multi-user MCP server, we return all tools since each request can have its own credentials
    # Tools that require connection will fail gracefully if no valid credentials are provided
    return all_tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    try:
        # Extract credentials from arguments if provided
        credentials = arguments.pop('_sf_credentials', None) if '_sf_credentials' in arguments else None
        encrypted_credentials = arguments.pop('_sf_encrypted_credentials', None) if '_sf_encrypted_credentials' in arguments else None
        
        # Create Salesforce client for this request
        sf_client = create_sf_client(credentials=credentials, encrypted_credentials=encrypted_credentials)
        
        if not sf_client:
            return [
                types.TextContent(
                    type="text",
                    text=f"Error: Unable to establish Salesforce connection. Please check credentials."
                )
            ]
        
        # Call the appropriate tool implementation with the per-request client
        if name == "create_object":
            return sfmcpimpl.create_object_impl(sf_client, arguments)
        elif name == "create_object_with_fields":
            return sfmcpimpl.create_object_with_fields_impl(sf_client, arguments)
        elif name == "delete_object_fields":
            return sfmcpimpl.delete_object_fields_impl(sf_client, arguments)
        elif name == "create_tab":
            return sfmcpimpl.create_tab_impl(sf_client, arguments)
        elif name == "create_custom_app":
            return sfmcpimpl.create_custom_app_impl(sf_client, arguments)
        elif name == "run_soql_query":
            return sfmcpimpl.run_soql_query_impl(sf_client, arguments)
        elif name == "run_sosl_search":
            return sfmcpimpl.run_sosl_search_impl(sf_client, arguments)
        elif name == "get_object_fields":
            return sfmcpimpl.get_object_fields_impl(sf_client, arguments)
        elif name == "create_record":
            return sfmcpimpl.create_record_impl(sf_client, arguments)
        elif name == "update_record":
            return sfmcpimpl.update_record_impl(sf_client, arguments)
        elif name == "delete_record":
            return sfmcpimpl.delete_record_impl(sf_client, arguments)
        elif name == "create_custom_fields":
            return sfmcpimpl.create_custom_fields_impl(sf_client, arguments)
        elif name == "define_tabs_on_app":
            return sfmcpimpl.define_tabs_on_app_impl(sf_client, arguments)
        elif name == "create_report_folder":
            return sfmcpimpl.create_report_folder_impl(sf_client, arguments)
        elif name == "create_dashboard_folder":
            return sfmcpimpl.create_dashboard_folder_impl(sf_client, arguments)
        elif name == "create_validation_rule":
            return sfmcpimpl.create_validation_rule_impl(sf_client, arguments)
        elif name == "create_custom_metadata_type":
            return sfmcpimpl.create_custom_metadata_type_impl(sf_client, arguments)
        elif name == "create_lightning_page":
            return sfmcpimpl.create_lightning_page_impl(sf_client, arguments)
        elif name == "describe_object":
            return sfmcpimpl.describe_object_impl(sf_client, arguments)
        elif name == "describe_relationship_fields":
            return sfmcpimpl.describe_relationship_fields_impl(sf_client, arguments)
        elif name == "get_fields_by_type":
            return sfmcpimpl.get_fields_by_type_impl(sf_client, arguments)
        elif name == "get_picklist_values":
            return sfmcpimpl.get_picklist_values_impl(sf_client, arguments)
        elif name == "get_validation_rules":
            return sfmcpimpl.get_validation_rules_impl(sf_client, arguments)
        elif name == "create_einstein_model":
            return sfmcpimpl.create_einstein_model_impl(sf_client, arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
    except Exception as e:
        print(f"Error executing tool '{name}': {str(e)}")
        print(f"Arguments: {arguments}")
        return [
            types.TextContent(
                type="text",
                text=f"Error executing '{name}': {str(e)}"
            )
        ]

async def run():
    async with mcp.server.stdio.stdio_server() as (read, write):
        await server.run(
            read,
            write,
            InitializationOptions(
                server_name="salesforce-mcp",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run())
