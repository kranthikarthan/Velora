#!/usr/bin/env python3
"""
Public-facing Velora Demo Server
Accessible from mobile devices on the same network
"""

import os
import socket
import subprocess
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def get_network_ip():
    """Get the machine's network IP address"""
    try:
        # Create a socket to determine the network IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "localhost"

def launch_public_server():
    """Launch the demo server accessible from network"""
    
    network_ip = get_network_ip()
    
    print("\n" + "="*70)
    print("🚀 VELORA DEMO - MOBILE ACCESS")
    print("="*70)
    
    print("\n📱 ACCESS FROM YOUR MOBILE DEVICE:")
    print("\n   Local Network Access:")
    print(f"   http://{network_ip}:8001")
    print(f"\n   Alternative:")
    print(f"   http://localhost:8001")
    
    print("\n" + "-"*70)
    print("📋 INSTRUCTIONS FOR MOBILE ACCESS:")
    print("-"*70)
    print("\n1. Make sure your mobile is on the SAME Wi-Fi network")
    print(f"2. Open your mobile browser")
    print(f"3. Type: http://{network_ip}:8001")
    print("4. Enjoy the interactive demo!")
    
    print("\n" + "-"*70)
    print("🌐 QR CODE FOR EASY ACCESS:")
    print("-"*70)
    
    # Generate QR code in terminal
    url = f"http://{network_ip}:8001"
    try:
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(url)
        qr.make()
        qr.print_ascii(invert=True)
    except ImportError:
        print(f"\n   URL: {url}")
        print("   (Install 'qrcode' package for QR code: pip install qrcode)")
    
    print("\n" + "="*70)
    print("✨ Server starting on all network interfaces...")
    print("="*70 + "\n")
    
    # Import and modify the standalone server to bind to all interfaces
    from demo.standalone_server import app
    import uvicorn
    
    # Run on all interfaces (0.0.0.0) to allow network access
    uvicorn.run(
        app, 
        host="0.0.0.0",  # This allows access from any network interface
        port=8001, 
        log_level="info"
    )

if __name__ == "__main__":
    launch_public_server()