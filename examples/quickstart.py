"""
Velora Quick Start Example

This example demonstrates how to:
1. Initialize Velora
2. Create and manage agents
3. Submit tasks for processing
4. Send messages between agents
5. Register and discover services
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

# Import Velora components
from velora.core import VeloraCore
from velora.agents import DataProcessorAgent, ProtocolTranslatorAgent
from velora.agents.base import TaskContext
from velora.protocols import MessageType


async def main():
    """Main example function"""
    print("=" * 60)
    print("Velora AI Interoperability Layer - Quick Start Example")
    print("=" * 60)
    
    # 1. Initialize Velora Core
    print("\n1. Initializing Velora Core...")
    velora = VeloraCore()
    await velora.setup()
    await velora.start()
    print("✓ Velora Core initialized and started")
    
    # 2. Create agents
    print("\n2. Creating agents...")
    
    # Create a data processor agent
    data_processor = await velora.agent_manager.create_agent(
        agent_type="data_processor",
        agent_id="example-data-processor"
    )
    await data_processor.start()
    print(f"✓ Created data processor agent: {data_processor.agent_id}")
    
    # Create a protocol translator agent
    translator = await velora.agent_manager.create_agent(
        agent_type="protocol_translator",
        agent_id="example-translator"
    )
    await translator.start()
    print(f"✓ Created protocol translator agent: {translator.agent_id}")
    
    # 3. Submit a data processing task
    print("\n3. Submitting data processing task...")
    
    # Sample data to process
    sample_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30,
        "city": "New York"
    }
    
    # Create task context
    data_task = TaskContext(
        task_type="data_processing",
        input_data=sample_data,
        parameters={
            "transformations": ["uppercase", "hash"],
            "validations": ["required_fields"],
            "enrichments": ["metadata", "checksum"]
        }
    )
    
    # Submit task
    task_id = await data_processor.submit_task(data_task)
    print(f"✓ Task submitted: {task_id}")
    
    # Wait for task completion
    await asyncio.sleep(2)
    
    # Check task result
    if data_processor.completed_tasks:
        result = data_processor.completed_tasks[-1]
        print(f"✓ Task completed with status: {result.status}")
        print(f"  Processed data: {json.dumps(result.output_data, indent=2)[:200]}...")
    
    # 4. Protocol translation example
    print("\n4. Protocol translation example...")
    
    # REST to gRPC translation
    rest_message = {
        "method": "POST",
        "path": "/api/users/create",
        "headers": {"Content-Type": "application/json"},
        "body": {"username": "alice", "email": "alice@example.com"}
    }
    
    translation_task = TaskContext(
        task_type="protocol_translation",
        input_data=rest_message,
        parameters={
            "source_protocol": "rest",
            "target_protocol": "grpc"
        }
    )
    
    task_id = await translator.submit_task(translation_task)
    print(f"✓ Translation task submitted: {task_id}")
    
    await asyncio.sleep(1)
    
    if translator.completed_tasks:
        result = translator.completed_tasks[-1]
        print(f"✓ Translation completed: {result.status}")
        print(f"  Translated message: {json.dumps(result.output_data, indent=2)}")
    
    # 5. Service registration and discovery
    print("\n5. Service registration and discovery...")
    
    # Register a service
    from velora.protocols.anp import ServiceRegistration, Capability
    
    # Register data processing capability
    capability = Capability(
        name="advanced_data_processing",
        description="Advanced data processing with ML",
        version="2.0.0"
    )
    data_processor.anp.register_capability(capability)
    
    # Register service
    service = ServiceRegistration(
        agent_id=data_processor.agent_id,
        service_name="Advanced Data Processor",
        service_category="data_processing",
        service_description="ML-powered data processing service",
        capability_manifest={
            "capabilities": [
                {
                    "name": "advanced_data_processing",
                    "version": "2.0.0"
                }
            ]
        }
    )
    
    service_id = velora.protocol_manager.anp.register_service(service)
    print(f"✓ Service registered: {service_id}")
    
    # Discover services
    discovered = velora.protocol_manager.anp.discover_services(
        capability_requirements=["advanced_data_processing"]
    )
    print(f"✓ Discovered {len(discovered)} matching services")
    
    # 6. Message exchange between agents
    print("\n6. Message exchange between agents...")
    
    # Send capability announcement
    message = velora.protocol_manager.uaicp.create_message(
        message_type=MessageType.CAPABILITY_ANNOUNCEMENT,
        destination_agent_id="broadcast",
        payload={
            "agent_id": data_processor.agent_id,
            "capabilities": ["data_processing", "ml_inference"],
            "status": "available"
        }
    )
    
    await velora.protocol_manager.uaicp.send_message(message)
    print(f"✓ Capability announcement sent: {message.message_id}")
    
    # 7. System status
    print("\n7. System Status:")
    status = velora.get_status()
    print(f"  Instance ID: {status['instance_id']}")
    print(f"  Uptime: {status['uptime_seconds']:.2f} seconds")
    print(f"  Environment: {status['environment']}")
    print(f"  Components:")
    for component, state in status['components'].items():
        print(f"    - {component}: {state}")
    
    # 8. Agent metrics
    print("\n8. Agent Metrics:")
    metrics = velora.agent_manager.get_metrics()
    print(f"  Total agents: {metrics['total_agents']}")
    print(f"  Agents by type: {metrics['agents_by_type']}")
    print(f"  Agents by state: {metrics['agents_by_state']}")
    
    # 9. Health check
    print("\n9. Health Check:")
    health = await velora.health_check()
    print(f"  Overall status: {health['status']}")
    for component, check in health['checks'].items():
        status = check.get('status', 'unknown')
        print(f"    - {component}: {status}")
    
    # 10. Cleanup
    print("\n10. Cleaning up...")
    await velora.stop()
    print("✓ Velora stopped successfully")
    
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())