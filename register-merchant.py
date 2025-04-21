#!/usr/bin/env python3
import os
import httpx
import sys
import uuid
from dotenv import load_dotenv
import argparse

# Load environment variables
load_dotenv()

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
API_URL = os.getenv("API_URL", "http://localhost:8000")

async def register_merchant(name, webhook_url):
    """
    Register a new merchant via the admin API
    """
    if not ADMIN_API_KEY:
        print("Error: ADMIN_API_KEY not set in environment")
        return False
    
    url = f"{API_URL}/admin/merchants"
    
    headers = {
        "admin-key": ADMIN_API_KEY,
        "Content-Type": "application/json"
    }
    
    params = {
        "name": name,
        "webhook_url": webhook_url
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, params=params, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                print("\nMerchant registered successfully:")
                print(f"Merchant ID: {result['merchant']['merchant_id']}")
                print(f"API Key: {result['merchant']['api_key']}")
                print(f"Default Wallet: {result['merchant']['default_wallet']}")
                print("\nIMPORTANT: Store this API key securely - it won't be shown again!")
                return True
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error registering merchant: {str(e)}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Register a new merchant")
    parser.add_argument("name", help="Merchant name")
    parser.add_argument("webhook_url", help="Webhook URL for payment notifications")
    
    args = parser.parse_args()
    
    import asyncio
    success = asyncio.run(register_merchant(args.name, args.webhook_url))
    
    if not success:
        sys.exit(1)
