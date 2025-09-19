# Deploying Salesforce MCP Server to Vercel

This guide will help you deploy your Salesforce MCP server to Vercel at [https://vercel.com/pablos-projects-f3f598d6/sfdcmcp](https://vercel.com/pablos-projects-f3f598d6/sfdcmcp).

## 🚀 Quick Deployment Steps

### 1. **Push Your Code to GitHub**
First, make sure all your changes are committed and pushed to your GitHub repository:

```bash
git add .
git commit -m "Add Vercel deployment configuration"
git push origin main
```

### 2. **Set Up Environment Variables in Vercel**
In your Vercel dashboard:

1. Go to **Settings** > **Environment Variables**
2. Add the following variables:

| Variable Name | Value | Environment |
|---------------|-------|-------------|
| `SF_USERNAME` | your-salesforce-username@example.com | Production |
| `SF_PASSWORD` | your-salesforce-password | Production |
| `SF_SECURITY_TOKEN` | your-security-token | Production |
| `SF_INSTANCE_URL` | https://login.salesforce.com (or your sandbox URL) | Production |
| `SF_SANDBOX` | false (or true for sandbox) | Production |

### 3. **Deploy to Vercel**
Your project should automatically deploy when you push to GitHub. If not:

1. Go to your Vercel dashboard
2. Click **Deployments**
3. Click **Redeploy** on the latest deployment

## 🔧 What Was Fixed

The original issue was that your MCP server wasn't following the **JSON-RPC 2.0 protocol** correctly. Here's what I fixed:

### ✅ **Before (Wrong Format):**
```json
{
  "protocolVersion": "2024-11-05",
  "capabilities": {"tools": {}},
  "serverInfo": {"name": "salesforce-mcp-vercel", "version": "1.0.0"}
}
```

### ✅ **After (Correct JSON-RPC Format):**
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {"tools": {}},
    "serverInfo": {"name": "salesforce-mcp-vercel", "version": "1.0.0"}
  }
}
```

### 🔨 **Key Changes Made:**

1. **Created `/api/mcp.py`** - Vercel-compatible HTTP endpoint
2. **Added proper JSON-RPC 2.0 wrapping** for all responses
3. **Fixed missing tool handlers** - Added handlers for all 10 defined tools
4. **Added error handling** with proper JSON-RPC error codes
5. **Created `vercel.json`** configuration
6. **Added `requirements.txt`** with all dependencies
7. **Fixed syntax error** in `definitions.py`

## 🧪 Testing Your Deployment

Once deployed, you can test your MCP server:

### **Test the Initialize Method:**
```bash
curl -X POST https://your-vercel-url.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "initialize",
    "id": 1,
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": {},
      "clientInfo": {"name": "test-client", "version": "1.0.0"}
    }
  }'
```

### **Test List Tools:**
```bash
curl -X POST https://your-vercel-url.vercel.app/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/list",
    "id": 2,
    "params": {}
  }'
```

## 📋 Available Tools

Your MCP server now supports all 10 tools:

### **Metadata Operations:**
- `create_object` - Create custom objects
- `delete_object_fields` - Delete fields from objects
- `create_tab` - Create custom tabs
- `create_custom_app` - Create Lightning applications

### **Data Operations:**
- `run_soql_query` - Execute SOQL queries
- `run_sosl_search` - Execute SOSL searches
- `get_object_fields` - Get object field metadata
- `create_record` - Create records
- `update_record` - Update records
- `delete_record` - Delete records

## 🔍 Troubleshooting

### **If deployment fails:**

1. **Check the build logs** in Vercel dashboard
2. **Verify environment variables** are set correctly
3. **Check Python version compatibility** (Vercel uses Python 3.9+)

### **If MCP client can't connect:**

1. **Verify the endpoint URL** is correct
2. **Check CORS headers** are properly set
3. **Test with curl** to isolate the issue

### **If Salesforce operations fail:**

1. **Verify SF credentials** in environment variables
2. **Check security token** is current
3. **Verify API access** for your Salesforce user

## 🎯 Next Steps

Your MCP server is now ready for production use with any MCP-compatible client! The JSON-RPC 2.0 protocol is properly implemented, so it will work with:

- **Claude Desktop** with MCP integration
- **Custom MCP clients**
- **Any JSON-RPC 2.0 compatible tool**

## 📞 Support

If you encounter any issues, check the Vercel function logs in your dashboard for detailed error messages.
