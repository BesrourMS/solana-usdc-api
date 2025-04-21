### 1. Prerequisites

- Python 3.9+
- MongoDB Atlas account
- Solana RPC node access (public or private)
- Basic understanding of Python and Solana blockchain

### 2. Setup Steps

1. **Create a MongoDB Atlas Cluster:**
   - Sign up/login to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Create a new cluster (free tier is fine for starting)
   - Set up a database user and whitelist your IP address
   - Get your connection string (it will look like `mongodb+srv://username:password@cluster0.mongodb.net/`)

2. **Clone the project and install dependencies:**
   ```bash
   git clone <your-repo>
   cd solana-usdc-fastapi
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables:**
   - Rename the `.env.example` file to `.env`
   - Update the `MONGODB_URI` value with your MongoDB Atlas connection string
   - Set a secure `ADMIN_API_KEY` for merchant registration

4. **Run the API:**
   ```bash
   uvicorn main:app --reload
   ```

5. **Register Your First Merchant:**
   ```bash
   python register_merchant.py "Your Store Name" "https://yourstore.com/webhook"
   ```

### 3. Key Features

- **FastAPI Framework:** High-performance, modern Python web framework
- **Asynchronous Design:** Uses async/await patterns for non-blocking operations
- **MongoDB Atlas Integration:** Cloud-based database for scalability
- **Interactive API Documentation:** Available at `/docs` endpoint
- **Solana Blockchain Integration:** For USDC token payments
- **Background Payment Monitoring:** Checks for incoming transactions
- **Webhook Notifications:** Alerts your system when payments are confirmed

### 4. Docker Deployment

For production deployment, you can use the provided Dockerfile:

```bash
docker build -t solana-usdc-api .
docker run -p 8000:8000 --env-file .env solana-usdc-api
```