# main.py
from fastapi import FastAPI, Header, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import os
import base58
import httpx
import motor.motor_asyncio
from dotenv import load_dotenv
from solana.rpc.async_api import AsyncClient
from solana.publickey import PublicKey
from solders.keypair import Keypair
import time

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Solana USDC Payment API",
    description="API for accepting USDC payments on Solana blockchain",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI")
client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
db = client.solana_payments

# Solana connection
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
solana_client = AsyncClient(SOLANA_RPC_URL)

# USDC token on Solana (mainnet)
USDC_MINT = PublicKey("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")

# Pydantic models
class PaymentRequest(BaseModel):
    amount: float = Field(..., gt=0)
    payment_id: str = Field(...)
    metadata: Optional[Dict[str, Any]] = None

class Payment(BaseModel):
    id: str
    payment_id: str
    wallet_address: str
    amount: float
    status: str
    tx_signature: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

class PaymentResponse(BaseModel):
    success: bool
    payment: Payment

class PaymentListResponse(BaseModel):
    success: bool
    payments: List[Payment]
    pagination: Dict[str, int]

class WebhookPayload(BaseModel):
    event: str
    payment: Payment

# Authentication middleware
async def authenticate_merchant(x_api_key: str = Header(...)):
    merchant = await db.merchants.find_one({"api_key": x_api_key})
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return merchant

# Generate a new keypair for receiving payments
def generate_payment_wallet():
    return Keypair()

# Utility to convert from/to public key string
def public_key_to_str(public_key):
    return str(public_key)

def str_to_public_key(public_key_str):
    return PublicKey(public_key_str)

# Routes
@app.post("/api/payments", response_model=PaymentResponse)
async def create_payment(
    payment_req: PaymentRequest,
    background_tasks: BackgroundTasks,
    merchant: dict = Depends(authenticate_merchant)
):
    # Generate new wallet for this payment
    payment_wallet = generate_payment_wallet()
    wallet_address = public_key_to_str(payment_wallet.pubkey())
    
    # Store wallet's private key securely (in production, use a more secure method)
    # Here we're just encoding it to save in our database
    private_key_encoded = base58.b58encode(bytes(payment_wallet.secret_key)).decode('ascii')

    # Create unique ID
    payment_id_internal = str(uuid.uuid4())
    
    # Create transaction record
    now = datetime.utcnow()
    transaction = {
        "id": payment_id_internal,
        "merchant_id": merchant["merchant_id"],
        "payment_id": payment_req.payment_id,
        "wallet_address": wallet_address,
        "wallet_private_key": private_key_encoded,  # In production, encrypt this
        "amount": payment_req.amount,
        "status": "pending",
        "tx_signature": None,
        "created_at": now, 
        "confirmed_at": None,
        "metadata": payment_req.metadata
    }
    
    # Insert into MongoDB
    await db.transactions.insert_one(transaction)
    
    payment = Payment(
        id=payment_id_internal,
        payment_id=payment_req.payment_id,
        wallet_address=wallet_address,
        amount=payment_req.amount,
        status="pending",
        created_at=now,
        metadata=payment_req.metadata
    )
    
    return PaymentResponse(success=True, payment=payment)

@app.get("/api/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    merchant: dict = Depends(authenticate_merchant)
):
    transaction = await db.transactions.find_one({
        "payment_id": payment_id,
        "merchant_id": merchant["merchant_id"]
    })
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    payment = Payment(
        id=transaction["id"],
        payment_id=transaction["payment_id"],
        wallet_address=transaction["wallet_address"],
        amount=transaction["amount"],
        status=transaction["status"],
        tx_signature=transaction.get("tx_signature"),
        created_at=transaction["created_at"],
        confirmed_at=transaction.get("confirmed_at"),
        metadata=transaction.get("metadata")
    )
    
    return PaymentResponse(success=True, payment=payment)

@app.get("/api/payments", response_model=PaymentListResponse)
async def list_payments(
    status: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    merchant: dict = Depends(authenticate_merchant)
):
    query = {"merchant_id": merchant["merchant_id"]}
    if status:
        query["status"] = status
    
    # Get total count
    total = await db.transactions.count_documents(query)
    
    # Get paginated results
    cursor = db.transactions.find(query).sort("created_at", -1).skip(offset).limit(limit)
    transactions = await cursor.to_list(length=limit)
    
    payments = []
    for tx in transactions:
        payments.append(Payment(
            id=tx["id"],
            payment_id=tx["payment_id"],
            wallet_address=tx["wallet_address"],
            amount=tx["amount"],
            status=tx["status"],
            tx_signature=tx.get("tx_signature"),
            created_at=tx["created_at"],
            confirmed_at=tx.get("confirmed_at"),
            metadata=tx.get("metadata")
        ))
    
    return PaymentListResponse(
        success=True,
        payments=payments,
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset
        }
    )

# Background tasks
async def send_webhook_to_merchant(transaction: dict):
    try:
        merchant = await db.merchants.find_one({"merchant_id": transaction["merchant_id"]})
        
        if not merchant or not merchant.get("webhook_url"):
            return
        
        # Create webhook payload
        payload = WebhookPayload(
            event="payment.confirmed",
            payment=Payment(
                id=transaction["id"],
                payment_id=transaction["payment_id"],
                wallet_address=transaction["wallet_address"],
                amount=transaction["amount"],
                status=transaction["status"],
                tx_signature=transaction.get("tx_signature"),
                created_at=transaction["created_at"],
                confirmed_at=transaction.get("confirmed_at"),
                metadata=transaction.get("metadata")
            )
        )
        
        # Send webhook
        async with httpx.AsyncClient() as client:
            await client.post(
                merchant["webhook_url"],
                json=payload.dict(),
                headers={"Content-Type": "application/json"}
            )
    except Exception as e:
        print(f"Error sending webhook for {transaction['id']}: {str(e)}")

# Admin endpoints for merchant management
@app.post("/admin/merchants")
async def create_merchant(
    name: str,
    webhook_url: str,
    admin_key: str = Header(...)
):
    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    # Generate merchant ID
    merchant_id = f"MERCH_{uuid.uuid4().hex[:8]}"
    
    # Generate API key
    api_key = uuid.uuid4().hex
    
    # Generate default receiving wallet
    default_wallet = generate_payment_wallet()
    default_wallet_address = public_key_to_str(default_wallet.pubkey())
    default_wallet_private_key = base58.b58encode(bytes(default_wallet.secret_key)).decode('ascii')
    
    # Create merchant record
    merchant = {
        "merchant_id": merchant_id,
        "name": name,
        "api_key": api_key,
        "webhook_url": webhook_url,
        "default_wallet": default_wallet_address,
        "default_wallet_private_key": default_wallet_private_key,  # In production, encrypt this
        "created_at": datetime.utcnow()
    }
    
    await db.merchants.insert_one(merchant)
    
    # Return merchant info (exclude the private key in response)
    merchant_response = {k: v for k, v in merchant.items() if k != "default_wallet_private_key"}
    return {"success": True, "merchant": merchant_response}

# Task to check for payments on pending transactions
@app.on_event("startup")
async def start_payment_listener():
    # In a production app, this would be a separate microservice or worker
    # Here we'll just create a background task
    async def payment_listener():
        while True:
            try:
                # Get all pending transactions
                cursor = db.transactions.find({"status": "pending"})
                pending_txs = await cursor.to_list(length=100)
                
                for tx in pending_txs:
                    # Check if payment was received
                    await check_payment_received(tx)
                    
                # Wait before next check
                await asyncio.sleep(15)
            except Exception as e:
                print(f"Error in payment listener: {str(e)}")
                await asyncio.sleep(30)  # Wait longer after error
    
    import asyncio
    asyncio.create_task(payment_listener())

async def check_payment_received(transaction: dict):
    try:
        wallet_public_key = str_to_public_key(transaction["wallet_address"])
        
        # Get token accounts for the USDC token
        response = await solana_client.get_token_accounts_by_owner(
            wallet_public_key,
            {"mint": USDC_MINT}
        )
        
        # If no token account exists yet, payment not received
        accounts = response.value
        if not accounts:
            return
        
        # Check balance of first account
        account_pubkey = str_to_public_key(accounts[0].pubkey)
        account_info = await solana_client.get_token_account_balance(account_pubkey)
        
        # USDC has 6 decimals
        usdc_amount = float(account_info.value.ui_amount)
        
        if usdc_amount >= transaction["amount"]:
            # Update transaction status
            now = datetime.utcnow()
            await db.transactions.update_one(
                {"id": transaction["id"]},
                {"$set": {
                    "status": "confirmed",
                    "confirmed_at": now
                }}
            )
            
            # Get updated transaction
            updated_tx = await db.transactions.find_one({"id": transaction["id"]})
            
            # Send webhook to merchant
            await send_webhook_to_merchant(updated_tx)
            
            # In production, you would now transfer funds to main wallet
            # await transfer_funds_to_main_wallet(transaction)
    except Exception as e:
        print(f"Error checking payment for {transaction['id']}: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
