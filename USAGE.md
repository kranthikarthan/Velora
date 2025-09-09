# Velora Usage Guide

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/velora/velora.git
cd velora

# Install dependencies
pip install -r requirements.txt

# Or using Poetry
poetry install
```

### Running with Docker

```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f velora
```

### Running Locally

```bash
# Start required services (PostgreSQL, Redis, etc.)
docker-compose up -d postgres redis neo4j mongodb kafka

# Run Velora
python -m velora.api.app

# API will be available at http://localhost:8000
# Documentation at http://localhost:8000/docs
```

## 📡 API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

### System Status

```bash
curl http://localhost:8000/api/v1/system/status
```

### Agent Management

#### List Agents
```bash
curl http://localhost:8000/api/v1/agents
```

#### Create Agent
```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "data_processor",
    "agent_id": "my-processor",
    "name": "My Data Processor"
  }'
```

#### Start/Stop Agent
```bash
# Start
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/start

# Stop
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/stop
```

### Task Processing

#### Submit Task
```bash
curl -X POST http://localhost:8000/api/v1/tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "data_processor",
    "task_type": "data_processing",
    "input_data": {
      "name": "John Doe",
      "age": 30
    },
    "parameters": {
      "transformations": ["uppercase"],
      "validations": ["required_fields"]
    }
  }'
```

#### Get Task Status
```bash
curl http://localhost:8000/api/v1/tasks/{task_id}
```

### Protocol Communication

#### Send Message
```bash
curl -X POST http://localhost:8000/api/v1/protocols/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "message_type": "CAPABILITY_ANNOUNCEMENT",
    "destination_agent": "agent-123",
    "payload": {
      "capabilities": ["data_processing", "ml_inference"]
    },
    "priority": 5
  }'
```

#### Register Service
```bash
curl -X POST http://localhost:8000/api/v1/protocols/service/register \
  -H "Content-Type: application/json" \
  -d '{
    "service_name": "Data Processing Service",
    "service_version": "1.0.0",
    "service_category": "data_processing",
    "service_description": "Advanced data processing",
    "capabilities": [
      {
        "name": "json_processing",
        "version": "1.0.0"
      }
    ]
  }'
```

#### Discover Services
```bash
curl -X POST http://localhost:8000/api/v1/protocols/service/discover \
  -H "Content-Type: application/json" \
  -d '{
    "capabilities": ["data_processing"],
    "filters": {
      "min_trust_score": 0.7
    }
  }'
```

## 🐍 Python SDK Usage

### Basic Example

```python
import asyncio
from velora import VeloraCore
from velora.agents import DataProcessorAgent
from velora.agents.base import TaskContext

async def main():
    # Initialize Velora
    velora = VeloraCore()
    await velora.setup()
    await velora.start()
    
    # Create an agent
    agent = await velora.agent_manager.create_agent(
        agent_type="data_processor",
        agent_id="my-processor"
    )
    await agent.start()
    
    # Submit a task
    task = TaskContext(
        task_type="data_processing",
        input_data={"name": "Alice", "age": 25},
        parameters={
            "transformations": ["uppercase"],
            "enrichments": ["metadata"]
        }
    )
    
    task_id = await agent.submit_task(task)
    print(f"Task submitted: {task_id}")
    
    # Wait for completion
    await asyncio.sleep(2)
    
    # Check results
    if agent.completed_tasks:
        result = agent.completed_tasks[-1]
        print(f"Result: {result.output_data}")
    
    # Cleanup
    await velora.stop()

# Run
asyncio.run(main())
```

### Protocol Communication

```python
from velora.protocols import UAICP, MessageType

# Create UAICP handler
uaicp = UAICP("my-agent")

# Create message
message = uaicp.create_message(
    MessageType.CAPABILITY_DISCOVERY_REQUEST,
    "target-agent",
    {
        "requested_capabilities": [
            {"capability_type": "data_processing"}
        ]
    }
)

# Send message
response = await uaicp.send_message(message, timeout=30)
```

### Service Registration

```python
from velora.protocols.anp import ServiceRegistration

# Register service
service = ServiceRegistration(
    service_name="ML Inference Service",
    service_category="ml_inference",
    service_description="TensorFlow-based inference",
    capability_manifest={
        "capabilities": [
            {
                "name": "image_classification",
                "version": "1.0.0"
            }
        ]
    }
)

service_id = velora.protocol_manager.anp.register_service(service)
```

## 🔌 WebSocket Real-time Events

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/events');

ws.onopen = () => {
    console.log('Connected to Velora');
    
    // Subscribe to events
    ws.send(JSON.stringify({
        type: 'subscribe',
        events: ['agent_status', 'task_complete']
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Event:', data);
};
```

## 🐳 Kubernetes Deployment

```bash
# Create namespace
kubectl apply -f deployment/k8s/namespace.yaml

# Deploy Velora
kubectl apply -f deployment/k8s/deployment.yaml

# Check deployment
kubectl get pods -n velora

# Scale deployment
kubectl scale deployment velora-core -n velora --replicas=5

# View logs
kubectl logs -f deployment/velora-core -n velora
```

## 📊 Monitoring

### Prometheus Metrics

Metrics are exposed at `http://localhost:9090/metrics`

### Grafana Dashboards

Access Grafana at `http://localhost:3000`
- Username: admin
- Password: admin

### Health Endpoints

- `/health` - Basic health check
- `/api/v1/system/health` - Detailed health check
- `/api/v1/system/metrics` - System metrics

## 🔧 Configuration

### Environment Variables

```bash
# Core settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/velora
REDIS_URL=redis://localhost:6379/0
NEO4J_URL=bolt://localhost:7687
MONGODB_URL=mongodb://localhost:27017/velora

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Security
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Performance
WORKERS=4
CONNECTION_POOL_SIZE=20
CACHE_TTL=300
```

### Configuration File

Create `.env` file in project root:

```env
APP_NAME=Velora
APP_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

DATABASE_URL=postgresql://velora:velora@localhost:5432/velora
REDIS_URL=redis://localhost:6379/0

UAICP_VERSION=1.0
ANP_VERSION=1.0
AGENT_HEARTBEAT_INTERVAL=30
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=velora tests/

# Run integration tests
pytest tests/integration/

# Run specific test
pytest tests/test_agents.py::test_data_processor
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection refused to database**
   ```bash
   # Check if services are running
   docker-compose ps
   
   # Restart services
   docker-compose restart postgres redis
   ```

2. **Agent not responding**
   ```bash
   # Check agent status
   curl http://localhost:8000/api/v1/agents/{agent_id}/status
   
   # Restart agent
   curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/stop
   curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/start
   ```

3. **High memory usage**
   ```bash
   # Check metrics
   curl http://localhost:8000/api/v1/system/metrics
   
   # Scale down agents
   curl -X POST "http://localhost:8000/api/v1/agents/scale/data_processor?target_count=2"
   ```

## 📚 Advanced Usage

### Custom Agent Development

```python
from velora.agents.base import Agent, AgentConfiguration, TaskContext, TaskResult

class CustomAgent(Agent):
    async def _initialize(self):
        # Custom initialization
        pass
    
    async def _start(self):
        # Custom start logic
        pass
    
    async def _stop(self):
        # Custom stop logic
        pass
    
    async def process_task(self, task: TaskContext) -> TaskResult:
        # Custom task processing
        result = TaskResult(
            task_id=task.task_id,
            status="completed",
            output_data={"processed": True}
        )
        return result

# Register custom agent type
velora.agent_manager.register_agent_type("custom", CustomAgent)
```

### Protocol Extensions

```python
from velora.protocols import MessageType

# Register custom message handler
async def handle_custom_message(message):
    print(f"Custom message: {message.payload}")
    return None

velora.protocol_manager.uaicp.register_handler(
    MessageType.CUSTOM_TYPE,
    handle_custom_message
)
```

## 📖 Documentation

- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](https://docs.velora.ai/api)
- [Protocol Specifications](protocols/)
- [Agent Development Guide](docs/agents.md)
- [Security Best Practices](security/README.md)

## 🆘 Support

- GitHub Issues: https://github.com/velora/velora/issues
- Documentation: https://docs.velora.ai
- Community Forum: https://community.velora.ai
- Email: support@velora.ai