"""
Legacy System Bridge - Orchestrates legacy system integration

Provides seamless integration between modern systems and legacy mainframes,
handling protocol conversion, data transformation, and transaction management.
"""

import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from velora.core.config import Settings, get_settings
from velora.core.logging import LoggerMixin
from velora.core.exceptions import IntegrationError
from velora.legacy.iso20022 import ISO20022Handler, ISO20022Message, PaymentInstruction
from velora.legacy.cobol import COBOLCopybookParser, COBOLCopybook
from velora.legacy.cics import CICSGateway, CICSTransaction, CICSTransactionType
from velora.agents.base import Agent, AgentConfiguration, AgentType, TaskContext, TaskResult


class LegacySystemType(Enum):
    """Types of legacy systems"""
    MAINFRAME_CICS = "mainframe_cics"
    MAINFRAME_IMS = "mainframe_ims"
    AS400 = "as400"
    TANDEM = "tandem"
    LEGACY_DATABASE = "legacy_db"
    FILE_BASED = "file_based"


@dataclass
class LegacySystemConfig:
    """Legacy system configuration"""
    system_type: LegacySystemType
    host: str
    port: int
    encoding: str = "cp037"  # EBCDIC
    timeout: int = 30
    retry_count: int = 3
    credentials: Optional[Dict[str, str]] = None


class LegacyBridge(LoggerMixin):
    """
    Main orchestrator for legacy system integration
    """
    
    def __init__(self, settings: Optional[Settings] = None):
        """Initialize Legacy Bridge"""
        self.settings = settings or get_settings()
        
        # Component handlers
        self.iso20022_handler = ISO20022Handler()
        self.cobol_parser = COBOLCopybookParser()
        self.cics_gateways: Dict[str, CICSGateway] = {}
        
        # System configurations
        self.legacy_systems: Dict[str, LegacySystemConfig] = {}
        
        # Transaction mappings
        self.transaction_mappings: Dict[str, Dict[str, Any]] = {}
        
        # Copybook registry
        self.copybooks: Dict[str, str] = {}
        
        # Initialize default configurations
        self._initialize_defaults()
        
        self.is_running = False
        self.log_info("Legacy Bridge initialized")
    
    def _initialize_defaults(self) -> None:
        """Initialize default configurations"""
        # Register default copybooks
        self._register_default_copybooks()
        
        # Register default transaction mappings
        self._register_default_mappings()
        
        # Register default legacy systems
        if self.settings.legacy_mainframe_host:
            self.register_legacy_system(
                "mainframe_primary",
                LegacySystemConfig(
                    system_type=LegacySystemType.MAINFRAME_CICS,
                    host=self.settings.legacy_mainframe_host,
                    port=self.settings.legacy_mainframe_port or 2006,
                    encoding="cp037"
                )
            )
    
    def _register_default_copybooks(self) -> None:
        """Register default COBOL copybooks"""
        # Payment copybook
        payment_copybook = self.cobol_parser.create_sample_copybook()
        self.cobol_parser.parse_copybook(payment_copybook, "PAYMENT")
        self.copybooks["PAYMENT"] = payment_copybook
        
        # Account copybook
        account_copybook = """
       01  ACCOUNT-RECORD.
           05  ACCOUNT-NUMBER      PIC X(34).
           05  ACCOUNT-TYPE        PIC X(2).
           05  ACCOUNT-STATUS      PIC X(1).
           05  CUSTOMER-ID         PIC X(10).
           05  CUSTOMER-NAME       PIC X(35).
           05  BALANCE             PIC S9(13)V99 COMP-3.
           05  CURRENCY            PIC X(3).
           05  OPEN-DATE           PIC 9(8).
           05  LAST-ACTIVITY       PIC 9(8).
           05  INTEREST-RATE       PIC S9(3)V9(4) COMP-3.
        """
        self.cobol_parser.parse_copybook(account_copybook, "ACCOUNT")
        self.copybooks["ACCOUNT"] = account_copybook
    
    def _register_default_mappings(self) -> None:
        """Register default transaction mappings"""
        # ISO 20022 to CICS payment mapping
        self.transaction_mappings["ISO20022_TO_CICS_PAYMENT"] = {
            "source_format": "ISO20022",
            "target_format": "CICS",
            "copybook": "PAYMENT",
            "transaction_id": "PAYM",
            "field_mappings": {
                "message_id": "TRANS-ID",
                "creation_date_time": "TRANS-DATE",
                "amount": "AMOUNT",
                "currency": "CURRENCY",
                "debtor_account": "DEBTOR-ACCT",
                "debtor_name": "DEBTOR-NAME",
                "creditor_account": "CREDITOR-ACCT",
                "creditor_name": "CREDITOR-NAME",
                "remittance_info": "REMIT-INFO"
            }
        }
        
        # REST to CICS account inquiry mapping
        self.transaction_mappings["REST_TO_CICS_INQUIRY"] = {
            "source_format": "REST",
            "target_format": "CICS",
            "copybook": "ACCOUNT",
            "transaction_id": "AINQ",
            "field_mappings": {
                "accountNumber": "ACCOUNT-NUMBER",
                "inquiryType": "INQUIRY-TYPE"
            }
        }
    
    def register_legacy_system(self, name: str, config: LegacySystemConfig) -> None:
        """Register a legacy system"""
        self.legacy_systems[name] = config
        
        # Create CICS gateway if needed
        if config.system_type == LegacySystemType.MAINFRAME_CICS:
            self.cics_gateways[name] = CICSGateway(
                config.host,
                config.port,
                config.encoding
            )
        
        self.log_info(f"Registered legacy system: {name} ({config.system_type.value})")
    
    async def process_iso20022_to_legacy(
        self,
        iso_message: Union[str, ISO20022Message],
        target_system: str = "mainframe_primary"
    ) -> Dict[str, Any]:
        """
        Process ISO 20022 message to legacy system
        
        Args:
            iso_message: ISO 20022 message (XML string or parsed)
            target_system: Target legacy system name
        
        Returns:
            Processing result
        """
        try:
            # Parse ISO 20022 message if needed
            if isinstance(iso_message, str):
                message = self.iso20022_handler.parse_message(iso_message)
            else:
                message = iso_message
            
            self.log_info(f"Processing ISO 20022 message: {message.message_id}")
            
            # Convert to COBOL format
            cobol_data = self.iso20022_handler.convert_to_cobol_format(message)
            
            # Process each payment instruction
            results = []
            for trans_data in cobol_data.get("TRANSACTIONS", []):
                # Prepare CICS transaction data
                cics_data = {
                    "amount": float(trans_data["AMOUNT"]) / 100,
                    "currency": trans_data["CURRENCY"],
                    "debtor_account": trans_data["DEBTOR-ACCT"],
                    "debtor_name": trans_data["DEBTOR-NAME"],
                    "creditor_account": trans_data["CREDITOR-ACCT"],
                    "creditor_name": trans_data["CREDITOR-NAME"],
                    "reference": trans_data["INSTR-ID"]
                }
                
                # Execute CICS transaction
                if target_system in self.cics_gateways:
                    gateway = self.cics_gateways[target_system]
                    result = await gateway.execute_transaction("PAYM", cics_data)
                    results.append(result)
                else:
                    results.append({
                        "success": False,
                        "error": f"System {target_system} not available"
                    })
            
            return {
                "success": all(r.get("success", False) for r in results),
                "message_id": message.message_id,
                "transaction_count": len(results),
                "results": results
            }
            
        except Exception as e:
            self.log_error(f"Failed to process ISO 20022 message: {e}")
            raise IntegrationError(f"ISO 20022 processing failed: {str(e)}")
    
    async def process_rest_to_cics(
        self,
        rest_data: Dict[str, Any],
        transaction_id: str,
        target_system: str = "mainframe_primary"
    ) -> Dict[str, Any]:
        """
        Process REST API request to CICS transaction
        
        Args:
            rest_data: REST request data
            transaction_id: CICS transaction ID
            target_system: Target system name
        
        Returns:
            Transaction result
        """
        try:
            self.log_info(f"Processing REST to CICS: {transaction_id}")
            
            # Get mapping
            mapping_key = f"REST_TO_CICS_{transaction_id}"
            if mapping_key not in self.transaction_mappings:
                # Use generic mapping
                cics_data = rest_data
            else:
                # Apply field mappings
                mapping = self.transaction_mappings[mapping_key]
                cics_data = {}
                for rest_field, cics_field in mapping["field_mappings"].items():
                    if rest_field in rest_data:
                        cics_data[cics_field.lower().replace("-", "_")] = rest_data[rest_field]
            
            # Execute transaction
            if target_system in self.cics_gateways:
                gateway = self.cics_gateways[target_system]
                result = await gateway.execute_transaction(transaction_id, cics_data)
                
                # Convert COBOL field names back to REST format
                if result.get("success"):
                    rest_result = self._convert_cobol_to_rest(result)
                    return rest_result
                else:
                    return result
            else:
                # Try z/OS Connect if available
                return await self._call_zos_connect(rest_data, transaction_id)
            
        except Exception as e:
            self.log_error(f"Failed to process REST to CICS: {e}")
            raise IntegrationError(f"REST to CICS processing failed: {str(e)}")
    
    def _convert_cobol_to_rest(self, cobol_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert COBOL field names to REST format"""
        rest_data = {}
        
        for key, value in cobol_data.items():
            # Convert underscore to camelCase
            parts = key.split("_")
            if len(parts) > 1:
                rest_key = parts[0] + "".join(p.capitalize() for p in parts[1:])
            else:
                rest_key = key
            
            rest_data[rest_key] = value
        
        return rest_data
    
    async def _call_zos_connect(
        self,
        data: Dict[str, Any],
        operation: str
    ) -> Dict[str, Any]:
        """Call z/OS Connect as fallback"""
        # This would integrate with z/OS Connect REST APIs
        # For now, return a simulated response
        return {
            "success": True,
            "source": "zos_connect",
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
    
    async def convert_copybook_to_json(
        self,
        copybook_name: str,
        data: bytes
    ) -> Dict[str, Any]:
        """
        Convert COBOL copybook data to JSON
        
        Args:
            copybook_name: Name of copybook
            data: Binary COBOL data
        
        Returns:
            JSON representation
        """
        return self.cobol_parser.parse_data(copybook_name, data)
    
    async def convert_json_to_copybook(
        self,
        copybook_name: str,
        json_data: Dict[str, Any]
    ) -> bytes:
        """
        Convert JSON to COBOL copybook format
        
        Args:
            copybook_name: Name of copybook
            json_data: JSON data
        
        Returns:
            Binary COBOL data
        """
        return self.cobol_parser.format_data(copybook_name, json_data)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on legacy connections"""
        health = {
            "status": "healthy",
            "systems": {}
        }
        
        for name, config in self.legacy_systems.items():
            system_health = {
                "type": config.system_type.value,
                "host": config.host,
                "port": config.port,
                "status": "unknown"
            }
            
            # Check CICS gateway
            if name in self.cics_gateways:
                gateway = self.cics_gateways[name]
                if gateway.is_connected:
                    system_health["status"] = "connected"
                else:
                    try:
                        await gateway.connect()
                        system_health["status"] = "available"
                        await gateway.disconnect()
                    except:
                        system_health["status"] = "unavailable"
                        health["status"] = "degraded"
            
            health["systems"][name] = system_health
        
        return health
    
    async def start(self) -> None:
        """Start legacy bridge"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Connect to configured systems
        for name, gateway in self.cics_gateways.items():
            try:
                await gateway.connect()
                self.log_info(f"Connected to {name}")
            except Exception as e:
                self.log_error(f"Failed to connect to {name}: {e}")
        
        self.log_info("Legacy Bridge started")
    
    async def stop(self) -> None:
        """Stop legacy bridge"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Disconnect from all systems
        for name, gateway in self.cics_gateways.items():
            try:
                await gateway.disconnect()
                self.log_info(f"Disconnected from {name}")
            except Exception as e:
                self.log_error(f"Error disconnecting from {name}: {e}")
        
        self.log_info("Legacy Bridge stopped")


class LegacyIntegrationAgent(Agent):
    """
    Specialized agent for legacy system integration
    """
    
    def __init__(self, agent_id: Optional[str] = None):
        """Initialize Legacy Integration Agent"""
        config = AgentConfiguration(
            agent_id=agent_id or "legacy-integration-agent",
            name="Legacy System Integration Agent",
            agent_type=AgentType.SPECIALIZED,
            capabilities=[
                {"name": "iso20022_processing", "version": "1.0.0"},
                {"name": "cobol_conversion", "version": "1.0.0"},
                {"name": "cics_transaction", "version": "1.0.0"},
                {"name": "mainframe_integration", "version": "1.0.0"}
            ]
        )
        super().__init__(config)
        
        # Initialize legacy bridge
        self.legacy_bridge = LegacyBridge()
    
    async def _initialize(self) -> None:
        """Initialize agent"""
        await super()._initialize()
        await self.legacy_bridge.start()
    
    async def _stop(self) -> None:
        """Stop agent"""
        await self.legacy_bridge.stop()
        await super()._stop()
    
    async def process_task(self, task: TaskContext) -> TaskResult:
        """Process legacy integration task"""
        try:
            start_time = datetime.utcnow()
            
            if task.task_type == "iso20022_to_legacy":
                # Process ISO 20022 message
                result = await self.legacy_bridge.process_iso20022_to_legacy(
                    task.input_data.get("message"),
                    task.parameters.get("target_system", "mainframe_primary")
                )
                
            elif task.task_type == "rest_to_cics":
                # Process REST to CICS
                result = await self.legacy_bridge.process_rest_to_cics(
                    task.input_data,
                    task.parameters.get("transaction_id"),
                    task.parameters.get("target_system", "mainframe_primary")
                )
                
            elif task.task_type == "copybook_conversion":
                # Convert between copybook and JSON
                if task.parameters.get("direction") == "to_json":
                    result = await self.legacy_bridge.convert_copybook_to_json(
                        task.parameters.get("copybook_name"),
                        task.input_data.get("data")
                    )
                else:
                    result = await self.legacy_bridge.convert_json_to_copybook(
                        task.parameters.get("copybook_name"),
                        task.input_data
                    )
                
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
            return TaskResult(
                task_id=task.task_id,
                status="completed",
                output_data=result,
                start_time=start_time,
                end_time=datetime.utcnow()
            )
            
        except Exception as e:
            self.log_error(f"Task processing failed: {e}")
            return TaskResult(
                task_id=task.task_id,
                status="failed",
                error=str(e),
                start_time=start_time,
                end_time=datetime.utcnow()
            )