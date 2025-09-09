"""
CICS Transaction Gateway Integration

Provides connectivity to IBM CICS (Customer Information Control System) for mainframe transactions.
"""

import asyncio
import socket
import struct
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from velora.core.logging import LoggerMixin
from velora.core.exceptions import IntegrationError


class CICSTransactionType(Enum):
    """CICS transaction types"""
    INQUIRY = "INQ"
    UPDATE = "UPD"
    CREATE = "CRT"
    DELETE = "DEL"
    BATCH = "BAT"


class CICSResponseCode(Enum):
    """CICS response codes"""
    OK = "00"
    NOT_FOUND = "13"
    DUPLICATE = "14"
    INVALID_REQUEST = "16"
    SECURITY_ERROR = "19"
    TIMEOUT = "30"
    SYSTEM_ERROR = "99"


@dataclass
class CICSTransaction:
    """CICS transaction definition"""
    transaction_id: str
    program_name: str
    commarea_length: int
    transaction_type: CICSTransactionType
    timeout: int = 30
    two_phase_commit: bool = False


@dataclass
class CICSRequest:
    """CICS request message"""
    transaction: CICSTransaction
    commarea: bytes
    user_id: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class CICSResponse:
    """CICS response message"""
    response_code: CICSResponseCode
    commarea: bytes
    abend_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class CICSGateway(LoggerMixin):
    """
    CICS Transaction Gateway client for mainframe integration
    """
    
    def __init__(self, host: str, port: int = 2006, encoding: str = "cp037"):
        """
        Initialize CICS Gateway
        
        Args:
            host: CICS gateway host
            port: CICS gateway port (default: 2006)
            encoding: Character encoding (default: EBCDIC cp037)
        """
        self.host = host
        self.port = port
        self.encoding = encoding
        
        # Connection management
        self.socket: Optional[socket.socket] = None
        self.is_connected = False
        
        # Transaction registry
        self.transactions: Dict[str, CICSTransaction] = {}
        
        # z/OS Connect API endpoints (alternative to direct CICS)
        self.zos_connect_endpoints: Dict[str, str] = {}
        
        # Initialize default transactions
        self._initialize_default_transactions()
        
        self.log_info(f"CICS Gateway initialized for {host}:{port}")
    
    def _initialize_default_transactions(self) -> None:
        """Initialize default CICS transactions"""
        # Payment transactions
        self.register_transaction(CICSTransaction(
            transaction_id="PAYM",
            program_name="PAYMENTPG",
            commarea_length=500,
            transaction_type=CICSTransactionType.UPDATE
        ))
        
        # Account inquiry
        self.register_transaction(CICSTransaction(
            transaction_id="AINQ",
            program_name="ACCTINQPG",
            commarea_length=200,
            transaction_type=CICSTransactionType.INQUIRY
        ))
        
        # Balance transfer
        self.register_transaction(CICSTransaction(
            transaction_id="XFER",
            program_name="TRANSFERPG",
            commarea_length=400,
            transaction_type=CICSTransactionType.UPDATE,
            two_phase_commit=True
        ))
    
    def register_transaction(self, transaction: CICSTransaction) -> None:
        """Register a CICS transaction"""
        self.transactions[transaction.transaction_id] = transaction
        self.log_info(f"Registered CICS transaction: {transaction.transaction_id}")
    
    def register_zos_connect_endpoint(self, service_name: str, url: str) -> None:
        """Register z/OS Connect REST API endpoint"""
        self.zos_connect_endpoints[service_name] = url
        self.log_info(f"Registered z/OS Connect endpoint: {service_name} -> {url}")
    
    async def connect(self) -> None:
        """Connect to CICS gateway"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            
            # Connect to CICS gateway
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.socket.connect,
                (self.host, self.port)
            )
            
            self.is_connected = True
            self.log_info(f"Connected to CICS gateway at {self.host}:{self.port}")
            
        except Exception as e:
            self.log_error(f"Failed to connect to CICS gateway: {e}")
            raise IntegrationError(f"CICS connection failed: {str(e)}")
    
    async def disconnect(self) -> None:
        """Disconnect from CICS gateway"""
        if self.socket:
            self.socket.close()
            self.socket = None
        
        self.is_connected = False
        self.log_info("Disconnected from CICS gateway")
    
    async def execute_transaction(
        self,
        transaction_id: str,
        data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a CICS transaction
        
        Args:
            transaction_id: CICS transaction ID
            data: Transaction data
            user_id: Optional user ID for authorization
        
        Returns:
            Transaction response data
        """
        if transaction_id not in self.transactions:
            raise ValueError(f"Unknown transaction: {transaction_id}")
        
        transaction = self.transactions[transaction_id]
        
        # Prepare COMMAREA
        commarea = self._prepare_commarea(transaction, data)
        
        # Create request
        request = CICSRequest(
            transaction=transaction,
            commarea=commarea,
            user_id=user_id,
            correlation_id=self._generate_correlation_id()
        )
        
        # Execute transaction
        response = await self._execute_cics_call(request)
        
        # Parse response
        result = self._parse_response(transaction, response)
        
        return result
    
    def _prepare_commarea(self, transaction: CICSTransaction, data: Dict[str, Any]) -> bytes:
        """Prepare COMMAREA for CICS transaction"""
        commarea = bytearray(transaction.commarea_length)
        
        # Format data based on transaction type
        if transaction.transaction_id == "PAYM":
            # Payment transaction format
            self._format_payment_commarea(commarea, data)
        elif transaction.transaction_id == "AINQ":
            # Account inquiry format
            self._format_inquiry_commarea(commarea, data)
        elif transaction.transaction_id == "XFER":
            # Transfer format
            self._format_transfer_commarea(commarea, data)
        else:
            # Generic format
            self._format_generic_commarea(commarea, data)
        
        return bytes(commarea)
    
    def _format_payment_commarea(self, commarea: bytearray, data: Dict[str, Any]) -> None:
        """Format payment transaction COMMAREA"""
        # Transaction code
        commarea[0:4] = "PAYM".encode(self.encoding)
        
        # Amount (packed decimal, 8 bytes)
        amount = int(data.get("amount", 0) * 100)
        commarea[4:12] = self._pack_decimal(amount, 8)
        
        # Currency (3 bytes)
        currency = data.get("currency", "USD")[:3].ljust(3)
        commarea[12:15] = currency.encode(self.encoding)
        
        # Debtor account (34 bytes)
        debtor_acct = data.get("debtor_account", "")[:34].ljust(34)
        commarea[15:49] = debtor_acct.encode(self.encoding)
        
        # Creditor account (34 bytes)
        creditor_acct = data.get("creditor_account", "")[:34].ljust(34)
        commarea[49:83] = creditor_acct.encode(self.encoding)
        
        # Reference (20 bytes)
        reference = data.get("reference", "")[:20].ljust(20)
        commarea[83:103] = reference.encode(self.encoding)
        
        # Timestamp (14 bytes - YYYYMMDDHHMMSS)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        commarea[103:117] = timestamp.encode(self.encoding)
    
    def _format_inquiry_commarea(self, commarea: bytearray, data: Dict[str, Any]) -> None:
        """Format account inquiry COMMAREA"""
        # Transaction code
        commarea[0:4] = "AINQ".encode(self.encoding)
        
        # Account number (34 bytes)
        account = data.get("account_number", "")[:34].ljust(34)
        commarea[4:38] = account.encode(self.encoding)
        
        # Inquiry type (1 byte)
        inquiry_type = data.get("inquiry_type", "B")  # B=Balance, T=Transactions
        commarea[38:39] = inquiry_type.encode(self.encoding)
    
    def _format_transfer_commarea(self, commarea: bytearray, data: Dict[str, Any]) -> None:
        """Format transfer transaction COMMAREA"""
        # Transaction code
        commarea[0:4] = "XFER".encode(self.encoding)
        
        # Source account (34 bytes)
        source_acct = data.get("source_account", "")[:34].ljust(34)
        commarea[4:38] = source_acct.encode(self.encoding)
        
        # Target account (34 bytes)
        target_acct = data.get("target_account", "")[:34].ljust(34)
        commarea[38:72] = target_acct.encode(self.encoding)
        
        # Amount (packed decimal, 8 bytes)
        amount = int(data.get("amount", 0) * 100)
        commarea[72:80] = self._pack_decimal(amount, 8)
        
        # Currency (3 bytes)
        currency = data.get("currency", "USD")[:3].ljust(3)
        commarea[80:83] = currency.encode(self.encoding)
    
    def _format_generic_commarea(self, commarea: bytearray, data: Dict[str, Any]) -> None:
        """Format generic COMMAREA"""
        # Convert data to string and encode
        data_str = str(data)[:len(commarea)].ljust(len(commarea))
        commarea[:] = data_str.encode(self.encoding)
    
    async def _execute_cics_call(self, request: CICSRequest) -> CICSResponse:
        """Execute actual CICS call"""
        if not self.is_connected:
            await self.connect()
        
        try:
            # Build ECI (External Call Interface) request
            eci_request = self._build_eci_request(request)
            
            # Send request
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.socket.sendall,
                eci_request
            )
            
            # Receive response
            response_data = await asyncio.get_event_loop().run_in_executor(
                None,
                self.socket.recv,
                4096
            )
            
            # Parse ECI response
            response = self._parse_eci_response(response_data, request.correlation_id)
            
            return response
            
        except socket.timeout:
            return CICSResponse(
                response_code=CICSResponseCode.TIMEOUT,
                commarea=b"",
                error_message="Transaction timeout",
                correlation_id=request.correlation_id
            )
        except Exception as e:
            self.log_error(f"CICS call failed: {e}")
            return CICSResponse(
                response_code=CICSResponseCode.SYSTEM_ERROR,
                commarea=b"",
                error_message=str(e),
                correlation_id=request.correlation_id
            )
    
    def _build_eci_request(self, request: CICSRequest) -> bytes:
        """Build ECI request message"""
        # ECI header (simplified)
        header = struct.pack(
            ">4sHH8s8sI",
            b"ECI ",                              # Eye-catcher
            1,                                     # Version
            len(request.commarea),                 # COMMAREA length
            request.transaction.transaction_id.encode(self.encoding).ljust(8),
            request.transaction.program_name.encode(self.encoding).ljust(8),
            request.transaction.timeout
        )
        
        # Add user ID if provided
        if request.user_id:
            user_id_bytes = request.user_id.encode(self.encoding).ljust(8)
        else:
            user_id_bytes = b"DEFAULT "
        
        # Combine header, user ID, and COMMAREA
        eci_request = header + user_id_bytes + request.commarea
        
        return eci_request
    
    def _parse_eci_response(self, response_data: bytes, correlation_id: str) -> CICSResponse:
        """Parse ECI response message"""
        if len(response_data) < 20:
            return CICSResponse(
                response_code=CICSResponseCode.SYSTEM_ERROR,
                commarea=b"",
                error_message="Invalid response",
                correlation_id=correlation_id
            )
        
        # Parse header (simplified)
        eye_catcher, version, response_code, abend_code = struct.unpack(
            ">4sHH4s",
            response_data[:12]
        )
        
        # Get COMMAREA from response
        commarea = response_data[20:] if len(response_data) > 20 else b""
        
        # Map response code
        if response_code == 0:
            cics_response_code = CICSResponseCode.OK
        else:
            cics_response_code = CICSResponseCode.SYSTEM_ERROR
        
        # Decode abend code
        abend_code_str = abend_code.decode(self.encoding).strip() if abend_code != b"\x00\x00\x00\x00" else None
        
        return CICSResponse(
            response_code=cics_response_code,
            commarea=commarea,
            abend_code=abend_code_str,
            correlation_id=correlation_id
        )
    
    def _parse_response(self, transaction: CICSTransaction, response: CICSResponse) -> Dict[str, Any]:
        """Parse CICS response based on transaction type"""
        if response.response_code != CICSResponseCode.OK:
            return {
                "success": False,
                "error_code": response.response_code.value,
                "error_message": response.error_message or "Transaction failed",
                "abend_code": response.abend_code
            }
        
        # Parse based on transaction type
        if transaction.transaction_id == "PAYM":
            return self._parse_payment_response(response.commarea)
        elif transaction.transaction_id == "AINQ":
            return self._parse_inquiry_response(response.commarea)
        elif transaction.transaction_id == "XFER":
            return self._parse_transfer_response(response.commarea)
        else:
            return {
                "success": True,
                "data": response.commarea.decode(self.encoding, errors='ignore').strip()
            }
    
    def _parse_payment_response(self, commarea: bytes) -> Dict[str, Any]:
        """Parse payment transaction response"""
        if len(commarea) < 50:
            return {"success": False, "error": "Invalid response"}
        
        return {
            "success": True,
            "transaction_id": commarea[0:20].decode(self.encoding).strip(),
            "status": commarea[20:22].decode(self.encoding).strip(),
            "authorization_code": commarea[22:32].decode(self.encoding).strip(),
            "timestamp": commarea[32:46].decode(self.encoding).strip()
        }
    
    def _parse_inquiry_response(self, commarea: bytes) -> Dict[str, Any]:
        """Parse account inquiry response"""
        if len(commarea) < 100:
            return {"success": False, "error": "Invalid response"}
        
        # Unpack balance (packed decimal)
        balance_bytes = commarea[38:46]
        balance = self._unpack_decimal(balance_bytes) / 100
        
        return {
            "success": True,
            "account_number": commarea[0:34].decode(self.encoding).strip(),
            "account_status": commarea[34:36].decode(self.encoding).strip(),
            "balance": balance,
            "currency": commarea[46:49].decode(self.encoding).strip(),
            "last_transaction_date": commarea[49:57].decode(self.encoding).strip()
        }
    
    def _parse_transfer_response(self, commarea: bytes) -> Dict[str, Any]:
        """Parse transfer transaction response"""
        if len(commarea) < 60:
            return {"success": False, "error": "Invalid response"}
        
        return {
            "success": True,
            "transaction_id": commarea[0:20].decode(self.encoding).strip(),
            "status": commarea[20:22].decode(self.encoding).strip(),
            "source_balance": self._unpack_decimal(commarea[22:30]) / 100,
            "target_balance": self._unpack_decimal(commarea[30:38]) / 100,
            "timestamp": commarea[38:52].decode(self.encoding).strip()
        }
    
    def _pack_decimal(self, value: int, length: int) -> bytes:
        """Pack integer into packed decimal format"""
        # Convert to string with appropriate length
        str_value = str(abs(value)).zfill(length * 2 - 1)
        
        packed = bytearray()
        for i in range(0, len(str_value) - 1, 2):
            high = int(str_value[i])
            low = int(str_value[i + 1])
            packed.append((high << 4) | low)
        
        # Add sign nibble
        last_digit = int(str_value[-1])
        sign = 0xC if value >= 0 else 0xD
        packed.append((last_digit << 4) | sign)
        
        # Pad to required length
        while len(packed) < length:
            packed.insert(0, 0)
        
        return bytes(packed[:length])
    
    def _unpack_decimal(self, packed: bytes) -> int:
        """Unpack packed decimal format"""
        digits = []
        
        for byte in packed[:-1]:
            digits.append(byte >> 4)
            digits.append(byte & 0x0F)
        
        # Last byte contains digit and sign
        last_byte = packed[-1]
        digits.append(last_byte >> 4)
        sign = last_byte & 0x0F
        
        # Convert to integer
        value = int(''.join(str(d) for d in digits))
        
        # Apply sign
        if sign == 0xD:
            value = -value
        
        return value
    
    def _generate_correlation_id(self) -> str:
        """Generate correlation ID for request tracking"""
        import uuid
        return str(uuid.uuid4())[:20]
    
    async def call_zos_connect_api(
        self,
        service_name: str,
        operation: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call z/OS Connect REST API as alternative to direct CICS
        
        Args:
            service_name: Service name
            operation: Operation name
            data: Request data
        
        Returns:
            Response data
        """
        if service_name not in self.zos_connect_endpoints:
            raise ValueError(f"Unknown z/OS Connect service: {service_name}")
        
        import httpx
        
        url = f"{self.zos_connect_endpoints[service_name]}/{operation}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise IntegrationError(
                    f"z/OS Connect API call failed: {response.status_code} - {response.text}"
                )