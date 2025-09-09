#!/usr/bin/env python3
"""
🚀 VELORA INTERACTIVE DEMO LAUNCHER
Complete demonstration with beautiful web UI
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def print_banner():
    """Print beautiful banner"""
    print("""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                                                                      ║
    ║   ██╗   ██╗███████╗██╗      ██████╗ ██████╗  █████╗                ║
    ║   ██║   ██║██╔════╝██║     ██╔═══██╗██╔══██╗██╔══██╗               ║
    ║   ██║   ██║█████╗  ██║     ██║   ██║██████╔╝███████║               ║
    ║   ╚██╗ ██╔╝██╔══╝  ██║     ██║   ██║██╔══██╗██╔══██║               ║
    ║    ╚████╔╝ ███████╗███████╗╚██████╔╝██║  ██║██║  ██║               ║
    ║     ╚═══╝  ╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝               ║
    ║                                                                      ║
    ║              🚀 INTERACTIVE DEMO WITH BEAUTIFUL UI 🚀               ║
    ║                                                                      ║
    ╚══════════════════════════════════════════════════════════════════════╝
    """)

def check_requirements():
    """Check if required packages are installed"""
    required = ['fastapi', 'uvicorn', 'httpx']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"\n⚠️  Missing packages: {', '.join(missing)}")
        print("\n📦 Installing required packages...")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing, 
                      capture_output=True, text=True)
        print("✅ Packages installed!")
    
    return True

def launch_demo():
    """Launch the interactive demo"""
    print_banner()
    
    print("\n🔍 Checking requirements...")
    if not check_requirements():
        return
    
    print("✅ All requirements satisfied!")
    
    print("\n🚀 Launching Velora Interactive Demo...")
    print("="*70)
    
    # Import and run the demo server
    try:
        from demo.standalone_server import run_demo
        
        print("\n⏳ Starting server...")
        time.sleep(1)
        
        # Try to open browser
        try:
            print("\n🌐 Opening browser...")
            webbrowser.open("http://localhost:8001")
        except:
            print("\n📱 Please open your browser to: http://localhost:8001")
        
        # Run the server
        run_demo()
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Trying alternative method...")
        
        # Fallback to subprocess
        try:
            subprocess.run([sys.executable, "demo/standalone_server.py"])
        except:
            print("\n🔧 Please run: python demo/standalone_server.py")

if __name__ == "__main__":
    launch_demo()