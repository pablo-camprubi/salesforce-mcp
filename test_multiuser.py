#!/usr/bin/env python3
"""
Test script for multi-user Salesforce MCP functionality.

This script demonstrates how to:
1. Encrypt credentials for secure transmission
2. Test the multi-user MCP server with different credentials
3. Verify that each request can have its own credentials
"""

import json
import base64
import os
from cryptography.fernet import Fernet

# Add src to path to import our modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from salesforcemcp.sfdc_client import encrypt_credentials, decrypt_credentials, OrgHandler
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root and have installed dependencies")
    sys.exit(1)

def generate_encryption_key():
    """Generate a new encryption key for testing."""
    return Fernet.generate_key().decode()

def test_credential_encryption():
    """Test credential encryption and decryption."""
    print("🧪 Testing credential encryption/decryption...")
    
    # Generate a test encryption key
    encryption_key = generate_encryption_key()
    print(f"Generated encryption key: {encryption_key}")
    
    # Test credentials
    test_credentials = {
        "username": "test@example.com",
        "password": "testpassword",
        "security_token": "testsecuritytoken123"
    }
    
    try:
        # Encrypt the credentials
        encrypted_creds = encrypt_credentials(test_credentials, encryption_key)
        print(f"✅ Encryption successful")
        print(f"Encrypted credentials: {encrypted_creds[:50]}...")
        
        # Decrypt the credentials
        decrypted_creds = decrypt_credentials(encrypted_creds, encryption_key)
        print(f"✅ Decryption successful")
        print(f"Decrypted credentials: {decrypted_creds}")
        
        # Verify they match
        if test_credentials == decrypted_creds:
            print("✅ Encryption/decryption test passed!")
        else:
            print("❌ Encryption/decryption test failed - credentials don't match")
            
    except Exception as e:
        print(f"❌ Encryption/decryption test failed: {e}")

def test_multi_user_client():
    """Test creating multiple clients with different credentials."""
    print("\n🧪 Testing multi-user client creation...")
    
    # Test credentials for different "users"
    user1_creds = {
        "username": "user1@example.com", 
        "password": "password1",
        "security_token": "token1"
    }
    
    user2_creds = {
        "username": "user2@example.com",
        "password": "password2", 
        "security_token": "token2"
    }
    
    # Test creating clients (these will fail to connect but test the credential handling)
    print("\n👤 Testing User 1 client creation...")
    client1 = OrgHandler()
    result1 = client1.establish_connection(
        username=user1_creds["username"],
        password=user1_creds["password"],
        security_token=user1_creds["security_token"]
    )
    print(f"User 1 connection result: {result1} (Expected: False for test credentials)")
    
    print("\n👤 Testing User 2 client creation...")
    client2 = OrgHandler()
    result2 = client2.establish_connection(
        username=user2_creds["username"],
        password=user2_creds["password"], 
        security_token=user2_creds["security_token"]
    )
    print(f"User 2 connection result: {result2} (Expected: False for test credentials)")
    
    print("✅ Multi-user client creation test completed")

def test_encrypted_credentials():
    """Test the full encrypted credential workflow."""
    print("\n🧪 Testing encrypted credential workflow...")
    
    # Generate encryption key
    encryption_key = generate_encryption_key()
    print(f"Using encryption key for test")
    
    # Test credentials
    test_creds = {
        "username": "encrypted_user@example.com",
        "password": "encrypted_password",
        "security_token": "encrypted_token123"
    }
    
    try:
        # Encrypt credentials
        encrypted_creds = encrypt_credentials(test_creds, encryption_key)
        print("✅ Credentials encrypted successfully")
        
        # Test with OrgHandler
        client = OrgHandler()
        result = client.establish_connection_with_encrypted_credentials(
            encrypted_credentials=encrypted_creds,
            encryption_key=encryption_key
        )
        print(f"Encrypted credential connection result: {result} (Expected: False for test credentials)")
        print("✅ Encrypted credential workflow test completed")
        
    except Exception as e:
        print(f"❌ Encrypted credential test failed: {e}")

def generate_sample_request():
    """Generate a sample JSON-RPC request with encrypted credentials."""
    print("\n📝 Generating sample JSON-RPC request...")
    
    # Generate encryption key
    encryption_key = generate_encryption_key()
    
    # Sample credentials (these are fake, for demonstration only)
    sample_creds = {
        "username": "your_sf_username@company.com",
        "password": "your_sf_password",
        "security_token": "your_sf_security_token"
    }
    
    # Encrypt the credentials
    encrypted_creds = encrypt_credentials(sample_creds, encryption_key)
    
    # Create sample JSON-RPC request
    sample_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "run_soql_query",
            "arguments": {
                "query": "SELECT Id, Name FROM Account LIMIT 5"
            },
            "encrypted_credentials": encrypted_creds
        }
    }
    
    print("Sample JSON-RPC request with encrypted credentials:")
    print(json.dumps(sample_request, indent=2))
    print(f"\n🔑 Encryption key to use: {encryption_key}")
    print("📝 Set this as environment variable: ENCRYPTION_KEY")
    
    # Also show header-based approach
    print("\n📨 Alternative: Using HTTP headers")
    print(f"X-Salesforce-Encrypted-Credentials: {encrypted_creds}")
    
    return sample_request, encryption_key

def main():
    """Run all tests."""
    print("🚀 Salesforce MCP Multi-User Functionality Tests")
    print("=" * 60)
    
    # Test credential encryption
    test_credential_encryption()
    
    # Test multi-user clients
    test_multi_user_client()
    
    # Test encrypted credential workflow
    test_encrypted_credentials()
    
    # Generate sample request
    sample_request, encryption_key = generate_sample_request()
    
    print("\n" + "=" * 60)
    print("🎉 Multi-user testing completed!")
    print("\n📋 Next steps:")
    print("1. Set up your real Salesforce credentials")
    print("2. Set the ENCRYPTION_KEY environment variable")
    print("3. Test with real credentials using the sample request above")
    print("4. Deploy to Vercel and test the login popup integration!")

if __name__ == "__main__":
    main()
