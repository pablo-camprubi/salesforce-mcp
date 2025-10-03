# Multi-User Salesforce MCP Setup Guide

🎯 **The Salesforce MCP server has been successfully transformed from single-user hardcoded → true multi-user platform!**

## Overview

The Salesforce MCP server now supports:
- ✅ Dynamic user credentials per request
- ✅ Encrypted credentials for secure transmission  
- ✅ Multiple credential sources (headers, request params, environment variables)
- ✅ Per-request client creation (no shared state)
- ✅ Backward compatibility with existing environment variable setup

## Credential Sources Priority

The server accepts credentials in the following priority order:

1. **Encrypted credentials** - Most secure, recommended for production
2. **Plain credentials in request** - For development/testing
3. **HTTP headers** - For platform integration
4. **Environment variables** - Fallback for single-user setups

## Usage Examples

### 1. Using Encrypted Credentials (Recommended)

First, encrypt your credentials:

```python
from salesforcemcp.sfdc_client import encrypt_credentials

# Your Salesforce credentials
credentials = {
    "username": "your_username@company.com",
    "password": "your_password",
    "security_token": "your_security_token"
}

# Encrypt them (requires ENCRYPTION_KEY environment variable)
encrypted_creds = encrypt_credentials(credentials)
```

Then send the JSON-RPC request:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_soql_query",
    "arguments": {
      "query": "SELECT Id, Name FROM Account LIMIT 5"
    },
    "encrypted_credentials": "Z0FBQUFBQm8wcWRhSmIxUlJ..."
  }
}
```

### 2. Using HTTP Headers

Send credentials in HTTP headers:

```http
POST /api/mcp
Content-Type: application/json
X-Salesforce-Encrypted-Credentials: Z0FBQUFBQm8wcWRhSmIxUlJ...

{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_soql_query",
    "arguments": {
      "query": "SELECT Id, Name FROM Account LIMIT 5"
    }
  }
}
```

### 3. Using Plain Credentials (Development Only)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "run_soql_query",
    "arguments": {
      "query": "SELECT Id, Name FROM Account LIMIT 5"
    },
    "credentials": {
      "username": "your_username@company.com",
      "password": "your_password", 
      "security_token": "your_security_token"
    }
  }
}
```

## Environment Variables

### Required for Encrypted Credentials
- `ENCRYPTION_KEY` - Fernet encryption key for credential decryption

### Optional Fallbacks
- `USERNAME` - Salesforce username
- `PASSWORD` - Salesforce password
- `SECURITY_TOKEN` - Salesforce security token

## Security Features

### Encryption
- Uses Fernet (AES 128) encryption for credentials
- Base64 encoded for safe transmission
- Encryption key stored separately from encrypted data

### Per-Request Isolation  
- Each request creates its own Salesforce client
- No shared authentication state between requests
- Supports multiple users simultaneously

### Secure Headers
- `X-Salesforce-Credentials` - JSON credentials
- `X-Salesforce-Encrypted-Credentials` - Encrypted credentials

## Testing Your Setup

Use the provided test script:

```bash
python3 test_multiuser.py
```

This will:
- Test credential encryption/decryption
- Verify multi-user client creation
- Generate sample requests
- Validate the complete workflow

## Platform Integration

### Login Popup Integration
The multi-user setup enables beautiful login popups in your platform:

1. User clicks "Connect Salesforce" 
2. Platform shows Salesforce login form
3. Platform encrypts credentials securely
4. Encrypted credentials sent with each MCP request
5. Each user gets their own isolated Salesforce session

### Vercel Deployment
The server is ready for Vercel deployment at `https://salesforce-mcp.vercel.app` with full multi-user support.

## Migration from Single-User

Existing single-user setups continue to work unchanged. The server falls back to environment variables when no request-specific credentials are provided.

## Troubleshooting

### Common Issues

1. **"Encryption key not provided"**
   - Set the `ENCRYPTION_KEY` environment variable
   - Generate a key with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

2. **"Unable to establish Salesforce connection"**
   - Verify credentials are correct
   - Check security token (required for non-trusted IPs)
   - Ensure user account is active

3. **"Server not properly initialized"**
   - Verify all dependencies are installed: `pip install -r requirements.txt`
   - Check that modules import correctly

### Debug Endpoints

- `GET /health` - Check server status and configuration
- `POST /` with `health/check` method - Detailed health check with credentials

## Architecture Changes

### Before (Single-User)
```
Global sf_client → All requests use same connection
```

### After (Multi-User) 
```
Request → Extract credentials → Create client → Execute → Return result
```

Each request is completely isolated with its own authentication context.

---

🎉 **Ready to test? Try toggling Salesforce ON and see your beautiful login popup!** 🎯

