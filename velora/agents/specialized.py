"""
Specialized Agent implementations

These agents handle specific tasks like data processing, protocol translation,
and API integration.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import hashlib
import base64

from velora.agents.base import Agent, AgentConfiguration, AgentType, AgentCapability, TaskContext, TaskResult
from velora.core.logging import LoggerMixin


class DataProcessorAgent(Agent):
    """
    Agent specialized in data processing and transformation
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize data processor agent"""
        capabilities = [
            AgentCapability(
                name="json_processing",
                description="Process and transform JSON data",
                version="1.0.0"
            ),
            AgentCapability(
                name="data_validation",
                description="Validate data against schemas",
                version="1.0.0"
            ),
            AgentCapability(
                name="data_enrichment",
                description="Enrich data with additional information",
                version="1.0.0"
            )
        ]
        
        config = AgentConfiguration(
            agent_id=agent_id or f"data-processor-{datetime.utcnow().timestamp()}",
            agent_type=AgentType.SPECIALIZED,
            name="DataProcessorAgent",
            description="Specialized agent for data processing and transformation",
            capabilities=capabilities
        )
        
        super().__init__(config)
        
        # Processing engines
        self.transformation_rules = {}
        self.validation_schemas = {}
        self.enrichment_sources = {}
    
    async def _initialize(self) -> None:
        """Initialize data processor specific components"""
        # Load default transformation rules
        self.transformation_rules = {
            "uppercase": lambda x: x.upper() if isinstance(x, str) else x,
            "lowercase": lambda x: x.lower() if isinstance(x, str) else x,
            "trim": lambda x: x.strip() if isinstance(x, str) else x,
            "hash": lambda x: hashlib.sha256(str(x).encode()).hexdigest()
        }
        
        # Load default validation schemas
        self.validation_schemas = {
            "required_fields": self._validate_required_fields,
            "data_types": self._validate_data_types,
            "value_ranges": self._validate_value_ranges
        }
        
        self.log_info("Data processor agent initialized")
    
    async def _start(self) -> None:
        """Start data processor services"""
        # Could start background data processing services
        pass
    
    async def _stop(self) -> None:
        """Stop data processor services"""
        # Clean up any resources
        pass
    
    async def process_task(self, task: TaskContext) -> TaskResult:
        """
        Process data transformation task
        
        Args:
            task: Task context containing data to process
        
        Returns:
            Task result with processed data
        """
        result = TaskResult(
            task_id=task.task_id,
            status="pending",
            start_time=datetime.utcnow()
        )
        
        try:
            # Extract processing instructions
            input_data = task.input_data
            transformations = task.parameters.get("transformations", [])
            validations = task.parameters.get("validations", [])
            enrichments = task.parameters.get("enrichments", [])
            
            # Validate input data
            if validations:
                validation_result = await self._validate_data(input_data, validations)
                if not validation_result["is_valid"]:
                    result.status = "validation_failed"
                    result.error = f"Validation failed: {validation_result['errors']}"
                    result.end_time = datetime.utcnow()
                    return result
            
            # Apply transformations
            processed_data = input_data
            if transformations:
                processed_data = await self._transform_data(processed_data, transformations)
            
            # Apply enrichments
            if enrichments:
                processed_data = await self._enrich_data(processed_data, enrichments)
            
            # Set result
            result.output_data = processed_data
            result.status = "completed"
            result.performance_metrics = {
                "records_processed": self._count_records(processed_data),
                "transformations_applied": len(transformations),
                "validations_performed": len(validations),
                "enrichments_applied": len(enrichments)
            }
            
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            self.log_error(f"Task {task.task_id} failed", error=e)
        
        result.end_time = datetime.utcnow()
        return result
    
    async def _validate_data(self, data: Any, validations: List[str]) -> Dict[str, Any]:
        """Validate data against specified rules"""
        errors = []
        
        for validation in validations:
            if validation in self.validation_schemas:
                validator = self.validation_schemas[validation]
                validation_result = validator(data)
                if not validation_result["is_valid"]:
                    errors.extend(validation_result["errors"])
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }
    
    async def _transform_data(self, data: Any, transformations: List[str]) -> Any:
        """Apply transformations to data"""
        transformed_data = data
        
        for transformation in transformations:
            if transformation in self.transformation_rules:
                transform_func = self.transformation_rules[transformation]
                if isinstance(transformed_data, dict):
                    for key in transformed_data:
                        transformed_data[key] = transform_func(transformed_data[key])
                elif isinstance(transformed_data, list):
                    transformed_data = [transform_func(item) for item in transformed_data]
                else:
                    transformed_data = transform_func(transformed_data)
        
        return transformed_data
    
    async def _enrich_data(self, data: Any, enrichments: List[str]) -> Any:
        """Enrich data with additional information"""
        enriched_data = data
        
        # Add metadata
        if "metadata" in enrichments and isinstance(enriched_data, dict):
            enriched_data["_metadata"] = {
                "processed_at": datetime.utcnow().isoformat(),
                "agent_id": self.agent_id,
                "version": self.configuration.version
            }
        
        # Add checksums
        if "checksum" in enrichments and isinstance(enriched_data, dict):
            data_str = json.dumps(enriched_data, sort_keys=True)
            enriched_data["_checksum"] = hashlib.sha256(data_str.encode()).hexdigest()
        
        return enriched_data
    
    def _validate_required_fields(self, data: Any) -> Dict[str, Any]:
        """Validate required fields"""
        # Simple example validation
        required = ["id", "name"]
        errors = []
        
        if isinstance(data, dict):
            for field in required:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
        
        return {"is_valid": len(errors) == 0, "errors": errors}
    
    def _validate_data_types(self, data: Any) -> Dict[str, Any]:
        """Validate data types"""
        # Simple example validation
        return {"is_valid": True, "errors": []}
    
    def _validate_value_ranges(self, data: Any) -> Dict[str, Any]:
        """Validate value ranges"""
        # Simple example validation
        return {"is_valid": True, "errors": []}
    
    def _count_records(self, data: Any) -> int:
        """Count records in data"""
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict):
            return 1
        return 0


class ProtocolTranslatorAgent(Agent):
    """
    Agent specialized in protocol translation between different systems
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize protocol translator agent"""
        capabilities = [
            AgentCapability(
                name="protocol_translation",
                description="Translate between different protocols",
                version="1.0.0"
            ),
            AgentCapability(
                name="message_transformation",
                description="Transform message formats",
                version="1.0.0"
            ),
            AgentCapability(
                name="schema_mapping",
                description="Map between different schemas",
                version="1.0.0"
            )
        ]
        
        config = AgentConfiguration(
            agent_id=agent_id or f"protocol-translator-{datetime.utcnow().timestamp()}",
            agent_type=AgentType.SPECIALIZED,
            name="ProtocolTranslatorAgent",
            description="Specialized agent for protocol translation",
            capabilities=capabilities
        )
        
        super().__init__(config)
        
        # Protocol mappings
        self.protocol_mappings = {}
        self.schema_mappings = {}
        self.transformation_rules = {}
    
    async def _initialize(self) -> None:
        """Initialize protocol translator specific components"""
        # Load protocol mappings
        self.protocol_mappings = {
            ("rest", "grpc"): self._translate_rest_to_grpc,
            ("grpc", "rest"): self._translate_grpc_to_rest,
            ("json", "xml"): self._translate_json_to_xml,
            ("xml", "json"): self._translate_xml_to_json,
            ("http", "mqtt"): self._translate_http_to_mqtt,
            ("mqtt", "http"): self._translate_mqtt_to_http
        }
        
        self.log_info("Protocol translator agent initialized")
    
    async def _start(self) -> None:
        """Start protocol translator services"""
        pass
    
    async def _stop(self) -> None:
        """Stop protocol translator services"""
        pass
    
    async def process_task(self, task: TaskContext) -> TaskResult:
        """
        Process protocol translation task
        
        Args:
            task: Task context containing message to translate
        
        Returns:
            Task result with translated message
        """
        result = TaskResult(
            task_id=task.task_id,
            status="pending",
            start_time=datetime.utcnow()
        )
        
        try:
            # Extract translation parameters
            message = task.input_data
            source_protocol = task.parameters.get("source_protocol", "")
            target_protocol = task.parameters.get("target_protocol", "")
            schema_mapping = task.parameters.get("schema_mapping", {})
            
            # Validate protocols
            translation_key = (source_protocol, target_protocol)
            if translation_key not in self.protocol_mappings:
                result.status = "failed"
                result.error = f"Unsupported protocol translation: {source_protocol} -> {target_protocol}"
                result.end_time = datetime.utcnow()
                return result
            
            # Perform translation
            translator = self.protocol_mappings[translation_key]
            translated_message = await translator(message, schema_mapping)
            
            # Set result
            result.output_data = translated_message
            result.status = "completed"
            result.performance_metrics = {
                "source_protocol": source_protocol,
                "target_protocol": target_protocol,
                "message_size": len(str(message)),
                "translated_size": len(str(translated_message))
            }
            
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            self.log_error(f"Translation task {task.task_id} failed", error=e)
        
        result.end_time = datetime.utcnow()
        return result
    
    async def _translate_rest_to_grpc(self, message: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Translate REST message to gRPC format"""
        # Simplified translation
        return {
            "method": message.get("method", ""),
            "service": message.get("path", "").split("/")[1] if "/" in message.get("path", "") else "",
            "request": message.get("body", {}),
            "metadata": message.get("headers", {})
        }
    
    async def _translate_grpc_to_rest(self, message: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Translate gRPC message to REST format"""
        # Simplified translation
        return {
            "method": "POST",
            "path": f"/{message.get('service', '')}/{message.get('method', '')}",
            "headers": message.get("metadata", {}),
            "body": message.get("request", {})
        }
    
    async def _translate_json_to_xml(self, message: Dict[str, Any], mapping: Dict[str, Any]) -> str:
        """Translate JSON to XML"""
        # Simplified translation (in production, use proper XML library)
        xml_parts = ["<?xml version='1.0' encoding='UTF-8'?>", "<root>"]
        
        def dict_to_xml(d: Dict[str, Any], indent: int = 1) -> List[str]:
            parts = []
            for key, value in d.items():
                indent_str = "  " * indent
                if isinstance(value, dict):
                    parts.append(f"{indent_str}<{key}>")
                    parts.extend(dict_to_xml(value, indent + 1))
                    parts.append(f"{indent_str}</{key}>")
                else:
                    parts.append(f"{indent_str}<{key}>{value}</{key}>")
            return parts
        
        xml_parts.extend(dict_to_xml(message))
        xml_parts.append("</root>")
        
        return "\n".join(xml_parts)
    
    async def _translate_xml_to_json(self, message: str, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Translate XML to JSON"""
        # Simplified translation (in production, use proper XML parser)
        # For now, return a placeholder
        return {"xml_content": message}
    
    async def _translate_http_to_mqtt(self, message: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Translate HTTP message to MQTT format"""
        return {
            "topic": message.get("path", "/").replace("/", "."),
            "payload": message.get("body", {}),
            "qos": 1,
            "retain": False
        }
    
    async def _translate_mqtt_to_http(self, message: Dict[str, Any], mapping: Dict[str, Any]) -> Dict[str, Any]:
        """Translate MQTT message to HTTP format"""
        return {
            "method": "POST",
            "path": "/" + message.get("topic", "").replace(".", "/"),
            "headers": {"Content-Type": "application/json"},
            "body": message.get("payload", {})
        }


class APIIntegrationAgent(Agent):
    """
    Agent specialized in API integration with external services
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize API integration agent"""
        capabilities = [
            AgentCapability(
                name="api_integration",
                description="Integrate with external APIs",
                version="1.0.0"
            ),
            AgentCapability(
                name="authentication_handling",
                description="Handle various authentication methods",
                version="1.0.0"
            ),
            AgentCapability(
                name="rate_limiting",
                description="Manage API rate limits",
                version="1.0.0"
            )
        ]
        
        config = AgentConfiguration(
            agent_id=agent_id or f"api-integration-{datetime.utcnow().timestamp()}",
            agent_type=AgentType.SPECIALIZED,
            name="APIIntegrationAgent",
            description="Specialized agent for API integration",
            capabilities=capabilities
        )
        
        super().__init__(config)
        
        # API configurations
        self.api_configs = {}
        self.auth_handlers = {}
        self.rate_limiters = {}
    
    async def _initialize(self) -> None:
        """Initialize API integration specific components"""
        # Load API configurations
        self.api_configs = {}
        
        # Setup authentication handlers
        self.auth_handlers = {
            "bearer": self._handle_bearer_auth,
            "basic": self._handle_basic_auth,
            "api_key": self._handle_api_key_auth,
            "oauth2": self._handle_oauth2_auth
        }
        
        self.log_info("API integration agent initialized")
    
    async def _start(self) -> None:
        """Start API integration services"""
        pass
    
    async def _stop(self) -> None:
        """Stop API integration services"""
        pass
    
    async def process_task(self, task: TaskContext) -> TaskResult:
        """
        Process API integration task
        
        Args:
            task: Task context containing API call details
        
        Returns:
            Task result with API response
        """
        result = TaskResult(
            task_id=task.task_id,
            status="pending",
            start_time=datetime.utcnow()
        )
        
        try:
            # Extract API call parameters
            api_id = task.parameters.get("api_id", "")
            endpoint = task.parameters.get("endpoint", "")
            method = task.parameters.get("method", "GET")
            headers = task.parameters.get("headers", {})
            auth_type = task.parameters.get("auth_type", "")
            auth_credentials = task.parameters.get("auth_credentials", {})
            
            # Handle authentication
            if auth_type and auth_type in self.auth_handlers:
                auth_handler = self.auth_handlers[auth_type]
                headers = await auth_handler(headers, auth_credentials)
            
            # Check rate limits
            if api_id in self.rate_limiters:
                await self._check_rate_limit(api_id)
            
            # Make API call (simplified - in production, use httpx or aiohttp)
            api_response = await self._make_api_call(
                endpoint, method, headers, task.input_data
            )
            
            # Set result
            result.output_data = api_response
            result.status = "completed"
            result.performance_metrics = {
                "api_id": api_id,
                "endpoint": endpoint,
                "method": method,
                "response_time": result.execution_time
            }
            
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            self.log_error(f"API task {task.task_id} failed", error=e)
        
        result.end_time = datetime.utcnow()
        return result
    
    async def _handle_bearer_auth(self, headers: Dict[str, str], credentials: Dict[str, Any]) -> Dict[str, str]:
        """Handle Bearer token authentication"""
        token = credentials.get("token", "")
        headers["Authorization"] = f"Bearer {token}"
        return headers
    
    async def _handle_basic_auth(self, headers: Dict[str, str], credentials: Dict[str, Any]) -> Dict[str, str]:
        """Handle Basic authentication"""
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        auth_str = f"{username}:{password}"
        auth_bytes = base64.b64encode(auth_str.encode()).decode()
        headers["Authorization"] = f"Basic {auth_bytes}"
        return headers
    
    async def _handle_api_key_auth(self, headers: Dict[str, str], credentials: Dict[str, Any]) -> Dict[str, str]:
        """Handle API key authentication"""
        api_key = credentials.get("api_key", "")
        key_location = credentials.get("key_location", "header")
        key_name = credentials.get("key_name", "X-API-Key")
        
        if key_location == "header":
            headers[key_name] = api_key
        # In production, handle query parameter API keys as well
        
        return headers
    
    async def _handle_oauth2_auth(self, headers: Dict[str, str], credentials: Dict[str, Any]) -> Dict[str, str]:
        """Handle OAuth2 authentication"""
        # Simplified OAuth2 - in production, implement full OAuth2 flow
        access_token = credentials.get("access_token", "")
        headers["Authorization"] = f"Bearer {access_token}"
        return headers
    
    async def _check_rate_limit(self, api_id: str) -> None:
        """Check and enforce rate limits"""
        # Simplified rate limiting - in production, use proper rate limiting
        await asyncio.sleep(0.1)  # Simple delay
    
    async def _make_api_call(
        self,
        endpoint: str,
        method: str,
        headers: Dict[str, str],
        data: Any
    ) -> Dict[str, Any]:
        """Make API call (placeholder)"""
        # In production, use httpx or aiohttp to make actual API calls
        return {
            "status": "success",
            "endpoint": endpoint,
            "method": method,
            "response": {"message": "API call simulated"}
        }