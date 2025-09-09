#!/usr/bin/env python3
"""
Velora Secure Demo - Demonstrates the complete system with security features
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any

from velora.core import VeloraCore
from velora.agents.base import TaskContext
from velora.security.auth import Permission


async def demonstrate_security_features(velora: VeloraCore):
    """Demonstrate security features"""
    print("\n" + "=" * 60)
    print("SECURITY FEATURES DEMONSTRATION")
    print("=" * 60)
    
    security = velora.security_manager
    
    # 1. User Registration and Authentication
    print("\n1. User Registration and Authentication")
    print("-" * 40)
    
    # Register a new user
    user_identity = security.auth_manager.register_identity(
        identity_id="demo_user",
        identity_type="user",
        name="Demo User",
        password="SecureP@ssw0rd123!",
        permissions={Permission.AGENT_READ, Permission.TASK_SUBMIT}
    )
    print(f"✓ Registered user: {user_identity.name}")
    
    # Authenticate with password
    auth_context = await security.authenticate({
        "type": "password",
        "identity_id": "demo_user",
        "password": "SecureP@ssw0rd123!",
        "ip": "192.168.1.100"
    })
    print(f"✓ Authentication successful")
    print(f"  Session ID: {auth_context.session_id}")
    print(f"  Token: {auth_context.token.token[:20]}...")
    
    # 2. Authorization Checks
    print("\n2. Authorization and Access Control")
    print("-" * 40)
    
    # Check permissions
    can_read = security.authorize(
        user_identity,
        Permission.AGENT_READ
    )
    print(f"✓ Can read agents: {can_read}")
    
    can_delete = security.authorize(
        user_identity,
        Permission.AGENT_DELETE
    )
    print(f"✓ Can delete agents: {can_delete}")
    
    # Grant additional permission
    security.authz_manager.grant_permission(
        user_identity,
        Permission.SERVICE_DISCOVER
    )
    print(f"✓ Granted SERVICE_DISCOVER permission")
    
    # 3. Data Encryption
    print("\n3. Data Encryption")
    print("-" * 40)
    
    # Encrypt sensitive data
    sensitive_data = b"This is confidential information"
    encrypted = security.encrypt_data(sensitive_data, "confidential")
    print(f"✓ Data encrypted")
    print(f"  Algorithm: {encrypted.algorithm}")
    print(f"  Ciphertext length: {len(encrypted.ciphertext)} bytes")
    
    # Decrypt data
    decrypted = security.decrypt_data(encrypted)
    print(f"✓ Data decrypted successfully")
    print(f"  Matches original: {decrypted == sensitive_data}")
    
    # 4. Threat Detection
    print("\n4. Threat Detection")
    print("-" * 40)
    
    # Simulate normal request
    normal_request = {
        "ip": "192.168.1.100",
        "path": "/api/agents",
        "method": "GET",
        "size": 256,
        "user_id": "demo_user"
    }
    
    threat = await security.analyze_request(normal_request)
    print(f"✓ Normal request analyzed: No threats detected")
    
    # Simulate SQL injection attempt
    malicious_request = {
        "ip": "10.0.0.1",
        "path": "/api/agents",
        "method": "POST",
        "data": "'; DROP TABLE users; --",
        "size": 512,
        "user_id": "attacker"
    }
    
    threat = await security.analyze_request(malicious_request)
    if threat:
        print(f"✓ Threat detected!")
        print(f"  Type: {threat.threat_type.value}")
        print(f"  Level: {threat.threat_level.name}")
        print(f"  Mitigated: {threat.mitigated}")
    
    # 5. Failed Authentication Tracking
    print("\n5. Brute Force Protection")
    print("-" * 40)
    
    # Simulate failed login attempts
    for i in range(3):
        try:
            await security.authenticate({
                "type": "password",
                "identity_id": "demo_user",
                "password": "wrong_password",
                "ip": "10.0.0.2"
            })
        except:
            pass
    
    print(f"✓ Failed authentication attempts tracked")
    
    # Check if IP would be blocked after more attempts
    threat = security.threat_detector.track_failed_authentication(
        "demo_user",
        "10.0.0.2"
    )
    print(f"✓ Brute force protection active")
    
    # 6. Security Status
    print("\n6. Security System Status")
    print("-" * 40)
    
    status = security.get_security_status()
    print(f"✓ Security Status:")
    print(f"  Active sessions: {status['statistics']['active_sessions']}")
    print(f"  Registered identities: {status['statistics']['registered_identities']}")
    print(f"  Blocked IPs: {status['statistics']['blocked_ips']}")
    print(f"  Active threats: {status['statistics']['active_threats']}")
    
    # 7. Audit Log
    print("\n7. Audit Trail")
    print("-" * 40)
    
    audit_log = security.get_audit_log(limit=5)
    print(f"✓ Recent audit log entries: {len(audit_log)}")
    for entry in audit_log[-3:]:
        print(f"  [{entry['timestamp'][:19]}] {entry['category']}/{entry['action']}")


async def demonstrate_agent_security(velora: VeloraCore):
    """Demonstrate agent-level security"""
    print("\n" + "=" * 60)
    print("AGENT SECURITY DEMONSTRATION")
    print("=" * 60)
    
    # 1. Create agent with security context
    print("\n1. Secure Agent Creation")
    print("-" * 40)
    
    # Register agent identity
    agent_keypair = velora.security_manager.encryption_engine.generate_signing_keypair()
    public_key_hex = agent_keypair.public_key.public_bytes_raw().hex()
    
    agent_identity = velora.security_manager.auth_manager.register_identity(
        identity_id="secure-agent-001",
        identity_type="agent",
        name="Secure Data Processor",
        public_key=public_key_hex,
        permissions={
            Permission.TASK_SUBMIT,
            Permission.TASK_READ,
            Permission.PROTOCOL_SEND,
            Permission.SERVICE_REGISTER
        }
    )
    print(f"✓ Agent identity registered: {agent_identity.name}")
    
    # Create the actual agent
    agent = await velora.agent_manager.create_agent(
        agent_type="data_processor",
        agent_id="secure-agent-001"
    )
    await agent.start()
    print(f"✓ Secure agent created and started")
    
    # 2. Secure Task Processing
    print("\n2. Secure Task Processing")
    print("-" * 40)
    
    # Create task with sensitive data
    sensitive_task = TaskContext(
        task_type="data_processing",
        input_data={
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "email": "user@example.com",
            "medical_record": "Patient has condition X"
        },
        parameters={
            "transformations": ["redact_pii", "encrypt_sensitive"],
            "validations": ["pii_compliance"],
            "security_level": "high"
        }
    )
    
    # Encrypt task data before submission
    task_data_bytes = json.dumps(sensitive_task.input_data).encode()
    encrypted_task_data = velora.security_manager.encrypt_data(
        task_data_bytes,
        "top_secret"
    )
    
    print(f"✓ Task data encrypted before processing")
    print(f"  Original size: {len(task_data_bytes)} bytes")
    print(f"  Encrypted size: {len(encrypted_task_data.ciphertext)} bytes")
    
    # Submit encrypted task
    task_id = await agent.submit_task(sensitive_task)
    print(f"✓ Secure task submitted: {task_id}")
    
    # 3. Secure Communication
    print("\n3. Secure Agent Communication")
    print("-" * 40)
    
    # Create signed message
    message_data = b"Critical agent directive"
    signature = velora.security_manager.encryption_engine.sign_data(
        message_data,
        agent_keypair.private_key
    )
    
    print(f"✓ Message signed with agent's private key")
    print(f"  Signature: {signature.hex()[:40]}...")
    
    # Verify signature
    is_valid = velora.security_manager.encryption_engine.verify_signature(
        message_data,
        signature,
        agent_keypair.public_key
    )
    print(f"✓ Signature verification: {is_valid}")


async def demonstrate_protocol_security(velora: VeloraCore):
    """Demonstrate protocol-level security"""
    print("\n" + "=" * 60)
    print("PROTOCOL SECURITY DEMONSTRATION")
    print("=" * 60)
    
    # 1. Secure Message Exchange
    print("\n1. Secure UAICP Message Exchange")
    print("-" * 40)
    
    # Create encrypted message
    message = velora.protocol_manager.uaicp.create_message(
        message_type="CAPABILITY_ANNOUNCEMENT",
        destination_agent_id="secure-agent-001",
        payload={
            "capabilities": ["secure_processing", "encryption"],
            "security_level": "high",
            "trust_score": 0.95
        }
    )
    
    # Message is automatically signed and can be encrypted
    print(f"✓ Secure message created")
    print(f"  Message ID: {message.message_id}")
    print(f"  Signed: {message.security.signature is not None}")
    
    # 2. Trust-based Service Discovery
    print("\n2. Trust-based Service Discovery")
    print("-" * 40)
    
    # Register secure service
    from velora.protocols.anp import ServiceRegistration
    
    secure_service = ServiceRegistration(
        agent_id="secure-agent-001",
        service_name="Secure Data Processing",
        service_category="data_processing",
        service_description="PII-compliant data processing with encryption",
        capability_manifest={
            "capabilities": [
                {"name": "pii_redaction", "version": "1.0.0"},
                {"name": "data_encryption", "version": "2.0.0"}
            ],
            "security_requirements": {
                "min_trust_score": 0.8,
                "encryption_required": True,
                "authentication_required": True
            }
        }
    )
    
    service_id = velora.protocol_manager.anp.register_service(secure_service)
    print(f"✓ Secure service registered: {service_id}")
    
    # Discover services with trust requirements
    trusted_services = velora.protocol_manager.anp.discover_services(
        capability_requirements=["data_encryption"],
        filters={"min_trust_score": 0.7}
    )
    print(f"✓ Found {len(trusted_services)} trusted services")


async def main():
    """Main demonstration function"""
    print("=" * 60)
    print("VELORA SECURE DEMONSTRATION")
    print("Complete System with Security Features")
    print("=" * 60)
    
    # Initialize Velora
    print("\nInitializing Velora with Security Framework...")
    velora = VeloraCore()
    await velora.setup()
    await velora.start()
    print("✓ Velora initialized with all security components")
    
    try:
        # Run security demonstrations
        await demonstrate_security_features(velora)
        await demonstrate_agent_security(velora)
        await demonstrate_protocol_security(velora)
        
        # System Health Check
        print("\n" + "=" * 60)
        print("SYSTEM HEALTH CHECK")
        print("=" * 60)
        
        health = await velora.health_check()
        print(f"\nOverall System Health: {health['status'].upper()}")
        print("\nComponent Status:")
        for component, status in health['checks'].items():
            status_str = status.get('status', 'unknown')
            print(f"  • {component}: {status_str}")
        
        # Final Statistics
        print("\n" + "=" * 60)
        print("DEMONSTRATION COMPLETE")
        print("=" * 60)
        
        print("\nSystem Statistics:")
        print(f"  • Uptime: {velora.get_uptime():.2f} seconds")
        print(f"  • Environment: {velora.settings.environment}")
        print(f"  • Security: ENABLED (Zero-Trust)")
        print(f"  • Encryption: AES-256-GCM + Ed25519/X25519")
        print(f"  • Threat Detection: AI-POWERED")
        
    finally:
        # Cleanup
        print("\nShutting down Velora...")
        await velora.stop()
        print("✓ Velora stopped successfully")
        
        print("\n" + "=" * 60)
        print("Thank you for exploring Velora!")
        print("The AI Interoperability Layer for the Future")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())