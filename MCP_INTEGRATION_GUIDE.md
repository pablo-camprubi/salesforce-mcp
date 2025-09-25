# 🔐 Salesforce MCP Server - Integration Guide

## Server Details
- **URL**: `https://salesforce-mcp.vercel.app`
- **Protocol**: JSON-RPC 2.0 over HTTP/HTTPS  
- **Tools Available**: 24 (including Einstein AI)
- **Authentication**: Per-request encrypted credentials

## 🔐 Credential Format

### Option 1: Encrypted Credentials (Recommended)
```javascript
// In tool call arguments:
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "create_object", 
    "arguments": {
      "_sf_encrypted_credentials": "eyJ1c2VybmFtZSI6InVzZXJAZXhhbXBsZS5jb20iLCJwYXNzd29yZCI6InBhc3MiLCJzZWN1cml0eV90b2tlbiI6InRva2VuIn0=",
      // ... other tool arguments
    }
  }
}
```

**Encryption Method**: Base64 encoding of JSON
```javascript
const credentials = {
  username: "user@salesforce.com",
  password: "userPassword", 
  security_token: "userSecurityToken"  // Optional if using trusted IP
};
const encrypted = Buffer.from(JSON.stringify(credentials)).toString('base64');
```

### Option 2: Plain Credentials (Alternative)
```javascript
{
  "jsonrpc": "2.0",
  "id": 1, 
  "method": "tools/call",
  "params": {
    "name": "create_object",
    "arguments": {
      "_sf_credentials": {
        "username": "user@salesforce.com",
        "password": "userPassword",
        "security_token": "userSecurityToken"
      },
      // ... other tool arguments
    }
  }
}
```

### Option 3: HTTP Headers (Alternative)
```http
POST / HTTP/1.1
Host: salesforce-mcp.vercel.app
Content-Type: application/json
X-Salesforce-Encrypted-Credentials: eyJ1c2VybmFtZSI6InVzZXJAZXhhbXBsZS5jb20i...

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call", 
  "params": {
    "name": "create_object",
    "arguments": {
      // tool arguments without credentials
    }
  }
}
```

## 📡 Injection Method

**✅ Per-Request Authentication**: Credentials are provided with EACH tool call
- No persistent connection or session required
- Each request is independently authenticated
- Supports true multi-user scenarios

**❌ NOT Session-Based**: No initial handshake or connection setup needed

## 🔓 Server-Side Decryption

The server handles decryption automatically:

1. **Priority Order** (server tries in this order):
   - `arguments._sf_encrypted_credentials` (Base64 JSON)
   - `arguments._sf_credentials` (Plain JSON object)  
   - `X-Salesforce-Encrypted-Credentials` header
   - `X-Salesforce-Credentials` header
   - Environment variables (fallback)

2. **Decryption Process**:
   ```javascript
   // Server-side (you don't need to implement this)
   const decrypted = JSON.parse(Buffer.from(encrypted_creds, 'base64').toString('utf-8'));
   const sf_client = new SalesforceClient(decrypted.username, decrypted.password, decrypted.security_token);
   ```

## 🛠️ Available Tools

### Core Salesforce Tools (23)
- `create_object` - Create custom objects
- `create_tab` - Create custom tabs  
- `create_custom_app` - Create Lightning apps
- `run_soql_query` - Execute SOQL queries
- `create_record` - Create Salesforce records
- `update_record` - Update records
- `delete_record` - Delete records
- ... and 16 more

### 🧠 Einstein AI Tools (1)
- `create_einstein_model` - Create Einstein Studio ML models

## 📊 Example Integration

### Test Connection
```javascript
const response = await fetch('https://salesforce-mcp.vercel.app', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list',
    params: {}
  })
});
const data = await response.json();
console.log(`${data.result.tools.length} tools available`); // Should show 24
```

### Create Einstein AI Model
```javascript
const credentials = {
  username: "user@salesforce.com",
  password: "password",
  security_token: "token123"
};
const encrypted = Buffer.from(JSON.stringify(credentials)).toString('base64');

const response = await fetch('https://salesforce-mcp.vercel.app', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/call',
    params: {
      name: 'create_einstein_model',
      arguments: {
        _sf_encrypted_credentials: encrypted,
        model_name: 'Lead_Conversion_Predictor',
        description: 'Predicts lead conversion likelihood', 
        outcome_field: 'Converted__c',
        data_source: 'Lead_Training__dlm',
        fields: [
          {field_name: 'Industry__c', field_label: 'Industry', field_type: 'Text', data_type: 'Categorical'},
          {field_name: 'Lead_Score__c', field_label: 'Lead Score', field_type: 'Number', data_type: 'Numerical'}
        ]
      }
    }
  })
});
```

## ❓ FAQ

**Q: Do I need special encryption?**  
A: No, just Base64 encoding of JSON credentials.

**Q: Is there session management?**  
A: No, each request is independently authenticated.

**Q: What if credentials are invalid?**  
A: Server returns error with connection failure details.

**Q: Can I test without credentials?**  
A: Yes, `tools/list` works without credentials. Individual tools need auth.

**Q: Is this production ready?**  
A: Yes! Deployed on Vercel with full multi-user support.

## 📞 Contact

For integration questions: Use this GitHub repo or test directly against the API!
