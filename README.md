# Salesforce MCP Connector 🚀

**Must read -**
**This is not an official Salesforce repository.**


Welcome to the Salesforce Model Context Protocol server! 
This MCP allows you to interact with your Salesforce data and metadata using natural language.

Whether you're a business user, developer, or administrator, you can now chat with your Salesforce org to:
Get insights, Manage data, Configure the platform, create objects, fields, flows.. delete them, automate tasks and many more.

## Quick Start ⚡


https://github.com/user-attachments/assets/60c8a448-c953-4399-99b3-7c3a1c976aa7


### Option 1: Cloud Version (Recommended for Most Users) ☁️
1. Visit [salesforce-mcp.com](https://salesforce-mcp.com)
2. Click "Connect to Salesforce" and authenticate with your org
3. Start chatting with your Salesforce data right away, be aware that its not an official Salesforce product!

### Option 2: Local Version (Recommended for Developers) 💻
1. Follow the configuration steps below
2. Set up your environment variables
3. Use with your preferred MCP-compatible AI assistant

## What You Can Do?  ✨

 ## Work with your data

1. **Ask Questions About Your Data** 🔍
   - Get insights about your Salesforce records
   - Example: "Show me all accounts created in the last 30 days with their names and annual revenue"
   - The AI will automatically translate this into the appropriate Salesforce query

2. **Search Across Your Org** 🔎
   - Find information across all your Salesforce records
   - Example: "Find all records containing 'Acme' in any field"
   - Works like a powerful search engine for your Salesforce data

3. **Understand Your Data Structure** 📊
   - Explore available fields and objects
   - Example: "What fields are available on the Account object?"
   - Get a clear view of your data model

4. **Manage Your Records** 📝
   - Create, update, and delete records with natural language
   - Examples:
     - "Create a new Account named 'Acme Corp' with industry 'Technology'"
     - "Update the phone number of Account 001xx000003DIloAAG to '555-0123'"
     - "Delete the Account with ID 001xx000003DIloAAG"
     - "Create a new user"...

## Work with your Metadata

5. **Create objects and fields** 🛠️
   - Access and manage your Salesforce Object Manager
   - Example: "Create a new custom object named "Contract with 3 fields: Name, Id and type"
   - Perfect for developers and administrators

6. **Delete objects fields** 🔌
   - Interact with your custom Salesforce objects
   - Example: "Delete the field type from the Contract object"
   - Seamlessly integrate with your existing solutions

7. **Create custom tabs and apps** ⚙️
   - Connect to any Salesforce API endpoint
   - Example: "Get the describe information for the Account object"
   - Unlock the full power of the Salesforce platform

8. **In Progress: Expanding Capabilities** 🚀
   - We’re actively working on powerful new features to further streamline your Salesforce experience, including:
     1. Flow automation and orchestration
     2. Page Layouts
     3. Validation rules
     4. Reports and Dashboards
     5. Simplified deployments
     6. And many more...
     

## Configuration ⚙️

### For Local Installation

To use this connector locally, you'll need to configure it in your `claude_desktop_config.json` file. Add the following to the `mcpServers` section:

```json
{
    "mcpServers": {
        "salesforce": {
            "command": "uvx",
            "args": [
                "--from",
                "salesforce-mcp",
                "salesforce"
            ],
            "env": {
                "USERNAME": "YOUR_SALESFORCE_USERNAME",
                "PASSWORD": "YOUR_SALESFORCE_PASSWORD",
                "SECURITY_TOKEN": "YOUR_SALESFORCE_SECURITY_TOKEN"
            }
        }
    }
}
```

Replace the placeholder values with your Salesforce credentials:
- `YOUR_SALESFORCE_USERNAME`: Your Salesforce username
- `YOUR_SALESFORCE_PASSWORD`: Your Salesforce password
- `YOUR_SALESFORCE_SECURITY_TOKEN`: Your Salesforce security token

## Security Note 🔒

Your Salesforce credentials are stored securely and are only used to establish the connection to your org. We never store or share your credentials with third parties.

## Contributing 👋 

Thanks for being here! Whether you’re fixing a bug, adding a feature, or improving documentation — your help makes a big difference.

Here’s how to get started:

1. Check out our [Contributing Guidelines](CONTRIBUTING.md)
2. Take a look at the open [Issues](https://github.com/salesforce-mcp/Salesforce-mcp/issues)
3. Fork the repo and create your branch
4. Open a pull request when you’re ready

We appreciate your support and look forward to collaborating! 🚀

## Support 💬

Need help? Visit our [documentation](https://salesforce-mcp.com/docs) or contact our support team at support@salesforce-mcp.com or in our Discord channel

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
