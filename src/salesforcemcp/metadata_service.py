import json
import shutil
import os
import base64
import xml.etree.ElementTree as ET # Need this for parsing SOAP fault
from xml.dom import minidom
import zipfile
from simple_salesforce import Salesforce
from datetime import datetime
import re
import time
import tempfile

# Use paths that work in both local and serverless environments
BASE_PATH = tempfile.gettempdir()  # Always use /tmp for writes
DEPLOY_DIR = "deployment_package"

# For reading assets, try multiple possible locations
def get_assets_path():
    """Find the assets directory in various possible locations"""
    possible_paths = [
        os.path.join(os.path.dirname(__file__), '..', 'assets'),  # Local development
        os.path.join('/var/task/src', 'assets'),  # Vercel serverless
        os.path.join('/var/task', 'src', 'assets'),  # Alternative Vercel path
        os.path.join(os.path.dirname(__file__), 'assets'),  # Direct relative
    ]
    
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            print(f"Found assets at: {abs_path}")
            return abs_path
    
    print(f"❌ Assets directory not found! Tried: {possible_paths}")
    raise FileNotFoundError("Assets directory not found in any expected location")

# Global variables for temp directories in serverless environments
current_package_dir = None
current_delete_dir = None

# Use /tmp for serverless environments like Vercel
def get_temp_dir(name="current"):
    """Get a temporary directory that works in serverless environments"""
    temp_dir = os.path.join(tempfile.gettempdir(), f"sf_metadata_{name}_{int(time.time())}")
    # Don't create the directory - let copytree create it
    return temp_dir

def _clean_deploy_dir():
    """Removes and recreates the deployment directory."""
    deploy_path = os.path.join(BASE_PATH, DEPLOY_DIR)
    if os.path.exists(deploy_path):
        shutil.rmtree(deploy_path)
    os.makedirs(deploy_path, exist_ok=True)

def write_to_file(content):
    # Use temp file for logging in serverless environments
    log_file = os.path.join(tempfile.gettempdir(), "sf_metadata.log")
    with open(log_file, 'a') as f:
        f.write(content + '\n')

def create_metadata_package(json_obj):
    try:
        name = json_obj["name"]
        plural_name = json_obj["plural_name"]
        description = json_obj["description"]
        api_name = json_obj["api_name"]
        fields = json_obj["fields"]

        # Use temporary directory for serverless environments
        destination = get_temp_dir("current")
        
        # Use the assets path finder instead of hardcoded path
        assets_path = get_assets_path()
        source = os.path.join(assets_path, "create_object_tmpl")

        shutil.copytree(source, destination, dirs_exist_ok=True)

        old_name = f"{destination}/objects/##api_name##.object"
        new_name = f"{destination}/objects/{api_name}.object"

        os.rename(old_name, new_name)
        
        # Store destination path for later use
        global current_package_dir
        current_package_dir = destination

        # Use assets path finder for field template
        field_tmpl_path = os.path.join(get_assets_path(), "field.tmpl")
        with open(field_tmpl_path, "r", encoding="utf-8") as file:
            field_tmpl = file.read()

        fields_str = ""
        field_names = []  # Track field names for profile permissions

        for field in fields:
            type_def = ""

            f_name = field["label"]
            f_type = field["type"]
            f_api_name = field["api_name"]
            field_names.append(f_api_name)  # Add field name to list

            # Debug log removed for serverless compatibility

            if f_type == "Text":
                type_def = """<type>Text</type>\n                    <length>100</length>"""
            elif f_type == "URL":
                type_def = "<type>Url</type>"
            elif f_type == "Checkbox":
                default_val = field.get("defaultValue", False)
                type_def = f"<type>Checkbox</type>\n                    <defaultValue>{str(default_val).lower()}</defaultValue>"
            elif f_type == "Lookup":
                reference_to = field.get("referenceTo", "")
                relationship_label = field.get("relationshipLabel", "")
                relationship_name = field.get("relationshipName", "")
                type_def = f"<type>Lookup</type>\n                    <referenceTo>{reference_to}</referenceTo>"
                if relationship_label:
                    type_def += f"\n                    <relationshipLabel>{relationship_label}</relationshipLabel>"
                if relationship_name:
                    type_def += f"\n                    <relationshipName>{relationship_name}</relationshipName>"
            else:
                if f_type == "Picklist":
                    # Debug log removed for serverless compatibility

                    f_picklist_values = field["picklist_values"]

                    picklist_values_str = ""
                    for picklist_value in f_picklist_values:
                        val = f"""<value>
                                    <fullName>{picklist_value}</fullName>
                                    <default>false</default>
                                    <label>{picklist_value}</label>
                                </value>
                                """
                        picklist_values_str = picklist_values_str + val

                    type_def = f"""
                        <type>Picklist</type>
                        <valueSet>
                            <restricted>true</restricted>
                            <valueSetDefinition>
                                <sorted>false</sorted>
                                {picklist_values_str}
                            </valueSetDefinition>
                        </valueSet>
                        """
                else:
                    # Debug log removed for serverless compatibility
                    type_def = """<precision>18</precision>
                        <scale>0</scale>
                        <type>Number</type>"""

            new_field = field_tmpl.replace("##api_name##", f_api_name)
            new_field = new_field.replace("##name##", f_name)
            new_field = new_field.replace("##type##", type_def)
            fields_str = fields_str + new_field

        # Debug log removed for serverless compatibility
        print(f"Generated fields metadata: {len(fields)} fields")

        # Update package.xml to include both object and profile
        package_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>{api_name}</members>
        <name>CustomObject</name>
    </types>
    <types>
        <members>Admin</members>
        <name>Profile</name>
    </types>
    <version>63.0</version>
</Package>""".format(api_name=api_name)

        with open(f"{destination}/package.xml", "w", encoding="utf-8") as file:
            file.write(package_xml)

        obj_path = f"{destination}/objects/{api_name}.object"

        with open(obj_path, "r", encoding="utf-8") as file:
            obj_tmpl = file.read()

        if description is None:
            description = ""

        obj_tmpl = obj_tmpl.replace("##description##", description)
        obj_tmpl = obj_tmpl.replace("##name##", name)
        obj_tmpl = obj_tmpl.replace("##plural_name##", plural_name)
        obj_tmpl = obj_tmpl.replace("##fields##", fields_str)

        with open(obj_path, "w", encoding="utf-8") as file:
            file.write(obj_tmpl)

        # Create profiles directory in the deployment package
        profiles_dir = os.path.join(destination, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)

        # Create field permissions XML
        field_permissions = ""
        for field in field_names:
            field_permissions += f"""    <fieldPermissions>
        <editable>true</editable>
        <field>{api_name}.{field}</field>
        <readable>true</readable>
    </fieldPermissions>
"""

        # Create profile XML using template
        profile_tmpl_path = os.path.join(get_assets_path(), "profile.tmpl")
        with open(profile_tmpl_path, "r", encoding="utf-8") as f:
            profile_template = f.read()

        profile_xml = profile_template.replace("##fieldPermissions##", field_permissions)

        # Write profile XML
        with open(os.path.join(profiles_dir, "Admin.profile"), "w", encoding="utf-8") as f:
            f.write(profile_xml)

    except Exception as e:
        # Reset the global variable since package creation failed
        current_package_dir = None
        err_msg = f"An error occurred: {e}"
        print(f"Metadata package error: {err_msg}")  # Use print instead of file write
        raise  # Re-raise the exception so the caller knows it failed


def delete_fields(json_obj):
    api_name = json_obj["api_name"]
    fields = json_obj["fields"]

    members = ""

    for field in fields:
        field_name = field["api_name"]
        members = members + f"<members>{api_name}.{field_name}</members>\n"

    # No need to clean up - using fresh temp directories

    # Use assets path finder and temp directory
    assets_path = get_assets_path()
    source = os.path.join(assets_path, "delete_fields_tmpl")
    destination = get_temp_dir("current_delete")
    
    # Store destination path for later use
    global current_delete_dir
    current_delete_dir = destination

    shutil.copytree(source, destination, dirs_exist_ok=True)

    with open(f"{destination}/destructiveChanges.xml", "r", encoding="utf-8") as file:
        destructive = file.read()

    destructive = destructive.replace("##fields##", members)
        
    with open(f"{destination}/destructiveChanges.xml", "w", encoding="utf-8") as file:
        file.write(destructive)

def create_tab_package(json_obj):
    tab_api_name = json_obj["tab_api_name"]
    tab_type = json_obj["tab_type"]
    label = json_obj["label"]
    motif = json_obj.get("motif")
    description = json_obj.get("description")
    object_name = json_obj.get("object_name")
    vf_page_name = json_obj.get("vf_page_name")
    web_url = json_obj.get("web_url")
    url_encoding_key = json_obj.get("url_encoding_key", "UTF8")

    # --- Basic Validation (keep this) --- 
    valid_types = ['CustomObject', 'VisualforcePage', 'Web']
    if tab_type not in valid_types:
        print(f"Invalid tab_type: {tab_type}. Must be one of {valid_types}")
        return
    if tab_type == 'CustomObject' and tab_api_name != object_name:
         print(f"Error: For CustomObject tabs, tab_api_name ('{tab_api_name}') must match the object_name ('{object_name}')")
         return
    if tab_type == 'VisualforcePage' and not vf_page_name:
        print(f"Error: vf_page_name is required for VisualforcePage tabs.")
        return
    if tab_type == 'Web' and not web_url:
        print(f"Error: web_url is required for Web tabs.")
        return
    # Add motif format validation if needed

    # --- Prepare Environment (keep this) --- 
    # No need to clean up - using fresh temp directories

    # Use assets path finder and temp directory
    assets_path = get_assets_path()
    source = os.path.join(assets_path, "create_tab_tmpl")
    destination = get_temp_dir("current")
    
    # Store destination path for later use
    global current_package_dir
    current_package_dir = destination

    try:
        shutil.copytree(source, destination, dirs_exist_ok=True)
    except Exception as e:
        print(f"Error copying template directory: {e}")
        return

    # Define target filename
    new_tab_meta_name = f"{destination}/tabs/{tab_api_name}.tab-meta.xml"
    # Ensure the target directory exists
    try:
        os.makedirs(os.path.dirname(new_tab_meta_name), exist_ok=True)
    except OSError as e:
        print(f"Error creating target directory: {e}")
        return

    # We can delete the copied template file as we won't use it
    old_tab_meta_name = f"{destination}/tabs/Template.tab-meta.xml"
    if os.path.exists(old_tab_meta_name):
        try:
            os.remove(old_tab_meta_name)
        except OSError as e:
             print(f"Warning: Could not remove template file {old_tab_meta_name}: {e}")

    # --- Update package.xml (keep this) --- 
    package_path = f"{destination}/package.xml"
    try:
        with open(package_path, "r", encoding="utf-8") as file:
            pack_tmpl = file.read()
        pack_tmpl = pack_tmpl.replace("##tab_api_name##", tab_api_name)
        with open(package_path, "w", encoding="utf-8") as file:
            file.write(pack_tmpl)
    except Exception as e:
        print(f"Error processing package.xml: {e}")
        return

    # --- Manually Construct Tab Meta XML --- 
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<CustomTab xmlns="http://soap.sforce.com/2006/04/metadata">',
        f'    <label>{label}</label>',
        f'    <motif>{motif}</motif>'
    ]
    
    # Add type-specific tag
    if tab_type == 'CustomObject':
        xml_lines.append('    <customObject>true</customObject>')
    elif tab_type == 'VisualforcePage':
        xml_lines.append(f'    <page>{vf_page_name}</page>')
    elif tab_type == 'Web':
        xml_lines.append(f'    <url>{web_url}</url>')
        xml_lines.append(f'    <urlEncodingKey>{url_encoding_key}</urlEncodingKey>')
        
    # Add optional description
    if description:
        xml_lines.append(f'    <description>{description}</description>')
        
    xml_lines.append('</CustomTab>')
    
    final_xml_content = "\n".join(xml_lines)
    # --- End XML Construction --- 

    # --- Write Constructed XML to File --- 
    try:
        with open(new_tab_meta_name, "w", encoding="utf-8") as file:
            file.write(final_xml_content)
    except Exception as e:
        print(f"Error writing .tab-meta.xml file: {e}")
        return
    # --- End Write XML ---

    # --- Create or Update Profile with Tab Visibility ---
    profiles_dir = os.path.join(destination, "profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    profile_file = os.path.join(profiles_dir, "Admin.profile-meta.xml")

    tab_visibility_xml = f"""    <tabVisibilities>\n        <tab>{tab_api_name}</tab>\n        <visibility>DefaultOn</visibility>\n    </tabVisibilities>\n"""

    if os.path.exists(profile_file):
        # Parse and append if not already present
        tree = ET.parse(profile_file)
        root = tree.getroot()
        ns = {'sf': 'http://soap.sforce.com/2006/04/metadata'}
        # Register namespace for writing
        ET.register_namespace('', 'http://soap.sforce.com/2006/04/metadata')
        exists = any(
            tv.find('tab').text == tab_api_name
            for tv in root.findall('sf:tabVisibilities', ns)
            if tv.find('tab') is not None
        )
        if not exists:
            tab_vis = ET.SubElement(root, 'tabVisibilities')
            tab = ET.SubElement(tab_vis, 'tab')
            tab.text = tab_api_name
            vis = ET.SubElement(tab_vis, 'visibility')
            vis.text = 'DefaultOn'
            tree.write(profile_file, encoding='utf-8', xml_declaration=True)
    else:
        # Use template as before
        profile_tmpl_path = os.path.join(get_assets_path(), "profile.tmpl")
        with open(profile_tmpl_path, "r", encoding="utf-8") as f:
            profile_template = f.read()
        profile_xml = profile_template.replace("##fieldPermissions##", "")
        profile_xml = profile_xml.replace("##tabVisibilities##", tab_visibility_xml)
        with open(profile_file, "w", encoding="utf-8") as f:
            f.write(profile_xml)

    # Update package.xml to include profile
    package_xml = """<?xml version="1.0" encoding="UTF-8"?>\n<Package xmlns="http://soap.sforce.com/2006/04/metadata">\n    <types>\n        <members>##tab_api_name##</members>\n        <name>CustomTab</name>\n    </types>\n    <types>\n        <members>Admin</members>\n        <name>Profile</name>\n    </types>\n    <version>58.0</version>\n</Package>"""

    with open(package_path, "w", encoding="utf-8") as f:
        f.write(package_xml.replace("##tab_api_name##", tab_api_name))

def create_custom_app_package(json_obj):
    """Prepares a package to deploy a single Custom Application.

    Args:
        json_obj (dict): Contains app parameters like api_name, label, nav_type, tabs, etc.
    """
    # Extract parameters
    api_name = json_obj.get("api_name")
    label = api_name  # Force label to always match developer name
    nav_type = json_obj.get("nav_type", "Standard") # Default to Standard
    tabs = json_obj.get("tabs", [])
    description = json_obj.get("description", "")
    header_color = json_obj.get("header_color") # Optional
    form_factors = json_obj.get("form_factors", ["Small", "Large"]) # Default
    setup_experience = json_obj.get("setup_experience", "all") # Default

    # Basic validation
    if not all([api_name, label, tabs]):
        print("Error: Missing required app parameters: api_name, label, tabs.")
        return
    if nav_type not in ["Standard", "Console"]:
        print(f"Warning: Invalid nav_type '{nav_type}'. Defaulting to Standard.")
        nav_type = "Standard"
    if not isinstance(tabs, list) or not all(isinstance(t, str) for t in tabs):
         print("Error: 'tabs' parameter must be a list of strings (tab API names).")
         return
    if not isinstance(form_factors, list) or not all(f in ["Small", "Large"] for f in form_factors):
        print("Warning: Invalid form_factors. Defaulting to ['Small', 'Large'].")
        form_factors = ["Small", "Large"]
    if setup_experience not in ["all", "none"]:
        print(f"Warning: Invalid setup_experience '{setup_experience}'. Defaulting to 'all'.")
        setup_experience = "all"

    # --- Prepare environment --- 
    global current_package_dir
    current_package_dir = get_temp_dir("custom_app")
    
    assets_path = get_assets_path()
    source_tmpl_dir = os.path.join(assets_path, "create_custom_app_tmpl")
    try:
        shutil.copytree(source_tmpl_dir, current_package_dir, dirs_exist_ok=True)
    except Exception as e:
        print(f"Error copying template directory: {e}")
        return
        
    # Rename app template file
    old_app_file = f"{current_package_dir}/applications/Template.app-meta.xml"
    new_app_file = f"{current_package_dir}/applications/{api_name}.app-meta.xml"
    try:
        # Ensure directory exists (needed if copytree didn't create it fully)
        os.makedirs(os.path.dirname(new_app_file), exist_ok=True) 
        os.rename(old_app_file, new_app_file)
    except OSError as e:
        print(f"Error renaming app template file: {e}")
        return
        
    # --- Update package.xml for CustomApplication only --- 
    package_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>{api_name}</members>
        <name>CustomApplication</name>
    </types>
    <version>63.0</version>
</Package>""".format(api_name=api_name)

    with open(os.path.join(current_package_dir, "package.xml"), "w", encoding="utf-8") as f:
        f.write(package_xml)
        
    # --- Prepare App XML using Template --- 
    try:
        with open(new_app_file, "r", encoding="utf-8") as file:
            app_tmpl = file.read()

        # Prepare all replacements
        replacements = {
            "##api_name##": api_name,
            "##label##": label,
            "##description##": description or "",
            "##nav_type##": nav_type,
            "##setup_experience##": setup_experience,
        }

        # Replace all placeholders
        for key, value in replacements.items():
            app_tmpl = app_tmpl.replace(key, value)
        
        # Generate brand XML (optional)
        brand_xml = ""
        if header_color:
             # Basic color validation could be added here (#ABCDEF format)
             brand_xml = f"    <brand>\n        <headerColor>{header_color}</headerColor>\n        <shouldOverrideOrgTheme>true</shouldOverrideOrgTheme>\n    </brand>"
        app_tmpl = app_tmpl.replace("<!-- ##brand_placeholder## -->", brand_xml)
        
        # Generate form factors XML - ensure it's properly placed in the XML structure
        form_factors_xml = "\n".join([f"    <formFactors>{ff}</formFactors>" for ff in form_factors])
        # Remove the placeholder comment and add the form factors
        app_tmpl = app_tmpl.replace("<!-- ##form_factors_placeholder## -->", form_factors_xml)
        
        # Generate tabs XML
        tabs_xml = "\n".join([f"    <tabs>{tab}</tabs>" for tab in tabs])
        app_tmpl = app_tmpl.replace("<!-- ##tabs_placeholder## -->", tabs_xml)

        # Clean up potentially empty lines from removed placeholders
        app_tmpl = "\n".join(line for line in app_tmpl.splitlines() if line.strip())

        # --- Debug: Log the processed XML ---
        with open(f"{BASE_PATH}/app_xml_debug.xml", "w", encoding="utf-8") as debug_f:
            debug_f.write(app_tmpl)

        # --- Safeguard: Check for any remaining placeholders ---
        if "##label##" in app_tmpl or "##description##" in app_tmpl:
            raise ValueError(f"Placeholder(s) not replaced in app XML for {api_name}. Check app_xml_debug.xml for details.")

        # Write the final XML
        with open(new_app_file, "w", encoding="utf-8") as f:
            f.write(app_tmpl)
        print(f"Custom App XML generated and written to: {new_app_file}")

        # Create profiles directory with proper structure
        profiles_dir = os.path.join(current_package_dir, "profiles")
        os.makedirs(profiles_dir, exist_ok=True)

        # Read the profile template
        profile_tmpl_path = os.path.join(assets_path, "create_custom_app_tmpl", "profiles", "Admin.profile-meta.xml")
        with open(profile_tmpl_path, "r", encoding="utf-8") as f:
            profile_template = f.read()

        # Replace the API name in the profile template
        profile_xml = profile_template.replace("##api_name##", api_name)

        # Prepare application visibility block
        app_vis_block = f"""    <applicationVisibilities>\n        <application>{api_name}</application>\n        <default>true</default>\n        <visible>true</visible>\n    </applicationVisibilities>\n"""
        # Replace the placeholder (if present)
        if "##applicationVisibilities##" in profile_xml:
            profile_xml = profile_xml.replace("##applicationVisibilities##", app_vis_block)
        else:
            # Fallback: add before </Profile> if placeholder is missing
            if f"<application>{api_name}</application>" not in profile_xml:
                profile_xml = profile_xml.replace("</Profile>", f"{app_vis_block}</Profile>")

        # Write profile XML with proper name
        profile_file = os.path.join(profiles_dir, "Admin.profile-meta.xml")
        with open(profile_file, "w", encoding="utf-8") as f:
            f.write(profile_xml)
            
    except Exception as e:
        print(f"Error processing app template or writing file: {e}")
        return

def zip_directory(filepath):
    source_directory = filepath
    output_zip_name = f"{BASE_PATH}/pack"
    shutil.make_archive(output_zip_name, 'zip', source_directory)

def binary_to_base64(file_path):
    try:
        with open(file_path, "rb") as binary_file:
            binary_data = binary_file.read()
            base64_encoded = base64.b64encode(binary_data)
            return base64_encoded.decode('utf-8')
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return None

import requests

def deploy(b64, sf):
    """Deploys the zipped package using the provided simple_salesforce connection."""
    if not sf:
         print("Error: Salesforce connection object (sf) not provided to deploy function.")
         raise ValueError("Deployment failed: Invalid Salesforce connection.")

    # --- Dynamically get session ID and instance URL --- 
    try:
        session_id = sf.session_id
        # simple-salesforce often stores instance like 'yourinstance.my.salesforce.com'
        # or 'yourinstance.lightning.force.com', ensure it's just the base instance
        instance_url = sf.sf_instance
        if not instance_url:
             raise ValueError("Could not retrieve instance URL from Salesforce connection.")
        # Construct the metadata API endpoint URL
        # Ensure API version matches package.xml if necessary (using 58.0 here)
        metadata_api_version = "58.0" 
        endpoint = f"https://{instance_url}/services/Soap/m/{metadata_api_version}"
        print(f"Using dynamic endpoint: {endpoint}") # Log the endpoint being used
    except AttributeError as e:
         print(f"Error accessing connection attributes: {e}")
         raise ValueError("Deployment failed: Could not get session details from Salesforce connection.")
    # --- End Dynamic Info --- 

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        'SOAPAction': '""'
    }

    xml_body_template = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:met="http://soap.sforce.com/2006/04/metadata">
   <soapenv:Header>
      <met:SessionHeader>
         <met:sessionId>{session_id}</met:sessionId> <!-- Dynamic Session ID -->
      </met:SessionHeader>
   </soapenv:Header>
   <soapenv:Body>
      <met:deploy>
         <met:ZipFile>{base64_zip}</met:ZipFile>
         <met:DeployOptions>
            <met:allowMissingFiles>false</met:allowMissingFiles>
            <met:autoUpdatePackage>false</met:autoUpdatePackage>
            <met:checkOnly>false</met:checkOnly>
            <met:ignoreWarnings>false</met:ignoreWarnings>
            <met:performRetrieve>false</met:performRetrieve>
            <met:purgeOnDelete>false</met:purgeOnDelete>
            <met:rollbackOnError>true</met:rollbackOnError>
            <met:singlePackage>true</met:singlePackage>
         </met:DeployOptions>
      </met:deploy>
   </soapenv:Body>
</soapenv:Envelope>
    """

    if b64 is None:
        print("Error: Base64 package data is None. Cannot deploy.")
        raise ValueError("Deployment failed: Invalid package data.")

    # Populate the template
    xml_body = xml_body_template.format(session_id=session_id, base64_zip=b64)

    # Log the request body (optional, good for debugging but might log session ID)
    # print(f"SOAP Request Body:\n{xml_body}")
    with open(f"{BASE_PATH}/deploy.log", "w", encoding="utf-8") as file:
        file.write(xml_body)

    try:
        response = requests.post(endpoint, data=xml_body, headers=headers)
        
        print(f"Deployment API Response Status: {response.status_code}")
        print(f"Deployment API Response Text:\n{response.text}")
        with open(f"{BASE_PATH}/deploy_http.log", "w", encoding="utf-8") as file:
            file.write(response.text)

        # --- Add Robust Error Checking --- 
        if response.status_code >= 400:
             # Try to parse for a SOAP fault message for better error reporting
             fault_message = f"HTTP Error {response.status_code}."
             try:
                 root = ET.fromstring(response.text)
                 # Look for soapenv:Fault (adjust namespace prefixes if needed)
                 fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
                 if fault is not None:
                     faultcode = fault.findtext('{*}faultcode')
                     faultstring = fault.findtext('{*}faultstring')
                     fault_message = f"SOAP Fault: Code='{faultcode}', Message='{faultstring}' (HTTP Status: {response.status_code})"
             except ET.ParseError:
                 fault_message += " Additionally, the response body was not valid XML." # Or just use raw text
             except Exception as parse_e:
                 print(f"Minor error parsing SOAP fault: {parse_e}") # Log parsing error but continue
                 fault_message += f" Response Text: {response.text[:500]}..." # Include snippet of raw text
             
             raise ValueError(f"Salesforce deployment API call failed: {fault_message}")
        # Add checks for specific deployment success/failure messages within the SOAP body if needed
        # For now, we assume non-error status code means the deployment was accepted (though it might fail asynchronously)
        print("Deployment request submitted successfully to Salesforce.")
        # --- End Error Checking --- 

    except requests.exceptions.RequestException as req_e:
         print(f"Network error during deployment API call: {req_e}")
         raise ValueError(f"Deployment failed: Network error contacting Salesforce API. Details: {str(req_e)}")
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"Unexpected error during deployment call: {e}")
        raise

def create_send_to_server(sf):
    """Zips the current package and sends it for deployment using the provided sf connection."""
    global current_package_dir
    if current_package_dir is None:
        raise ValueError("No package directory available for deployment")
    
    # Deploy both CustomApplication and Profile in a single package to avoid dependency issues
    # Update package.xml to include both CustomApplication and Profile
    package_xml = """<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Package xmlns=\"http://soap.sforce.com/2006/04/metadata\">\n    <types>\n        <members>*</members>\n        <name>CustomApplication</name>\n    </types>\n    <types>\n        <members>Admin</members>\n        <name>Profile</name>\n    </types>\n    <version>63.0</version>\n</Package>"""

    with open(os.path.join(current_package_dir, "package.xml"), "w", encoding="utf-8") as f:
        f.write(package_xml)

    # Ensure the profile XML has the correct API name and app visibility
    profiles_dir = os.path.join(current_package_dir, "profiles")
    profile_file = os.path.join(profiles_dir, "Admin.profile-meta.xml")

    # Get the app API name from the current app package
    # (Assume only one app in current/applications/)
    applications_dir = os.path.join(current_package_dir, "applications")
    app_api_name = None
    if os.path.exists(applications_dir):
        for fname in os.listdir(applications_dir):
            if fname.endswith(".app-meta.xml"):
                app_api_name = fname.replace(".app-meta.xml", "")
                break

    if not app_api_name:
        raise ValueError("Could not determine app API name for profile visibility update.")

    # Read the profile file
    if os.path.exists(profile_file):
        with open(profile_file, "r", encoding="utf-8") as f:
            profile_content = f.read()

        # Safeguard: Abort if placeholder is still present
        if "##api_name##" in profile_content:
            debug_path = os.path.join(BASE_PATH, "profile_debug.xml")
            with open(debug_path, "w", encoding="utf-8") as debug_f:
                debug_f.write(profile_content)
            raise ValueError(f"ABORTING DEPLOYMENT: Placeholder ##api_name## still present in Admin.profile-meta.xml. See {debug_path} for details.")

        # Prepare application visibility block
        app_vis_block = f"""    <applicationVisibilities>\n        <application>{app_api_name}</application>\n        <default>true</default>\n        <visible>true</visible>\n    </applicationVisibilities>\n"""
        # Add the block if not already present
        if f"<application>{app_api_name}</application>" not in profile_content:
            if "##applicationVisibilities##" in profile_content:
                profile_content = profile_content.replace("##applicationVisibilities##", app_vis_block)
            else:
                profile_content = profile_content.replace("</Profile>", f"{app_vis_block}</Profile>")

        with open(profile_file, "w", encoding="utf-8") as f:
            f.write(profile_content)

    # Deploy both CustomApplication and Profile in a single deployment
    zip_directory(current_package_dir)
    b64 = binary_to_base64(f"{BASE_PATH}/pack.zip")
    deploy(b64, sf)
    print("✅ Custom Application and Profile deployed together successfully")

def delete_send_to_server(sf):
    """Zips the current delete package and sends it for deployment using the provided sf connection."""
    global current_delete_dir
    if current_delete_dir is None:
        raise ValueError("No delete package directory available for deployment")
    
    zip_directory(current_delete_dir)
    b64 = binary_to_base64(f"{BASE_PATH}/pack.zip")
    deploy(b64, sf) # Pass sf connection

def create_report_package(report_info: dict):
    """Prepares the deployment package for a Salesforce report."""
    _clean_deploy_dir()

    report_name = report_info.get("report_name")
    folder_name = report_info.get("folder_name")
    report_type = report_info.get("report_type")
    columns = report_info.get("columns", [])
    filters = report_info.get("filters", [])
    groupings = report_info.get("groupings", [])

    write_to_file(f"Creating report package for: {report_name} in folder {folder_name}")

    # Paths
    assets_path = get_assets_path()
    source_tmpl_dir = os.path.join(assets_path, "create_report_tmpl")
    deploy_dir = os.path.join(BASE_PATH, DEPLOY_DIR)
    reports_dir = os.path.join(deploy_dir, "reports")
    package_tmpl = os.path.join(source_tmpl_dir, "package.xml")
    report_tmpl = os.path.join(source_tmpl_dir, "reports", "Template.report")

    # Copy template structure
    os.makedirs(deploy_dir, exist_ok=True)
    shutil.copytree(source_tmpl_dir, deploy_dir, dirs_exist_ok=True)
    write_to_file(f"Copied report template to {deploy_dir}")

    # Remove the template file itself to avoid parsing errors
    template_report_path = os.path.join(reports_dir, "Template.report")
    if os.path.exists(template_report_path):
        os.remove(template_report_path)
        write_to_file(f"Removed template report file: {template_report_path}")

    # Process package.xml
    with open(package_tmpl, "r", encoding="utf-8") as f:
        pkg = f.read()
    # Remove '.report' extension for package.xml members
    base_report_name = report_name[:-7] if report_name.endswith('.report') else report_name
    member_name = f"{folder_name}/{base_report_name}"
    pkg = pkg.replace("Template", member_name)
    with open(os.path.join(deploy_dir, "package.xml"), "w", encoding="utf-8") as f:
        f.write(pkg)
    write_to_file(f"Processed package.xml with member {member_name}")

    # Build report XML
    with open(report_tmpl, "r", encoding="utf-8") as f:
        rpt = f.read()
    # Ensure the <fullName> tag matches the folder and report name (no .report extension)
    base_name = report_name[:-7] if report_name.endswith('.report') else report_name
    full_name_value = f"{folder_name}/{base_name}"
    rpt = re.sub(r'<fullName>.*?</fullName>', f'<fullName>{full_name_value}</fullName>', rpt)
    # Detail columns XML (use <columns><field> for metadata API)
    cols_xml = "".join([
        f"    <columns>\n        <field>{c}</field>\n    </columns>\n"
        for c in columns
    ])
    # Filters XML: emit each filter as its own <reportFilters> block
    flt_full = "".join([
        f"    <reportFilters>\n"
        f"        <column>{filt['column']}</column>\n"
        f"        <operator>{filt['operator']}</operator>\n"
        f"        <value>{filt['value']}</value>\n"
        f"    </reportFilters>\n"
        for filt in filters
    ])
    rpt = rpt.replace("##report_filters##", flt_full)
    # Groupings XML
    grp_xml = "".join([f"        <groupingsDown><column>{g}</column></groupingsDown>\n" for g in groupings])
    rpt = rpt.replace("##groupings_down##", grp_xml)
    # Default empty sections
    rpt = rpt.replace("##aggregates##", "")
    rpt = rpt.replace("##buckets##", "")
    rpt = rpt.replace("##chart##", "")
    # Handle optional across groupings
    grp_across = "".join([f"    <groupingsAcross><field>{g}</field></groupingsAcross>\n" for g in report_info.get('groupings_across', [])])
    rpt = rpt.replace("##groupings_across##", grp_across)
    # Default format, scope, showDetails
    rpt = rpt.replace("##format##", report_info.get("format", "Tabular"))
    rpt = rpt.replace("##scope##", report_info.get("scope", "organization"))
    rpt = rpt.replace("##show_details##", str(report_info.get("show_details", True)).lower())
    # Time frame filter: include only if both column and interval are provided
    tf_col = report_info.get("time_frame_column")
    tf_int = report_info.get("time_frame_interval")
    if tf_col and tf_int:
        rpt = rpt.replace("##time_frame_column##", tf_col)
        rpt = rpt.replace("##time_frame_interval##", tf_int)
    else:
        # remove the entire timeFrameFilter block
        rpt = re.sub(r"\s*<timeFrameFilter>[\s\S]*?</timeFrameFilter>\n", "", rpt)

    # Ensure reports directory exists
    os.makedirs(reports_dir, exist_ok=True)
    # Create the folder subdirectory for this report
    report_folder_dir = os.path.join(reports_dir, folder_name)
    os.makedirs(report_folder_dir, exist_ok=True)
    # Determine the report filename (ensure it ends with .report)
    report_filename = report_name if report_name.endswith('.report') else f"{report_name}.report"
    final_path = os.path.join(report_folder_dir, report_filename)
    with open(final_path, "w", encoding="utf-8") as f:
        f.write(rpt)
    write_to_file(f"Wrote report file: {final_path}")

def deploy_package_from_deploy_dir(sf):
    """Zips the DEPLOY_DIR and deploys it via the Metadata API."""
    deploy_dir_path = os.path.join(BASE_PATH, DEPLOY_DIR)
    if not os.path.exists(deploy_dir_path):
        raise FileNotFoundError(f"Deployment directory not found: {deploy_dir_path}")

    # Zip only the contents of the deployment directory (no parent folder)
    zip_path = os.path.join(BASE_PATH, "deploy_package.zip")
    # Remove old zip if present
    if os.path.exists(zip_path):
        os.remove(zip_path)
    # Create new zip with contents at the root
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(deploy_dir_path):
            for file in files:
                abs_file = os.path.join(root, file)
                # Compute path relative to deploy_dir_path
                rel_path = os.path.relpath(abs_file, deploy_dir_path)
                zf.write(abs_file, rel_path)

    # Encode and deploy
    b64 = binary_to_base64(zip_path)
    deploy(b64, sf)

def deploy_object_package(sf):
    """Simple deployment for custom objects - no app-specific logic"""
    global current_package_dir
    if current_package_dir is None:
        raise ValueError("No package directory available for deployment. Package creation may have failed.")
    
    if not os.path.exists(current_package_dir):
        raise ValueError(f"Package directory does not exist: {current_package_dir}")
    
    # Simple deployment without app-specific logic
    zip_directory(current_package_dir)
    b64 = binary_to_base64(f"{BASE_PATH}/pack.zip")
    deploy(b64, sf)
    print("✅ Object package deployed successfully")

def deploy_tab_package(sf):
    """Simple deployment for custom tabs - no app-specific logic"""
    global current_package_dir
    if current_package_dir is None:
        raise ValueError("No package directory available for deployment")
    
    # Simple deployment without app-specific logic
    zip_directory(current_package_dir)
    b64 = binary_to_base64(f"{BASE_PATH}/pack.zip")
    deploy(b64, sf)
    print("✅ Tab package deployed successfully")

def create_report_folder_package(json_obj):
    """Prepares the deployment package for a new Salesforce report folder."""
    folder_api_name = json_obj.get('folder_api_name')
    folder_label = json_obj.get('folder_label')
    access_type = json_obj.get('access_type', 'Private')
    # Prepare directory
    _clean_deploy_dir()
    assets_path = get_assets_path()
    source_tmpl_dir = os.path.join(assets_path, 'create_report_folder_tmpl')
    deploy_dir = os.path.join(BASE_PATH, DEPLOY_DIR)
    reportFolders_dir = os.path.join(deploy_dir, 'reportFolders')
    # Copy template structure
    os.makedirs(deploy_dir, exist_ok=True)
    shutil.copytree(source_tmpl_dir, deploy_dir, dirs_exist_ok=True)
    # Process package.xml
    package_tmpl = os.path.join(source_tmpl_dir, 'package.xml')
    with open(package_tmpl, 'r', encoding='utf-8') as f:
        pkg = f.read()
    pkg = pkg.replace('Template', folder_api_name)
    with open(os.path.join(deploy_dir, 'package.xml'), 'w', encoding='utf-8') as f:
        f.write(pkg)
    # Process folder template
    tmpl_folder_file = os.path.join(source_tmpl_dir, 'reportFolders', 'Template.reportFolder')
    with open(tmpl_folder_file, 'r', encoding='utf-8') as f:
        cont = f.read()
    # Replace fullName and accessType
    cont = re.sub(r'<fullName>.*?</fullName>', f'<fullName>{folder_api_name}</fullName>', cont)
    cont = re.sub(r'<accessType>.*?</accessType>', f'<accessType>{access_type}</accessType>', cont)
    # Write final folder file
    os.makedirs(reportFolders_dir, exist_ok=True)
    final_file = os.path.join(reportFolders_dir, f'{folder_api_name}.reportFolder')
    with open(final_file, 'w', encoding='utf-8') as f:
        f.write(cont)
    print(f"Prepared report folder metadata at: {final_file}")

def create_profile_permissions_package(object_name: str, fields: list):
    """Creates a package to update the System Administrator profile with field permissions.
    Preserves existing permissions while adding new ones.
    
    Args:
        object_name (str): The API name of the object
        fields (list): List of field API names to grant permissions for
    """
    # Clean and prepare deploy directory
    _clean_deploy_dir()
    
    # Create profiles directory
    deploy_dir = os.path.join(BASE_PATH, DEPLOY_DIR)
    profiles_dir = os.path.join(deploy_dir, "profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    
    # Create package.xml
    package_xml = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Admin</members>
        <name>Profile</name>
    </types>
    <version>63.0</version>
</Package>"""
    
    with open(os.path.join(deploy_dir, "package.xml"), "w", encoding="utf-8") as f:
        f.write(package_xml)
    
    # Create new field permissions XML
    new_field_permissions = ""
    for field in fields:
        new_field_permissions += f"""    <fieldPermissions>
        <editable>true</editable>
        <field>{object_name}.{field}</field>
        <readable>true</readable>
    </fieldPermissions>
"""
    
    # Read the profile template
    profile_tmpl_path = os.path.join(get_assets_path(), "profile.tmpl")
    with open(profile_tmpl_path, "r", encoding="utf-8") as f:
        profile_template = f.read()
    
    # Replace the fieldPermissions placeholder with our new permissions
    profile_xml = profile_template.replace("##fieldPermissions##", new_field_permissions)
    
    # Write profile XML
    with open(os.path.join(profiles_dir, "Admin.profile"), "w", encoding="utf-8") as f:
        f.write(profile_xml)

def deploy_hardcoded_lightning_page(page_label="Simple Lightning App Page", description=""):
    """Creates a new Lightning Page with a unique name based on the provided label.
    
    Args:
        page_label (str): The label for the Lightning Page
        description (str): Optional description for the Lightning Page
    """
    try:
        _clean_deploy_dir()
        # Generate a unique API name from the label
        api_name = page_label.replace(" ", "_") + "_" + str(int(time.time()))
        
        assets_path = get_assets_path()
        asset_path = os.path.join(assets_path, "Flexipages", "HardcodedPage.flexipage")
        with open(asset_path, "r", encoding="utf-8") as asset_file:
            flexipage_xml = asset_file.read()
        
        # Replace the placeholders
        flexipage_xml = flexipage_xml.replace("##PAGE_LABEL##", page_label)
        flexipage_xml = flexipage_xml.replace("##PAGE_DESCRIPTION##", description)
        
        flexipage_dir = os.path.join(BASE_PATH, DEPLOY_DIR, "flexipages")
        os.makedirs(flexipage_dir, exist_ok=True)
        
        # Use the unique API name for the file
        flexipage_path = os.path.join(flexipage_dir, f"{api_name}.flexipage")
        with open(flexipage_path, "w", encoding="utf-8") as f:
            f.write(flexipage_xml)
            
        # Update package.xml to use the unique API name
        package_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>{api_name}</members>
        <name>FlexiPage</name>
    </types>
    <version>63.0</version>
</Package>'''
        
        package_path = os.path.join(BASE_PATH, DEPLOY_DIR, "package.xml")
        with open(package_path, "w", encoding="utf-8") as f:
            f.write(package_xml)
            
        write_to_file(f"Created new Lightning page with API name: {api_name}")
        return True
    except Exception as e:
        write_to_file(f"Error creating Lightning page package: {str(e)}")
        return False

if __name__ == "__main__":
    with open(f"{BASE_PATH}/mylog.txt", "r", encoding="utf-8") as file:
        exa = file.read()

    json_obj = json.loads(exa)

    delete_fields(json_obj)

    deploy_hardcoded_lightning_page(
        page_label="My Custom Page",
        description="This is a custom Lightning page for my application"
    )

