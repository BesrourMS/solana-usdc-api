# FastAPI Solana USDC Payment API Integration Guide

This guide provides instructions for merchants to integrate with our FastAPI-based Solana USDC payment API. This API allows you to accept USDC payments on the Solana blockchain with minimal setup.

## Getting Started

To use this API, you'll need to:
1. Register as a merchant
2. Obtain your API key
3. Implement the API in your application

## Authentication

All API requests must include your API key in the header:
```
X-API-Key: your_api_key_here
```

## API Endpoints

### Create a Payment

**Request:**
```http
POST /api/payments
Content-Type: application/json
X-API-Key: your_api_key_here

{
  "amount": 10.50,
  "payment_id": "order_123456",
  "metadata": {
    "customer_name": "John Doe",
    "product_id": "product_abc"
  }
}
```

**Response:**
```json
{
  "success": true,
  "payment": {
    "id": "6153f8d7-3e3a-4b12-9456-789012345678",
    "payment_id": "order_123456",
    "wallet_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "amount": 10.50,
    "status": "pending",
    "tx_signature": null,
    "created_at": "2025-04-21T14:32:27.000Z",
    "confirmed_at": null,
    "metadata": {
      "customer_name": "John Doe",
      "product_id": "product_abc"
    }
  }
}
```

### Check Payment Status

**Request:**
```http
GET /api/payments/order_123456
X-API-Key: your_api_key_here
```

**Response:**
```json
{
  "success": true,
  "payment": {
    "id": "6153f8d7-3e3a-4b12-9456-789012345678",
    "payment_id": "order_123456",
    "wallet_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "amount": 10.50,
    "status": "confirmed",
    "tx_signature": "5wHu1qwD4kPdBdwHZgFCnwuC4uMFp2GBWT8BdtX9nKLd291afUNiKz4fkMTBMQVNfrqXFtPgZKwUQGcRwXdUJD84",
    "created_at": "2025-04-21T14:32:27.000Z",
    "confirmed_at": "2025-04-21T14:35:12.000Z",
    "metadata": {
      "customer_name": "John Doe",
      "product_id": "product_abc"
    }
  }
}
```

### List Payments

**Request:**
```http
GET /api/payments?status=confirmed&limit=10&offset=0
X-API-Key: your_api_key_here
```

**Response:**
```json
{
  "success": true,
  "payments": [
    {
      "id": "6153f8d7-3e3a-4b12-9456-789012345678",
      "payment_id": "order_123456",
      "wallet_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "amount": 10.50,
      "status": "confirmed",
      "tx_signature": "5wHu1qwD4kPdBdwHZgFCnwuC4uMFp2GBWT8BdtX9nKLd291afUNiKz4fkMTBMQVNfrqXFtPgZKwUQGcRwXdUJD84",
      "created_at": "2025-04-21T14:32:27.000Z",
      "confirmed_at": "2025-04-21T14:35:12.000Z",
      "metadata": {
        "customer_name": "John Doe",
        "product_id": "product_abc"
      }
    }
    // Additional payments...
  ],
  "pagination": {
    "total": 45,
    "limit": 10,
    "offset": 0
  }
}
```

## Webhook Notifications

When a payment is confirmed, our system will send a webhook notification to the URL you specified during registration. The payload will be:

```json
{
  "event": "payment.confirmed",
  "payment": {
    "id": "6153f8d7-3e3a-4b12-9456-789012345678",
    "payment_id": "order_123456",
    "wallet_address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "amount": 10.50,
    "status": "confirmed",
    "tx_signature": "5wHu1qwD4kPdBdwHZgFCnwuC4uMFp2GBWT8BdtX9nKLd291afUNiKz4fkMTBMQVNfrqXFtPgZKwUQGcRwXdUJD84",
    "created_at": "2025-04-21T14:32:27.000Z",
    "confirmed_at": "2025-04-21T14:35:12.000Z",
    "metadata": {
      "customer_name": "John Doe",
      "product_id": "product_abc"
    }
  }
}
```

## Implementation Flow

1. Create a payment when your customer initiates checkout
2. Show the wallet address and amount to your customer
3. Wait for payment confirmation
   - Either poll the payment status endpoint
   - Or rely on webhook notifications
4. Update your order status once payment is confirmed

## Frontend Integration Example

Here's a simple example of how to integrate the payment flow in your frontend:

```javascript
// Example using JavaScript and Fetch API
async function createPayment(amount, orderId, metadata) {
  const response = await fetch('https://your-api-domain.com/api/payments', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your_api_key_here'
    },
    body: JSON.stringify({
      amount: amount,
      payment_id: orderId,
      metadata: metadata
    })
  });
  
  return await response.json();
}

// Create a payment
const payment = await createPayment(10.50, 'order_123456', {
  customer_name: 'John Doe',
  product_id: 'product_abc'
});

// Display payment information to customer
if (payment.success) {
  displayPaymentInfo(payment.payment);
}

// Function to display payment info
function displayPaymentInfo(payment) {
  // Show wallet address and amount to customer
  document.getElementById('wallet-address').innerText = payment.wallet_address;
  document.getElementById('amount').innerText = payment.amount;
  
  // Start polling for payment status
  const checkInterval = setInterval(async () => {
    const status = await checkPaymentStatus(payment.payment_id);
    if (status.payment.status === 'confirmed') {
      clearInterval(checkInterval);
      handleConfirmedPayment(status.payment);
    }
  }, 10000); // Check every 10 seconds
}

// Function to check payment status
async function checkPaymentStatus(paymentId) {
  const response = await fetch(`https://your-api-domain.com/api/payments/${paymentId}`, {
    headers: {
      'X-API-Key': 'your_api_key_here'
    }
  });
  
  return await response.json();
}

// Handle confirmed payment
function handleConfirmedPayment(payment) {
  // Update UI to show payment confirmation
  document.getElementById('payment-status').innerText = 'Payment Confirmed!';
  
  // Proceed with order fulfillment
  fulfillOrder(payment.payment_id);
}
```

## Solana Wallet Configuration

Your customers will need a Solana wallet with USDC tokens. They can use wallets like:
- Phantom
- Solflare
- Sollet

## Creating QR Codes for Payments

You can generate QR codes for Solana payments using the following format:

```javascript
// Example using JavaScript
function generatePaymentQR(address, amount) {
  const solanaPayUrl = `solana:${address}?amount=${amount}&spl-token=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v`;
  
  // Use any QR code library to generate the QR code
  // Example with qrcode.js:
  // QRCode.toCanvas(document.getElementById('qrcode'), solanaPayUrl);
  
  return solanaPayUrl;
}
```

## Test Environment

For testing, we recommend using Solana's devnet with devnet USDC tokens. Update your `.env` file to use the devnet RPC URL:

```
SOLANA_RPC_URL=https://api.devnet.solana.com
```

## Going Live

Before going live:
1. Test thoroughly on devnet
2. Update your `.env` configuration to use mainnet
3. Ensure your webhook endpoint is secure and reliable
4. Set up production MongoDB Atlas cluster with proper security settings
5. Implement proper key management for wallet private keys

## API Documentation

The complete API documentation is available at `/docs` when running the API server. This interactive documentation is automatically generated by FastAPI and allows you to test all endpoints directly from the browser.

## Support

For any issues or questions, please contact support at support@your-payment-service.com.
