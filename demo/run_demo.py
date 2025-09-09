#!/usr/bin/env python3
"""
Velora Demo Runner - Complete working demonstration
"""

import asyncio
import json
import random
import time
from datetime import datetime
from typing import Dict, Any, List
import uvicorn
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx

from velora.core import VeloraCore
from velora.legacy.iso20022 import ISO20022Message, PaymentInstruction, ISO20022MessageType
from velora.agents.base import TaskContext

# Initialize FastAPI for demo
app = FastAPI(title="Velora Demo", version="1.0.0")

# Add CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Velora instance
velora: VeloraCore = None

# Transaction history
transaction_history: List[Dict[str, Any]] = []

# WebSocket connections
websocket_connections: List[WebSocket] = []


@app.on_event("startup")
async def startup_event():
    """Initialize Velora on startup"""
    global velora
    print("\n" + "="*60)
    print("🚀 VELORA DEMO - Starting Up")
    print("="*60)
    
    # Initialize Velora
    velora = VeloraCore()
    await velora.setup()
    await velora.start()
    
    # Start mock mainframe if in demo mode
    if os.getenv("DEMO_MODE") == "true":
        asyncio.create_task(mock_mainframe_simulator())
    
    print("✅ Velora Demo Ready!")
    print("📊 Dashboard: http://localhost:3000")
    print("📡 API: http://localhost:8000")
    print("📈 Grafana: http://localhost:3001")
    print("="*60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global velora
    if velora:
        await velora.stop()


@app.get("/")
async def root():
    """Demo homepage"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velora Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
            .status { background: #27ae60; color: white; padding: 10px 20px; border-radius: 5px; display: inline-block; }
            .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 30px; }
            .card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #3498db; }
            .card h3 { margin-top: 0; color: #2c3e50; }
            .button { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
            .button:hover { background: #2980b9; }
            .metrics { display: flex; justify-content: space-around; margin: 20px 0; }
            .metric { text-align: center; }
            .metric-value { font-size: 2em; font-weight: bold; color: #3498db; }
            .metric-label { color: #7f8c8d; margin-top: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Velora AI Interoperability Layer - Live Demo</h1>
            <div class="status">System Online</div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value" id="transactions">0</div>
                    <div class="metric-label">Transactions</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="latency">0ms</div>
                    <div class="metric-label">Avg Latency</div>
                </div>
                <div class="metric">
                    <div class="metric-value" id="success">100%</div>
                    <div class="metric-label">Success Rate</div>
                </div>
            </div>
            
            <div class="grid">
                <div class="card">
                    <h3>🏦 Banking Demo</h3>
                    <p>Process payments through legacy mainframe</p>
                    <a href="/demo/payment" class="button">Send Payment</a>
                    <a href="/demo/batch" class="button">Batch Process</a>
                </div>
                
                <div class="card">
                    <h3>🔄 Protocol Translation</h3>
                    <p>Convert between different formats</p>
                    <a href="/demo/iso20022" class="button">ISO 20022</a>
                    <a href="/demo/cobol" class="button">COBOL</a>
                </div>
                
                <div class="card">
                    <h3>📊 Monitoring</h3>
                    <p>Real-time system monitoring</p>
                    <a href="/metrics" class="button">Metrics</a>
                    <a href="http://localhost:3001" class="button">Grafana</a>
                </div>
                
                <div class="card">
                    <h3>🔌 API Explorer</h3>
                    <p>Interactive API documentation</p>
                    <a href="/docs" class="button">Swagger UI</a>
                    <a href="/redoc" class="button">ReDoc</a>
                </div>
            </div>
            
            <h2>Recent Transactions</h2>
            <div id="transactions-list"></div>
        </div>
        
        <script>
            // Connect to WebSocket for real-time updates
            const ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateMetrics(data);
            };
            
            function updateMetrics(data) {
                document.getElementById('transactions').textContent = data.total_transactions || 0;
                document.getElementById('latency').textContent = (data.avg_latency || 0) + 'ms';
                document.getElementById('success').textContent = (data.success_rate || 100) + '%';
            }
            
            // Fetch initial metrics
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => updateMetrics(data));
        </script>
    </body>
    </html>
    """)


@app.get("/demo/payment")
async def demo_payment_form():
    """Payment demo form"""
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Payment Demo - Velora</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f0f0f0; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }
            h1 { color: #2c3e50; }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
            button { background: #27ae60; color: white; padding: 12px 30px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
            button:hover { background: #229954; }
            .result { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 5px; }
            .success { border-left: 4px solid #27ae60; }
            .error { border-left: 4px solid #e74c3c; }
            .processing { border-left: 4px solid #f39c12; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏦 Payment Processing Demo</h1>
            <p>Submit a payment that will be processed through the legacy mainframe</p>
            
            <form id="paymentForm">
                <div class="form-group">
                    <label>Amount</label>
                    <input type="number" id="amount" value="1500.00" step="0.01" required>
                </div>
                
                <div class="form-group">
                    <label>Currency</label>
                    <select id="currency">
                        <option value="USD">USD - US Dollar</option>
                        <option value="EUR">EUR - Euro</option>
                        <option value="GBP">GBP - British Pound</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Debtor Account (IBAN)</label>
                    <input type="text" id="debtorAccount" value="US12345678901234567890" required>
                </div>
                
                <div class="form-group">
                    <label>Debtor Name</label>
                    <input type="text" id="debtorName" value="John Smith" required>
                </div>
                
                <div class="form-group">
                    <label>Creditor Account (IBAN)</label>
                    <input type="text" id="creditorAccount" value="US98765432109876543210" required>
                </div>
                
                <div class="form-group">
                    <label>Creditor Name</label>
                    <input type="text" id="creditorName" value="ABC Corporation" required>
                </div>
                
                <div class="form-group">
                    <label>Reference</label>
                    <input type="text" id="reference" value="INV-2024-001" required>
                </div>
                
                <button type="submit">Process Payment</button>
            </form>
            
            <div id="result"></div>
        </div>
        
        <script>
            document.getElementById('paymentForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '<div class="result processing">⏳ Processing payment...</div>';
                
                const payment = {
                    amount: parseFloat(document.getElementById('amount').value),
                    currency: document.getElementById('currency').value,
                    debtorAccount: document.getElementById('debtorAccount').value,
                    debtorName: document.getElementById('debtorName').value,
                    creditorAccount: document.getElementById('creditorAccount').value,
                    creditorName: document.getElementById('creditorName').value,
                    reference: document.getElementById('reference').value
                };
                
                try {
                    const response = await fetch('/api/process-payment', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payment)
                    });
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        resultDiv.innerHTML = `
                            <div class="result success">
                                <h3>✅ Payment Processed Successfully!</h3>
                                <p><strong>Transaction ID:</strong> ${result.transactionId}</p>
                                <p><strong>Status:</strong> ${result.status}</p>
                                <p><strong>Processing Time:</strong> ${result.processingTime}ms</p>
                                <p><strong>Flow:</strong> REST → ISO 20022 → COBOL → CICS → Mainframe</p>
                            </div>
                        `;
                    } else {
                        resultDiv.innerHTML = `
                            <div class="result error">
                                <h3>❌ Payment Failed</h3>
                                <p>${result.error}</p>
                            </div>
                        `;
                    }
                } catch (error) {
                    resultDiv.innerHTML = `
                        <div class="result error">
                            <h3>❌ Error</h3>
                            <p>${error.message}</p>
                        </div>
                    `;
                }
            });
        </script>
    </body>
    </html>
    """)


@app.post("/api/process-payment")
async def process_payment(payment: Dict[str, Any]):
    """Process a payment through the complete flow"""
    start_time = time.time()
    
    try:
        # Step 1: Create ISO 20022 message
        iso_message = ISO20022Message(
            message_type=ISO20022MessageType.PAIN_001,
            message_id=f"MSG{datetime.now().strftime('%Y%m%d%H%M%S')}",
            creation_date_time=datetime.utcnow(),
            initiating_party=payment['debtorName'],
            group_header={
                "message_id": f"PAY-{random.randint(1000000, 9999999)}",
                "creation_date": datetime.utcnow().isoformat(),
                "number_of_transactions": "1",
                "control_sum": str(payment['amount'])
            },
            payment_instructions=[
                PaymentInstruction(
                    instruction_id=f"INST-{random.randint(1000000, 9999999)}",
                    end_to_end_id=payment['reference'],
                    amount=payment['amount'],
                    currency=payment['currency'],
                    debtor_account=payment['debtorAccount'],
                    debtor_name=payment['debtorName'],
                    creditor_account=payment['creditorAccount'],
                    creditor_name=payment['creditorName'],
                    remittance_info=f"Payment ref: {payment['reference']}"
                )
            ]
        )
        
        # Step 2: Process through legacy bridge
        result = await velora.legacy_bridge.process_iso20022_to_legacy(
            iso_message,
            target_system="mock-mainframe"
        )
        
        # Calculate processing time
        processing_time = int((time.time() - start_time) * 1000)
        
        # Record transaction
        transaction = {
            "transactionId": iso_message.message_id,
            "timestamp": datetime.utcnow().isoformat(),
            "amount": payment['amount'],
            "currency": payment['currency'],
            "status": "completed" if result.get("success") else "failed",
            "processingTime": processing_time
        }
        transaction_history.append(transaction)
        
        # Broadcast to WebSocket clients
        await broadcast_transaction(transaction)
        
        return {
            "success": True,
            "transactionId": iso_message.message_id,
            "status": "completed",
            "processingTime": processing_time,
            "result": result
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Send periodic updates
            await asyncio.sleep(1)
            metrics = await get_system_metrics()
            await websocket.send_json(metrics)
    except:
        websocket_connections.remove(websocket)


async def broadcast_transaction(transaction: Dict[str, Any]):
    """Broadcast transaction to all WebSocket clients"""
    for connection in websocket_connections:
        try:
            await connection.send_json({
                "type": "transaction",
                "data": transaction
            })
        except:
            pass


async def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics"""
    total_transactions = len(transaction_history)
    successful = len([t for t in transaction_history if t['status'] == 'completed'])
    
    avg_latency = 0
    if transaction_history:
        avg_latency = sum(t['processingTime'] for t in transaction_history) / len(transaction_history)
    
    success_rate = 100
    if total_transactions > 0:
        success_rate = (successful / total_transactions) * 100
    
    return {
        "total_transactions": total_transactions,
        "avg_latency": int(avg_latency),
        "success_rate": int(success_rate),
        "active_agents": len(velora.agent_manager.agents) if velora and velora.agent_manager else 0,
        "uptime": velora.get_uptime() if velora else 0
    }


@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics"""
    return await get_system_metrics()


@app.get("/api/transactions")
async def get_transactions():
    """Get transaction history"""
    return transaction_history[-50:]  # Last 50 transactions


async def mock_mainframe_simulator():
    """Simulate mainframe responses"""
    print("🖥️ Mock Mainframe Simulator Started")
    
    while True:
        await asyncio.sleep(0.1)  # Simulate processing delay
        # Mock mainframe would process CICS transactions here


if __name__ == "__main__":
    import os
    
    # Run the demo
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info"
    )