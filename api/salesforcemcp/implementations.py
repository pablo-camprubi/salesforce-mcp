from . import sfdc_client
from .sfdc_client import OrgHandler
from . import metadata_service

# Use local types instead of mcp library for serverless compatibility
class TextContent:
    def __init__(self, type: str, text: str):
        self.type = type
        self.text = text

class types:
    TextContent = TextContent
import json
from simple_salesforce import SalesforceError
from typing import Any, Optional
import re
import os
import shutil

def create_object_impl(sf_client: sfdc_client.OrgHandler, arguments: dict[str, Any]):
    name = arguments.get("name")
    plural_name = arguments.get("plural_name")
    api_name = arguments.get("api_name")
    description = arguments.get("description")
    fields = arguments.get("fields")

    json_obj = {}
    json_obj["name"] = name
    json_obj["plural_name"] = plural_name
    json_obj["api_name"] = api_name
    json_obj["description"] = description
    json_obj["fields"] = fields

    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot perform metadata deployment.")
    
    try:
        metadata_service.write_to_file(json.dumps(json_obj))
        metadata_service.create_metadata_package(json_obj)
        metadata_service.deploy_object_package(sf_client.connection)

        return [
            types.TextContent(
                type="text",
                text=f"Custom Object '{api_name}' creation package prepared and deployment initiated."
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error creating custom object '{api_name}': {str(e)}"
            )
        ]

def create_object_with_fields_impl(sf_client: sfdc_client.OrgHandler, arguments: dict[str, Any]):
    name = arguments.get("name")
    plural_name = arguments.get("plural_name")
    api_name = arguments.get("api_name")
    description = arguments.get("description")
    fields = arguments.get("fields")

    json_obj = {}
    json_obj["name"] = name
    json_obj["plural_name"] = plural_name
    json_obj["api_name"] = api_name
    json_obj["description"] = description
    json_obj["fields"] = fields

    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot perform metadata deployment.")
    
    try:
        metadata_service.write_to_file(json.dumps(json_obj))
        metadata_service.create_metadata_package(json_obj)
        metadata_service.deploy_object_package(sf_client.connection)

        return [
            types.TextContent(
                type="text",
                text=f"Custom Object '{api_name}' with enhanced fields creation package prepared and deployment initiated."
            )
        ]
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error creating custom object '{api_name}': {str(e)}"
            )
        ]

def delete_object_fields_impl(sf_client: sfdc_client.OrgHandler, arguments: dict[str, Any]):
    api_name = arguments.get("api_name")
    fields = arguments.get("fields")

    json_obj = {}
    json_obj["api_name"] = api_name
    json_obj["fields"] = fields

    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot perform metadata deployment.")
    metadata_service.delete_fields(json_obj)
    metadata_service.delete_send_to_server(sf_client.connection)

    return [
        types.TextContent(
            type="text",
            text=f"Delete Object fields on '{api_name}' creation package prepared and deployment initiated."
        )
    ]

def create_tab_impl(sf_client: sfdc_client.OrgHandler, arguments: dict[str, Any]):
    args = arguments
    tab_api_name = args.get("tab_api_name")
    label = args.get("label")
    motif = args.get("motif")
    tab_type = args.get("tab_type")
    object_name = args.get("object_name")
    vf_page_name = args.get("vf_page_name")
    web_url = args.get("web_url")
    url_encoding_key = args.get("url_encoding_key", "UTF8")
    description = args.get("description")

    if not all([tab_api_name, label, motif, tab_type]):
        raise ValueError("Missing required arguments: tab_api_name, label, motif, tab_type")

    valid_types = ['CustomObject', 'VisualforcePage', 'Web']
    if tab_type not in valid_types:
        raise ValueError(f"Invalid tab_type: '{tab_type}'. Must be one of {valid_types}")
    if tab_type == 'CustomObject' and not object_name:
         raise ValueError("object_name is required when tab_type is 'CustomObject'")
    if tab_type == 'CustomObject' and tab_api_name != object_name:
         # This validation is also in sfdc_client, but good to have early check
         raise ValueError("For CustomObject tabs, tab_api_name must match object_name")
    if tab_type == 'VisualforcePage' and not vf_page_name:
        raise ValueError("vf_page_name is required when tab_type is 'VisualforcePage'")
    if tab_type == 'Web' and not web_url:
        raise ValueError("web_url is required when tab_type is 'Web'")
        
    json_obj = {
        "tab_api_name": tab_api_name,
        "label": label,
        "motif": motif,
        "tab_type": tab_type,
        "object_name": object_name, # Will be None if not provided
        "vf_page_name": vf_page_name,
        "web_url": web_url,
        "url_encoding_key": url_encoding_key,
        "description": description
    }

    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot perform metadata deployment.")

    try:
        metadata_service.create_tab_package(json_obj)
        metadata_service.deploy_tab_package(sf_client.connection)
        return [
            types.TextContent(
                type="text",
                text=f"Custom Tab '{tab_api_name}' creation package prepared and deployment initiated."
            )
        ]
    except Exception as e:
        print(f"Error during Custom Tab creation/deployment: {e}")
        raise ValueError(f"Failed to create or deploy Custom Tab '{tab_api_name}'. Error: {str(e)}")

def create_custom_app_impl(sf_client: sfdc_client.OrgHandler, arguments: dict[str, Any]):
        api_name = arguments.get("api_name")
        label = arguments.get("label")
        nav_type = arguments.get("nav_type", "Standard")
        tabs = arguments.get("tabs")
        description = arguments.get("description")
        header_color = arguments.get("header_color")
        form_factors = arguments.get("form_factors", ["Small", "Large"])
        setup_experience = arguments.get("setup_experience", "all")

        if not all([api_name, label, isinstance(tabs, list)]):
             raise ValueError("Missing required arguments: api_name, label, tabs (must be a list)")
        if not api_name.replace("_", "").isalnum() or " " in api_name:
             raise ValueError(f"Invalid api_name: '{api_name}'. Use only letters, numbers, and underscores.")
             
        json_obj = {
            "api_name": api_name,
            "label": label,
            "nav_type": nav_type,
            "tabs": tabs,
            "description": description,
            "header_color": header_color,
            "form_factors": form_factors,
            "setup_experience": setup_experience
        }

        if not sf_client.connection:
            raise ValueError("Salesforce connection is not active. Cannot perform metadata deployment.")

        try:
            metadata_service.create_custom_app_package(json_obj)
            metadata_service.create_send_to_server(sf_client.connection)
            return [
                types.TextContent(
                    type="text",
                    text=f"Custom Application '{api_name}' creation package prepared and deployment initiated."
                )
            ]
        except Exception as e:
            print(f"Error during Custom Application creation/deployment: {e}")
            raise ValueError(f"Failed to create or deploy Custom Application '{api_name}'. Error: {str(e)}")

# --- Data Operations ---

def run_soql_query_impl(sf_client: OrgHandler, arguments: dict[str, str]):
    import json, base64  # Import at function level to fix scope issue
    
    query = arguments.get("query")
    _sf_encrypted_credentials = arguments.get("_sf_encrypted_credentials")
    
    print(f"🔍 [SERVER DEBUG] run_soql_query_impl called")
    print(f"🔍 [SERVER DEBUG] Query: {query}")
    print(f"🔍 [SERVER DEBUG] Has encrypted credentials: {bool(_sf_encrypted_credentials)}")
    
    if _sf_encrypted_credentials:
        
        print(f"🔍 [SERVER DEBUG] Received encrypted credentials length: {len(_sf_encrypted_credentials)}")
        
        try:
            # Decode credentials
            decoded_bytes = base64.b64decode(_sf_encrypted_credentials)
            decoded_str = decoded_bytes.decode('utf-8')
            credentials = json.loads(decoded_str)
            
            print(f"✅ [SERVER DEBUG] Successfully decoded credentials")
            print(f"🔍 [SERVER DEBUG] Username: {credentials.get('username')}")
            print(f"🔍 [SERVER DEBUG] Password length: {len(credentials.get('password', ''))}")
            print(f"🔍 [SERVER DEBUG] Security token: '{credentials.get('securityToken', 'EMPTY')}'")
            print(f"🔍 [SERVER DEBUG] Instance URL: {credentials.get('instanceUrl')}")
            
            # Test Salesforce connection
            from simple_salesforce import Salesforce
            try:
                print(f"🔄 [SERVER DEBUG] Attempting direct Salesforce connection...")
                sf = Salesforce(
                    username=credentials['username'],
                    password=credentials['password'],
                    security_token=credentials.get('securityToken', ''),
                    domain='login'
                )
                print(f"✅ [SERVER DEBUG] Direct Salesforce connection successful!")
                print(f"✅ [SERVER DEBUG] Session ID: {sf.session_id[:20]}...")
                
                # Test query with direct connection
                print(f"🔄 [SERVER DEBUG] Testing query with direct connection...")
                results = sf.query_all(query)
                print(f"✅ [SERVER DEBUG] Direct query successful! {len(results.get('records', []))} records")
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"DIRECT CONNECTION SUCCESS - SOQL Query Results (JSON):\\n{json.dumps(results, indent=2)}"
                    )
                ]
                
            except Exception as sf_error:
                print(f"❌ [SERVER DEBUG] Direct Salesforce connection failed: {str(sf_error)}")
                print(f"❌ [SERVER DEBUG] Direct connection error type: {type(sf_error).__name__}")
                if hasattr(sf_error, 'content'):
                    print(f"❌ [SERVER DEBUG] Error content: {sf_error.content}")
                # Continue with sf_client method below
            
        except Exception as decode_error:
            print(f"❌ [SERVER DEBUG] Credential decode error: {str(decode_error)}")
            print(f"❌ [SERVER DEBUG] Decode error type: {type(decode_error).__name__}")
            return [types.TextContent(type="text", text=f"Debug - Credential decode error: {str(decode_error)}")]
    
    # Original sf_client method
    if not query:
        raise ValueError("Missing 'query' argument")
    if not sf_client.connection:
        print(f"❌ [SERVER DEBUG] sf_client.connection is None - connection not established")
        raise ValueError("Salesforce connection not established.")
    
    print(f"🔄 [SERVER DEBUG] Using sf_client.connection for query...")
    try:
        results = sf_client.connection.query_all(query)
        print(f"✅ [SERVER DEBUG] sf_client query successful! {len(results.get('records', []))} records")
        # Consider limits on result size? Truncate or summarize if too large?
        return [
            types.TextContent(
                type="text",
                text=f"SF_CLIENT SUCCESS - SOQL Query Results (JSON):\\n{json.dumps(results, indent=2)}"
            )
        ]
    except SalesforceError as e:
        print(f"❌ [SERVER DEBUG] SalesforceError: {e.status} {e.resource_name} {e.content}")
        return [types.TextContent(type="text", text=f"Debug - SOQL Error: {e.status} {e.resource_name} {e.content}")]
    except Exception as e:
        print(f"❌ [SERVER DEBUG] General error executing SOQL: {str(e)}")
        print(f"❌ [SERVER DEBUG] Error type: {type(e).__name__}")
        return [types.TextContent(type="text", text=f"Debug - Error executing SOQL: {e}")]

def run_sosl_search_impl(sf_client: OrgHandler, arguments: dict[str, str]):
    search = arguments.get("search")
    if not search:
        raise ValueError("Missing 'search' argument")
    if not sf_client.connection:
        raise ValueError("Salesforce connection not established.")
    try:
        results = sf_client.connection.search(search)
        return [
            types.TextContent(
                type="text",
                text=f"SOSL Search Results (JSON):\\n{json.dumps(results, indent=2)}"
            )
        ]
    except SalesforceError as e:
        return [types.TextContent(type="text", text=f"SOSL Error: {e.status} {e.resource_name} {e.content}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error executing SOSL: {e}")]

def get_object_fields_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    object_name = arguments.get("object_name")
    if not object_name:
        raise ValueError("Missing 'object_name' argument")
    try:
        # Use the caching method from OrgHandler
        results = sf_client.get_object_fields_cached(object_name)
        return [
            types.TextContent(
                type="text",
                text=f"{object_name} Fields Metadata (JSON):\\n{json.dumps(results, indent=2)}"
            )
        ]
    except Exception as e: # Catches errors from get_object_fields_cached
         return [types.TextContent(type="text", text=f"Error getting fields for {object_name}: {e}")]

def create_record_impl(sf_client: OrgHandler, arguments: dict[str, Any]): # Data can be complex
    object_name = arguments.get("object_name")
    data = arguments.get("data")
    if not object_name or not data:
        raise ValueError("Missing 'object_name' or 'data' argument")
    if not sf_client.connection:
        raise ValueError("Salesforce connection not established.")
    if not isinstance(data, dict):
         raise ValueError("'data' argument must be a dictionary/object.")
    try:
        sf_object = getattr(sf_client.connection, object_name)
        results = sf_object.create(data)
        # Result usually {'id': '...', 'success': True, 'errors': []}
        return [
            types.TextContent(
                type="text",
                text=f"Create {object_name} Record Result (JSON):\\n{json.dumps(results, indent=2)}"
            )
        ]
    except SalesforceError as e:
        return [types.TextContent(type="text", text=f"Create Record Error: {e.status} {e.resource_name} {e.content}")]
    except AttributeError:
         return [types.TextContent(type="text", text=f"Error: Object type '{object_name}' not found or accessible via API.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error creating {object_name} record: {e}")]

def update_record_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    object_name = arguments.get("object_name")
    record_id = arguments.get("record_id")
    data = arguments.get("data")
    if not object_name or not record_id or not data:
        raise ValueError("Missing 'object_name', 'record_id', or 'data' argument")
    if not sf_client.connection:
        raise ValueError("Salesforce connection not established.")
    if not isinstance(data, dict):
         raise ValueError("'data' argument must be a dictionary/object.")
    try:
        sf_object = getattr(sf_client.connection, object_name)
        # Update returns status code (204 No Content on success)
        status_code = sf_object.update(record_id, data)
        success = 200 <= status_code < 300
        message = f"Update {object_name} record {record_id}: Status Code {status_code} - {'Success' if success else 'Failed'}"
        return [types.TextContent(type="text", text=message)]
    except SalesforceError as e:
        return [types.TextContent(type="text", text=f"Update Record Error: {e.status} {e.resource_name} {e.content}")]
    except AttributeError:
         return [types.TextContent(type="text", text=f"Error: Object type '{object_name}' not found or accessible via API.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error updating {object_name} record {record_id}: {e}")]

def delete_record_impl(sf_client: OrgHandler, arguments: dict[str, str]):
    object_name = arguments.get("object_name")
    record_id = arguments.get("record_id")
    if not object_name or not record_id:
        raise ValueError("Missing 'object_name' or 'record_id' argument")
    if not sf_client.connection:
        raise ValueError("Salesforce connection not established.")
    try:
        sf_object = getattr(sf_client.connection, object_name)
        # Delete returns status code (204 No Content on success)
        status_code = sf_object.delete(record_id)
        success = 200 <= status_code < 300
        message = f"Delete {object_name} record {record_id}: Status Code {status_code} - {'Success' if success else 'Failed'}"
        return [types.TextContent(type="text", text=message)]
    except SalesforceError as e:
        # Handle common delete errors (e.g., protected record)
        return [types.TextContent(type="text", text=f"Delete Record Error: {e.status} {e.resource_name} {e.content}")]
    except AttributeError:
         return [types.TextContent(type="text", text=f"Error: Object type '{object_name}' not found or accessible via API.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error deleting {object_name} record {record_id}: {e}")]

# --- End Data Operations ---

# --- Additional Functions from SFDC-MCP ---

def create_custom_fields_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    name = arguments.get("name")
    plural_name = arguments.get("plural_name")
    api_name = arguments.get("api_name")
    description = arguments.get("description")
    fields = arguments.get("fields")

    json_obj = {}
    json_obj["name"] = name
    json_obj["plural_name"] = plural_name
    json_obj["api_name"] = api_name
    json_obj["description"] = description
    json_obj["fields"] = fields

    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot perform metadata deployment.")
    metadata_service.write_to_file(json.dumps(json_obj))
    metadata_service.create_metadata_package(json_obj)
    metadata_service.deploy_object_package(sf_client.connection)

    return [
        types.TextContent(
            type="text",
            text=f"Custom fields on '{api_name}' creation package prepared and deployment initiated."
        )
    ]

def define_tabs_on_app_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """
    Defines or updates the tabs for an existing Lightning app.
    
    Args:
        sf_client: OrgHandler instance with an active Salesforce connection
        arguments: dict with keys:
            - app_api_name (str): API name of the existing app
            - tabs (list): List of tab API names to include in the app
            - append (bool, optional): If True, append to existing tabs. If False, replace existing tabs.
    """
    app_api_name = arguments.get("app_api_name")
    tabs = arguments.get("tabs")
    append = arguments.get("append", False)

    if not app_api_name or not isinstance(tabs, list):
        raise ValueError("Missing required arguments: app_api_name and tabs (must be a list)")

    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot update app tabs.")

    try:
        # For now, return a simple message since the actual implementation would require metadata service
        action = "appended to" if append else "replaced in"
        return [
            types.TextContent(
                type="text",
                text=f"Tabs {tabs} would be {action} app '{app_api_name}'. This function requires metadata service integration."
            )
        ]
    except Exception as e:
        raise ValueError(f"Error updating app tabs: {str(e)}")

def create_report_folder_impl(sf_client: OrgHandler, arguments: dict[str, str]):
    """Creates a new Salesforce report folder by inserting a Folder record via the REST API."""
    folder_api_name = arguments.get("folder_api_name")
    folder_label = arguments.get("folder_label")
    access_type = arguments.get("access_type", "Private")
    if not folder_api_name or not folder_label:
        return [types.TextContent(type="text", text="Missing 'folder_api_name' or 'folder_label'.")]
    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot create folder.")
    data = {
        "DeveloperName": folder_api_name,
        "Name": folder_label,
        "AccessType": access_type,
        "Type": "Report"
    }
    try:
        result = sf_client.connection.Folder.create(data)
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=(
                    f"Report folder '{folder_label}' (API Name: {folder_api_name}) created successfully. "
                    f"(Id: {result.get('id')})"
                )
            )]
        else:
            errors = "; ".join(result.get("errors", []))
            return [types.TextContent(type="text", text=f"Failed to create folder: {errors}")]
    except SalesforceError as e:
        return [types.TextContent(type="text", text=f"Salesforce Error creating folder: {e.status} {e.content}")]
    except Exception as e:
        raise ValueError(f"Unexpected error creating folder: {e}")

def create_dashboard_folder_impl(sf_client: OrgHandler, arguments: dict[str, str]):
    """Creates a new Salesforce dashboard folder by inserting a Folder record via the REST API."""
    folder_api_name = arguments.get("folder_api_name")
    folder_label = arguments.get("folder_label")
    access_type = arguments.get("access_type", "Private")
    if not folder_api_name or not folder_label:
        return [types.TextContent(type="text", text="Missing 'folder_api_name' or 'folder_label'.")]
    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot create dashboard folder.")
    data = {
        "DeveloperName": folder_api_name,
        "Name": folder_label,
        "AccessType": access_type,
        "Type": "Dashboard"
    }
    try:
        result = sf_client.connection.Folder.create(data)
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=(
                    f"Dashboard folder '{folder_label}' (API Name: {folder_api_name}) created successfully. "
                    f"(Id: {result.get('id')})"
                )
            )]
        else:
            errors = "; ".join(result.get("errors", []))
            return [types.TextContent(type="text", text=f"Failed to create dashboard folder: {errors}")]
    except SalesforceError as e:
        return [types.TextContent(type="text", text=f"Salesforce Error creating dashboard folder: {e.status} {e.content}")]
    except Exception as e:
        raise ValueError(f"Unexpected error creating dashboard folder: {e}")

def create_validation_rule_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """Creates a new validation rule on a specified object via the Tooling API."""
    object_name = arguments.get("object_name")
    rule_name = arguments.get("rule_name")
    active = arguments.get("active", True)
    description = arguments.get("description", "")
    error_condition_formula = arguments.get("error_condition_formula")
    error_message = arguments.get("error_message")
    error_display_field = arguments.get("error_display_field")
    
    # Validate required inputs
    missing = []
    for field in ("object_name", "rule_name", "error_condition_formula", "error_message"):
        if not arguments.get(field):
            missing.append(field)
    if missing:
        return [types.TextContent(
            type="text",
            text=f"Missing required argument(s): {', '.join(missing)}"
        )]
    if not sf_client.connection:
        raise ValueError("Salesforce connection is not active. Cannot create validation rule.")
    
    # Resolve TableEnumOrId: use custom object ID for __c objects, or API name for standard objects
    if object_name.endswith('__c'):
        # Query CustomObject by full API name (DeveloperName includes __c)
        soql_obj = f"SELECT Id FROM CustomObject WHERE DeveloperName = '{object_name}'"
        obj_query = sf_client.connection.tooling.query(soql_obj)
        if obj_query.get('totalSize', 0) > 0:
            table_enum_or_id = obj_query['records'][0]['Id']
        else:
            return [types.TextContent(type="text", text=f"Custom object '{object_name}' not found.")]
    else:
        table_enum_or_id = object_name

    # Prepare payload for Tooling API
    payload = {
        "DeveloperName": rule_name,
        "TableEnumOrId": table_enum_or_id,
        "Active": active,
        "ErrorConditionFormula": error_condition_formula,
        "ErrorMessage": error_message,
        "Description": description
    }
    if error_display_field:
        # Use QualifiedApiName to match the full API name including __c
        soql_field = f"SELECT Id FROM CustomField WHERE TableEnumOrId = '{table_enum_or_id}' AND QualifiedApiName = '{error_display_field}'"
        field_query = sf_client.connection.tooling.query(soql_field)
        if field_query.get('totalSize', 0) > 0:
            payload["ErrorDisplayField"] = field_query['records'][0]['Id']
        else:
            return [types.TextContent(type="text", text=f"Field '{error_display_field}' not found on object '{object_name}'.")]
    try:
        result = sf_client.connection.tooling.create("ValidationRule", payload)
        if result.get("success"):
            return [types.TextContent(
                type="text",
                text=(
                    f"Validation Rule '{rule_name}' created on {object_name}. "
                    f"(Id: {result.get('id')})"
                )
            )]
        else:
            errs = result.get("errors", [])
            return [types.TextContent(type="text", text=f"Failed to create validation rule: {errs}")]
    except SalesforceError as e:
        return [types.TextContent(type="text", text=f"Salesforce Error creating validation rule: {e.status} {e.content}")]
    except Exception as e:
        raise ValueError(f"Unexpected error creating validation rule: {e}")

def create_custom_metadata_type_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """Creates a new Custom Metadata Type via the Metadata API."""
    api_name = arguments.get("api_name")
    label = arguments.get("label")
    plural_name = arguments.get("plural_name")
    description = arguments.get("description", "")
    fields = arguments.get("fields")

    # Validate required inputs
    missing = []
    for arg in ("api_name", "label", "plural_name", "fields"):
        if not arguments.get(arg):
            missing.append(arg)
    if missing:
        return [types.TextContent(type="text", text=f"Missing required argument(s): {', '.join(missing)}")]

    if not sf_client.connection:
        raise ValueError("Salesforce connection not active. Cannot deploy custom metadata type.")

    # For now, return a simple message since metadata service integration is needed
    return [types.TextContent(type="text", text=f"Custom Metadata Type '{api_name}' would be created with {len(fields)} fields. This function requires metadata service integration.")]

def create_lightning_page_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """Creates a new Lightning App Page in Salesforce with a unique name."""
    try:
        page_label = arguments.get("label", "Simple Lightning App Page")
        description = arguments.get("description", "")
        
        # For now, return a simple message since metadata service integration is needed
        return [types.TextContent(type="text", text=f"Lightning Page '{page_label}' would be created. This function requires metadata service integration.")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error creating Lightning App Page: {str(e)}")]

def describe_object_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """
    Get detailed schema information for a Salesforce object, formatted as markdown.
    """
    object_name = arguments.get("object_name")
    include_field_details = arguments.get("include_field_details", True)
    if not object_name:
        return [types.TextContent(type="text", text="Missing 'object_name' argument")]  
    if not sf_client.connection:
        return [types.TextContent(type="text", text="Salesforce connection not established.")]
    try:
        sf_object = getattr(sf_client.connection, object_name)
        describe = sf_object.describe()
        
        # Basic object info
        result = f"## {describe['label']} ({describe['name']})\n\n"
        result += f"**Type:** {'Custom Object' if describe.get('custom') else 'Standard Object'}\n"
        result += f"**API Name:** {describe['name']}\n"
        result += f"**Label:** {describe['label']}\n"
        result += f"**Plural Label:** {describe.get('labelPlural', '')}\n"
        result += f"**Key Prefix:** {describe.get('keyPrefix', 'N/A')}\n"
        result += f"**Createable:** {describe.get('createable')}\n"
        result += f"**Updateable:** {describe.get('updateable')}\n"
        result += f"**Deletable:** {describe.get('deletable')}\n\n"
        
        if include_field_details:
            # Fields table
            result += "## Fields\n\n"
            result += "| API Name | Label | Type | Required | Unique | External ID |\n"
            result += "|----------|-------|------|----------|--------|------------|\n"
            for field in describe["fields"]:
                required = "Yes" if not field.get("nillable", True) else "No"
                unique = "Yes" if field.get("unique", False) else "No"
                external_id = "Yes" if field.get("externalId", False) else "No"
                result += f"| {field['name']} | {field['label']} | {field['type']} | {required} | {unique} | {external_id} |\n"
                
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error describing object {object_name}: {str(e)}")]

def describe_relationship_fields_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """
    Get detailed information about all relationship fields for a Salesforce object, formatted as markdown.
    """
    object_name = arguments.get("object_name")
    if not object_name:
        return [types.TextContent(type="text", text="Missing 'object_name' argument")]
    if not sf_client.connection:
        return [types.TextContent(type="text", text="Salesforce connection not established.")]
    try:
        sf_object = getattr(sf_client.connection, object_name)
        describe = sf_object.describe()
        
        # Parent relationships (lookup/master-detail fields)
        reference_fields = [
            f for f in describe["fields"] if f["type"] == "reference" and f.get("referenceTo")
        ]
        # Child relationships (other objects referencing this one)
        child_relationships = describe.get("childRelationships", [])
        
        # Markdown output
        result = f"# Relationship Fields for {describe['label']} ({describe['name']})\n\n"
        
        # Parent relationships section
        if reference_fields:
            result += "## Lookup/Master-Detail Fields (Parent Relationships)\n\n"
            result += "| API Name | Field Label | Related To | Relationship Name | Type |\n"
            result += "|----------|------------|-----------|------------------|------|\n"
            for field in reference_fields:
                related_to = ", ".join(field["referenceTo"])
                rel_name = field.get("relationshipName", "N/A")
                rel_type = "Master-Detail" if not field.get("nillable", True) else "Lookup"
                result += f"| {field['name']} | {field['label']} | {related_to} | {rel_name} | {rel_type} |\n"
        else:
            result += "No parent relationship fields found.\n\n"
            
        # Child relationships section
        if child_relationships:
            result += "\n## Child Relationships\n\n"
            result += "| Child Object | Relationship Name | Field Name | Cascade Delete |\n"
            result += "|-------------|------------------|-----------|---------------|\n"
            for rel in child_relationships:
                rel_name = rel.get("relationshipName") or "N/A"
                cascade = "Yes" if rel.get("cascadeDelete", False) else "No"
                result += f"| {rel['childSObject']} | {rel_name} | {rel['field']} | {cascade} |\n"
        else:
            result += "\nNo child relationships found.\n"
            
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error describing relationship fields for {object_name}: {str(e)}")]

def get_fields_by_type_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """
    Get fields of a specific type for a Salesforce object, formatted as a markdown table.
    """
    object_name = arguments.get("object_name")
    field_type = arguments.get("field_type")
    if not object_name:
        return [types.TextContent(type="text", text="Missing 'object_name' argument")]
    if not sf_client.connection:
        return [types.TextContent(type="text", text="Salesforce connection not established.")]
    try:
        sf_object = getattr(sf_client.connection, object_name)
        describe = sf_object.describe()
        fields = describe["fields"]
        
        # Filter by type if specified
        if field_type:
            fields = [f for f in fields if f["type"].lower() == field_type.lower()]
            if not fields:
                return [types.TextContent(type="text", text=f"No fields of type '{field_type}' found on object '{object_name}'.")]
        
        # Markdown header
        if field_type:
            result = f"# {field_type.capitalize()} Fields on {describe['label']} ({describe['name']})\n\n"
        else:
            result = f"# All Fields on {describe['label']} ({describe['name']})\n\n"
        result += "| API Name | Label | Type | Required | Updateable | Custom | Description |\n"
        result += "|----------|-------|------|----------|------------|--------|-------------|\n"
        
        # Sort fields by name for consistent output
        fields.sort(key=lambda f: f["name"])
        for field in fields:
            required = "Yes" if not field.get("nillable", True) else "No"
            updateable = "Yes" if field.get("updateable", False) else "No"
            custom = "Yes" if field.get("custom", False) else "No"
            description = field.get("inlineHelpText", "")
            if description:
                description = description.replace("\n", " ").replace("|", "\\|")
            result += f"| {field['name']} | {field['label']} | {field['type']} | {required} | {updateable} | {custom} | {description} |\n"
            
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error getting fields for {object_name}: {str(e)}")]

def get_picklist_values_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """
    Get picklist values for a specific Salesforce field, formatted as a markdown table.
    """
    object_name = arguments.get("object_name")
    field_name = arguments.get("field_name")
    if not object_name or not field_name:
        return [types.TextContent(type="text", text="Missing 'object_name' or 'field_name' argument")]
    if not sf_client.connection:
        return [types.TextContent(type="text", text="Salesforce connection not established.")]
    try:
        sf_object = getattr(sf_client.connection, object_name)
        describe = sf_object.describe()
        
        # Find the specific field
        field = next((f for f in describe["fields"] if f["name"] == field_name), None)
        if not field:
            return [types.TextContent(type="text", text=f"Field '{field_name}' not found on object '{object_name}'.")]
        if field["type"] not in ("picklist", "multipicklist"):
            return [types.TextContent(type="text", text=f"Field '{field_name}' is not a picklist field (type: {field['type']}).")]
        
        # Markdown table
        result = f"Picklist values for {object_name}.{field_name} ({field['label']}):\n\n"
        result += "| Value | Label | Default | Active |\n"
        result += "|-------|-------|---------|--------|\n"
        for value in field.get("picklistValues", []):
            is_default = "Yes" if value.get("defaultValue", False) else "No"
            is_active = "Yes" if value.get("active", True) else "No"
            val = str(value["value"]).replace("|", "\\|")
            label = str(value["label"]).replace("|", "\\|")
            result += f"| {val} | {label} | {is_default} | {is_active} |\n"
            
        return [types.TextContent(type="text", text=result)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error getting picklist values for {object_name}.{field_name}: {str(e)}")]

def get_validation_rules_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """
    Get validation rules for a specific object using Tooling API, formatted as a markdown table.
    """
    object_name = arguments.get("object_name")
    if not object_name:
        return [types.TextContent(type="text", text="Missing 'object_name' argument")]
    if not sf_client.connection:
        return [types.TextContent(type="text", text="Salesforce connection not established.")]
    try:
        # Build SOQL query for validation rules
        soql = (
            "SELECT Id, ValidationName, Active, Description, "
            "EntityDefinition.DeveloperName, ErrorDisplayField, ErrorMessage "
            f"FROM ValidationRule WHERE EntityDefinition.DeveloperName='{object_name}' "
            "ORDER BY ValidationName"
        )
        result = sf_client.connection.tooling.query(soql)
        records = result.get("records", [])
        
        if not records:
            return [types.TextContent(type="text", text=f"No validation rules found for {object_name}.")]
            
        output = f"Found {len(records)} validation rules for {object_name}:\n\n"
        output += "| Name | Active | Error Message | Error Field | Description |\n"
        output += "|------|--------|--------------|------------|-------------|\n"
        
        for rule in records:
            active = "Yes" if rule.get("Active", False) else "No"
            error_field = rule.get("ErrorDisplayField", "N/A")
            error_message = rule.get("ErrorMessage", "")
            if error_message is not None:
                error_message = error_message.replace("\n", " ").replace("|", "\\|")
            else:
                error_message = "N/A"
            description = rule.get("Description", "")
            if description is not None:
                if len(description) > 100:
                    description = description[:97] + "..."
                description = description.replace("\n", " ").replace("|", "\\|")
            else:
                description = "N/A"
            output += f"| {rule.get('ValidationName', 'N/A')} | {active} | {error_message} | {error_field} | {description} |\n"
            
        return [types.TextContent(type="text", text=output)]
    except Exception as e:
        return [types.TextContent(type="text", text=f"Error retrieving validation rules: {str(e)}")]

# --- Einstein Studio Model Implementations ---

def create_einstein_model_impl(sf_client: OrgHandler, arguments: dict[str, Any]):
    """Creates an Einstein Studio model using AppFrameworkTemplateBundle."""
    model_name = arguments.get("model_name")
    description = arguments.get("description")
    model_capability = arguments.get("model_capability", "BinaryClassification")
    outcome_field = arguments.get("outcome_field")
    goal = arguments.get("goal", "Maximize")
    data_source = arguments.get("data_source")
    success_value = arguments.get("success_value", "true")
    failure_value = arguments.get("failure_value", "false")
    algorithm_type = arguments.get("algorithm_type", "XGBoost")
    fields = arguments.get("fields", [])

    # Validate required fields
    if not all([model_name, description, outcome_field, data_source, fields]):
        return [types.TextContent(
            type="text", 
            text="Missing required fields: model_name, description, outcome_field, data_source, and fields are required"
        )]

    if not sf_client.connection:
        return [types.TextContent(
            type="text", 
            text="Salesforce connection is not active. Cannot perform metadata deployment."
        )]

    try:
        # Create Einstein Studio model package
        json_obj = {
            "model_name": model_name,
            "description": description,
            "model_capability": model_capability,
            "outcome_field": outcome_field,
            "goal": goal,
            "data_source": data_source,
            "success_value": success_value,
            "failure_value": failure_value,
            "algorithm_type": algorithm_type,
            "fields": fields
        }

        sfdc_client.write_to_file(json.dumps(json_obj))
        sfdc_client.create_einstein_model_package(json_obj)
        sfdc_client.deploy_package_from_deploy_dir(sf_client.connection)

        return [
            types.TextContent(
                type="text",
                text=f"Einstein Studio model '{model_name}' creation package prepared and deployment initiated."
            )
        ]
    except Exception as e:
        return [types.TextContent(
            type="text", 
            text=f"Error creating Einstein Studio model: {str(e)}"
        )]
