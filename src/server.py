import asyncio
from typing import Any

import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions

import mcp.server.stdio

import salesforcemcp.sfdc_client as sfdc_client
import salesforcemcp.definitions as sfmcpdef
import salesforcemcp.implementations as sfmcpimpl
    
server = Server("salesforce-mcp")

sf_client = sfdc_client.OrgHandler()
if not sf_client.establish_connection():
    print("Failed to initialize Salesforce connection")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Dynamically excludes tools requiring a live connection if sf_client is not connected.
    """

    all_tools = sfmcpdef.get_tools()
    is_connected = sf_client.metadata_cache is not None

    if is_connected:
        return all_tools
    else:
        print("Salesforce connection inactive. Filtering available tools.")
        live_connection_tools = {
            "create_record", "delete_object_fields", "create_tab", "create_custom_app", "create_object_with_fields",
            "create_custom_fields", "define_tabs_on_app", "create_report_folder", "create_dashboard_folder",
            "create_validation_rule", "create_custom_metadata_type", "create_lightning_page", "describe_object",
            "describe_relationship_fields", "get_fields_by_type", "get_picklist_values", "get_validation_rules"
        }
        available_tools = [tool for tool in all_tools if tool.name not in live_connection_tools]
        return available_tools

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
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
    else:
        raise ValueError(f"Unknown tool: {name}")

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
