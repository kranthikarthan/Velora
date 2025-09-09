#!/bin/bash

echo "=========================================="
echo "🚀 VELORA DEMO - Starting Up"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose found"
echo ""

# Stop any existing containers
echo "🛑 Stopping any existing containers..."
docker-compose -f docker-compose.demo.yml down 2>/dev/null

# Build and start the demo
echo ""
echo "🔨 Building demo containers..."
docker-compose -f docker-compose.demo.yml build

echo ""
echo "🚀 Starting Velora demo..."
docker-compose -f docker-compose.demo.yml up -d

# Wait for services to be ready
echo ""
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are running
if docker-compose -f docker-compose.demo.yml ps | grep -q "Up"; then
    echo ""
    echo "=========================================="
    echo "✅ VELORA DEMO IS RUNNING!"
    echo "=========================================="
    echo ""
    echo "🌐 Access Points:"
    echo "   📊 Main Dashboard:  http://localhost:3000"
    echo "   🔌 API Explorer:    http://localhost:8000/docs"
    echo "   📈 Grafana:         http://localhost:3001 (admin/admin)"
    echo "   🏦 Payment Demo:    http://localhost:8000/demo/payment"
    echo ""
    echo "📝 Try These:"
    echo "   1. Open http://localhost:8000 in your browser"
    echo "   2. Click 'Send Payment' to process a payment"
    echo "   3. Watch the real-time flow through the system"
    echo ""
    echo "🛑 To stop the demo:"
    echo "   ./stop_demo.sh"
    echo ""
    echo "📋 To view logs:"
    echo "   docker-compose -f docker-compose.demo.yml logs -f"
    echo ""
else
    echo ""
    echo "❌ Failed to start services. Check the logs:"
    echo "   docker-compose -f docker-compose.demo.yml logs"
    exit 1
fi