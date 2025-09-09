#!/usr/bin/env python3
"""
Velora Standalone Demo Server
Complete interactive demo with beautiful web UI
"""

import asyncio
import json
import random
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Set
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

# Initialize FastAPI
app = FastAPI(
    title="Velora Interactive Demo",
    description="AI Interoperability Layer - Banking Integration Demo",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass

manager = ConnectionManager()

# Transaction storage
transactions: List[Dict[str, Any]] = []
metrics = {
    "total_transactions": 0,
    "successful_transactions": 0,
    "failed_transactions": 0,
    "total_processing_time": 0,
    "min_latency": float('inf'),
    "max_latency": 0
}

# Serve the dashboard
@app.get("/")
async def serve_dashboard():
    """Serve the main dashboard"""
    dashboard_path = Path(__file__).parent / "dashboard" / "index.html"
    if dashboard_path.exists():
        return FileResponse(dashboard_path)
    else:
        # Return inline HTML if file doesn't exist
        return HTMLResponse(content=get_inline_dashboard())

@app.post("/api/process-payment")
async def process_payment(request: Request):
    """Process a payment transaction"""
    global metrics
    
    payment = await request.json()
    start_time = time.time()
    
    # Simulate processing steps
    await asyncio.sleep(0.1)  # REST parsing
    await asyncio.sleep(0.2)  # ISO 20022 conversion
    await asyncio.sleep(0.15)  # COBOL formatting
    await asyncio.sleep(0.3)  # CICS transaction
    await asyncio.sleep(0.1)  # Response formatting
    
    processing_time = int((time.time() - start_time) * 1000)
    
    # Generate transaction result
    transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
    auth_code = f"AUTH{random.randint(100000, 999999)}"
    
    # Update metrics
    metrics["total_transactions"] += 1
    metrics["successful_transactions"] += 1
    metrics["total_processing_time"] += processing_time
    metrics["min_latency"] = min(metrics["min_latency"], processing_time)
    metrics["max_latency"] = max(metrics["max_latency"], processing_time)
    
    # Store transaction
    transaction = {
        "transactionId": transaction_id,
        "authorizationCode": auth_code,
        "amount": payment.get("amount"),
        "currency": payment.get("currency"),
        "from": payment.get("debtorName"),
        "to": payment.get("creditorName"),
        "timestamp": datetime.utcnow().isoformat(),
        "processingTime": processing_time,
        "status": "completed"
    }
    transactions.append(transaction)
    
    # Broadcast metrics update
    await manager.broadcast(get_current_metrics())
    
    return {
        "success": True,
        "transactionId": transaction_id,
        "authorizationCode": auth_code,
        "status": "completed",
        "processingTime": processing_time,
        "details": {
            "iso20022_conversion": "15ms",
            "cobol_formatting": "10ms",
            "cics_execution": "80ms",
            "total": f"{processing_time}ms"
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    
    try:
        # Send initial metrics
        await websocket.send_json(get_current_metrics())
        
        while True:
            # Send periodic updates
            await asyncio.sleep(2)
            await websocket.send_json(get_current_metrics())
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/metrics")
async def get_metrics():
    """Get current system metrics"""
    return get_current_metrics()

@app.get("/api/transactions")
async def get_transactions():
    """Get recent transactions"""
    return transactions[-50:]  # Last 50 transactions

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time(),
        "version": "1.0.0"
    }

def get_current_metrics() -> Dict[str, Any]:
    """Calculate current metrics"""
    avg_latency = 0
    success_rate = 100
    
    if metrics["total_transactions"] > 0:
        avg_latency = int(metrics["total_processing_time"] / metrics["total_transactions"])
        success_rate = int((metrics["successful_transactions"] / metrics["total_transactions"]) * 100)
    
    return {
        "total_transactions": metrics["total_transactions"],
        "avg_latency": avg_latency,
        "success_rate": success_rate,
        "min_latency": metrics["min_latency"] if metrics["min_latency"] != float('inf') else 0,
        "max_latency": metrics["max_latency"],
        "active_protocols": 4,
        "timestamp": datetime.utcnow().isoformat()
    }

def get_inline_dashboard() -> str:
    """Return inline dashboard HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Velora Demo</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                margin: 0;
                padding: 20px;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                color: #1a202c;
                margin: 0 0 10px 0;
                font-size: 2.5em;
            }
            .subtitle {
                color: #718096;
                margin-bottom: 30px;
            }
            .status {
                display: inline-block;
                background: #48bb78;
                color: white;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 600;
                margin-bottom: 30px;
            }
            .demo-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .demo-card {
                background: #f7fafc;
                padding: 25px;
                border-radius: 12px;
                border: 2px solid #e2e8f0;
                transition: all 0.3s;
                cursor: pointer;
            }
            .demo-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                border-color: #667eea;
            }
            .demo-card h3 {
                color: #2d3748;
                margin: 0 0 10px 0;
                font-size: 1.3em;
            }
            .demo-card p {
                color: #718096;
                margin: 0 0 15px 0;
                line-height: 1.6;
            }
            .btn {
                background: #667eea;
                color: white;
                padding: 10px 20px;
                border-radius: 8px;
                text-decoration: none;
                display: inline-block;
                font-weight: 600;
                transition: all 0.3s;
            }
            .btn:hover {
                background: #5a67d8;
                transform: translateY(-2px);
            }
            .metrics {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                margin: 30px 0;
            }
            .metric {
                text-align: center;
                padding: 20px;
                background: #f7fafc;
                border-radius: 12px;
            }
            .metric-value {
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }
            .metric-label {
                color: #718096;
                margin-top: 5px;
                font-size: 0.9em;
            }
            .flow-diagram {
                background: #f7fafc;
                padding: 30px;
                border-radius: 12px;
                margin: 30px 0;
                text-align: center;
            }
            .flow-step {
                display: inline-block;
                background: white;
                padding: 15px 25px;
                border-radius: 8px;
                margin: 10px;
                border: 2px solid #e2e8f0;
                font-weight: 600;
                color: #2d3748;
            }
            .arrow {
                display: inline-block;
                color: #667eea;
                font-size: 1.5em;
                margin: 0 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Velora Interactive Demo</h1>
            <p class="subtitle">AI Interoperability Layer - Banking Integration</p>
            <div class="status">✓ System Online</div>
            
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
                <div class="metric">
                    <div class="metric-value" id="protocols">4</div>
                    <div class="metric-label">Active Protocols</div>
                </div>
            </div>
            
            <div class="flow-diagram">
                <h3>Protocol Translation Flow</h3>
                <div style="margin-top: 20px;">
                    <span class="flow-step">REST API</span>
                    <span class="arrow">→</span>
                    <span class="flow-step">ISO 20022</span>
                    <span class="arrow">→</span>
                    <span class="flow-step">COBOL</span>
                    <span class="arrow">→</span>
                    <span class="flow-step">CICS</span>
                    <span class="arrow">→</span>
                    <span class="flow-step">Mainframe</span>
                </div>
            </div>
            
            <div class="demo-grid">
                <div class="demo-card" onclick="testPayment()">
                    <h3>💳 Process Payment</h3>
                    <p>Submit a payment transaction through the complete legacy integration flow</p>
                    <a href="#" class="btn" onclick="event.preventDefault(); testPayment()">Try Now</a>
                </div>
                
                <div class="demo-card" onclick="showMetrics()">
                    <h3>📊 View Metrics</h3>
                    <p>Real-time performance metrics and system health monitoring</p>
                    <a href="#" class="btn" onclick="event.preventDefault(); showMetrics()">View</a>
                </div>
                
                <div class="demo-card" onclick="showAPI()">
                    <h3>🔌 API Explorer</h3>
                    <p>Interactive API documentation and testing interface</p>
                    <a href="/docs" class="btn">Explore</a>
                </div>
            </div>
            
            <div id="result" style="margin-top: 30px;"></div>
        </div>
        
        <script>
            // Connect to WebSocket
            let ws = null;
            
            function connectWebSocket() {
                ws = new WebSocket('ws://localhost:8001/ws');
                
                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    updateMetrics(data);
                };
                
                ws.onerror = function() {
                    setTimeout(connectWebSocket, 3000);
                };
            }
            
            function updateMetrics(data) {
                document.getElementById('transactions').textContent = data.total_transactions || 0;
                document.getElementById('latency').textContent = (data.avg_latency || 0) + 'ms';
                document.getElementById('success').textContent = (data.success_rate || 100) + '%';
                document.getElementById('protocols').textContent = data.active_protocols || 4;
            }
            
            async function testPayment() {
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '<div style="padding: 20px; background: #f7fafc; border-radius: 12px;">⏳ Processing payment...</div>';
                
                const payment = {
                    amount: 1500.00,
                    currency: 'USD',
                    debtorAccount: 'US12345678901234567890',
                    debtorName: 'John Smith',
                    creditorAccount: 'US98765432109876543210',
                    creditorName: 'ABC Corporation',
                    reference: 'DEMO-' + Date.now()
                };
                
                try {
                    const response = await fetch('/api/process-payment', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payment)
                    });
                    
                    const result = await response.json();
                    
                    resultDiv.innerHTML = `
                        <div style="padding: 20px; background: #c6f6d5; border-radius: 12px; border: 2px solid #48bb78;">
                            <h3 style="color: #22543d; margin: 0 0 10px 0;">✅ Payment Processed Successfully!</h3>
                            <p><strong>Transaction ID:</strong> ${result.transactionId}</p>
                            <p><strong>Authorization:</strong> ${result.authorizationCode}</p>
                            <p><strong>Processing Time:</strong> ${result.processingTime}ms</p>
                            <p><strong>Amount:</strong> $${payment.amount.toFixed(2)} ${payment.currency}</p>
                        </div>
                    `;
                } catch (error) {
                    resultDiv.innerHTML = `
                        <div style="padding: 20px; background: #fed7d7; border-radius: 12px; border: 2px solid #fc8181;">
                            <h3 style="color: #742a2a;">❌ Error</h3>
                            <p>${error.message}</p>
                        </div>
                    `;
                }
            }
            
            function showMetrics() {
                fetch('/api/metrics')
                    .then(response => response.json())
                    .then(data => updateMetrics(data));
            }
            
            function showAPI() {
                window.open('/docs', '_blank');
            }
            
            // Initialize
            connectWebSocket();
            showMetrics();
        </script>
    </body>
    </html>
    """

def run_demo():
    """Run the demo server"""
    print("\n" + "="*70)
    print("🚀 VELORA INTERACTIVE DEMO SERVER")
    print("="*70)
    print("\n✨ Starting beautiful web interface...\n")
    
    print("📊 Access Points:")
    print("   🌐 Dashboard:  http://localhost:8001")
    print("   📡 API Docs:   http://localhost:8001/docs")
    print("   🔌 WebSocket:  ws://localhost:8001/ws")
    print("\n" + "="*70)
    print("Ready! Open your browser to http://localhost:8001")
    print("="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="error")

if __name__ == "__main__":
    run_demo()