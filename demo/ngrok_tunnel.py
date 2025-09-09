#!/usr/bin/env python3
"""
Create a public tunnel for the Velora demo
This uses localtunnel as a fallback solution
"""

import subprocess
import sys
import time
import re

def create_tunnel():
    """Create a public tunnel to the demo server"""
    print("\n" + "="*70)
    print("🌐 CREATING PUBLIC TUNNEL FOR MOBILE ACCESS")
    print("="*70 + "\n")
    
    # Check if the demo server is running
    try:
        import requests
        response = requests.get("http://localhost:8001/api/health", timeout=2)
        if response.status_code != 200:
            print("⚠️  Demo server not responding properly")
            print("Please ensure the demo is running on port 8001")
            return
    except:
        print("⚠️  Demo server is not running!")
        print("Please run: python3 demo/standalone_server.py")
        return
    
    print("✅ Demo server is running on port 8001")
    print("\n📡 Creating public tunnel...")
    
    # Try using localtunnel (npx based solution)
    try:
        print("\n🔧 Installing localtunnel...")
        subprocess.run(["npm", "install", "-g", "localtunnel"], 
                      capture_output=True, check=False)
        
        print("🚀 Starting tunnel...")
        process = subprocess.Popen(
            ["npx", "localtunnel", "--port", "8001", "--subdomain", "velora-demo"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for URL
        time.sleep(3)
        
        print("\n" + "="*70)
        print("📱 MOBILE ACCESS READY!")
        print("="*70)
        print("\n🌐 Your demo is now accessible at:")
        print("\n   https://velora-demo.loca.lt")
        print("\n📱 Open this URL on your mobile device!")
        print("\n⚠️  Note: You may need to enter 'velora-demo' as password")
        print("="*70)
        print("\nPress Ctrl+C to stop the tunnel")
        
        # Keep running
        process.wait()
        
    except KeyboardInterrupt:
        print("\n\n👋 Tunnel closed")
    except Exception as e:
        print(f"\n❌ Could not create tunnel: {e}")
        print("\n💡 Alternative: Use SSH tunneling or ngrok")
        print("   ngrok: ngrok http 8001")
        print("   SSH: ssh -R 80:localhost:8001 serveo.net")

if __name__ == "__main__":
    create_tunnel()