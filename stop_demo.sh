#!/bin/bash

echo "=========================================="
echo "🛑 Stopping Velora Demo"
echo "=========================================="
echo ""

# Stop containers
docker-compose -f docker-compose.demo.yml down

echo ""
echo "✅ Demo stopped successfully"
echo ""