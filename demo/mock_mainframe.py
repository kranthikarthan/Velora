#!/usr/bin/env python3
"""
Mock Mainframe Simulator
Simulates CICS transactions and mainframe responses for demo
"""

import asyncio
import socket
import struct
import random
import time
from datetime import datetime
from typing import Dict, Any, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockMainframe:
    """
    Simulates a mainframe with CICS transaction processing
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 2006):
        self.host = host
        self.port = port
        self.server = None
        self.is_running = False
        
        # Transaction statistics
        self.transactions_processed = 0
        self.total_processing_time = 0
        
        # Simulated accounts database
        self.accounts = {
            "US12345678901234567890": {
                "balance": 50000.00,
                "currency": "USD",
                "status": "ACTIVE",
                "name": "John Smith"
            },
            "US98765432109876543210": {
                "balance": 100000.00,
                "currency": "USD",
                "status": "ACTIVE",
                "name": "ABC Corporation"
            }
        }
        
        # CICS transaction handlers
        self.transaction_handlers = {
            "PAYM": self.handle_payment_transaction,
            "AINQ": self.handle_account_inquiry,
            "XFER": self.handle_transfer_transaction,
            "BALN": self.handle_balance_inquiry
        }
    
    async def start(self):
        """Start the mock mainframe server"""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        self.is_running = True
        addr = self.server.sockets[0].getsockname()
        logger.info(f"🖥️ Mock Mainframe started on {addr[0]}:{addr[1]}")
        logger.info(f"   Simulating CICS Gateway on port {self.port}")
        logger.info(f"   Ready to process transactions...")
        
        async with self.server:
            await self.server.serve_forever()
    
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming CICS connection"""
        addr = writer.get_extra_info('peername')
        logger.info(f"📡 Connection from {addr}")
        
        try:
            while True:
                # Read ECI request header (32 bytes)
                header_data = await reader.read(32)
                if not header_data:
                    break
                
                # Parse ECI header
                eye_catcher = header_data[0:4].decode('ascii', errors='ignore')
                version = struct.unpack('>H', header_data[4:6])[0]
                commarea_length = struct.unpack('>H', header_data[6:8])[0]
                transaction_id = header_data[8:16].decode('ascii', errors='ignore').strip()
                program_name = header_data[16:24].decode('ascii', errors='ignore').strip()
                
                logger.info(f"📥 Transaction: {transaction_id}, Program: {program_name}, COMMAREA: {commarea_length} bytes")
                
                # Read COMMAREA
                commarea = await reader.read(commarea_length)
                
                # Process transaction
                start_time = time.time()
                response = await self.process_transaction(transaction_id, commarea)
                processing_time = (time.time() - start_time) * 1000
                
                # Update statistics
                self.transactions_processed += 1
                self.total_processing_time += processing_time
                
                logger.info(f"✅ Transaction processed in {processing_time:.2f}ms")
                
                # Send response
                writer.write(response)
                await writer.drain()
        
        except Exception as e:
            logger.error(f"❌ Error handling client: {e}")
        
        finally:
            writer.close()
            await writer.wait_closed()
            logger.info(f"🔌 Connection closed from {addr}")
    
    async def process_transaction(self, transaction_id: str, commarea: bytes) -> bytes:
        """Process a CICS transaction"""
        
        # Simulate processing delay (50-200ms like real mainframe)
        delay = random.uniform(0.05, 0.2)
        await asyncio.sleep(delay)
        
        # Get handler for transaction
        handler = self.transaction_handlers.get(transaction_id, self.handle_unknown_transaction)
        
        # Process transaction
        response_data = await handler(commarea)
        
        # Build ECI response
        response = self.build_eci_response(transaction_id, response_data)
        
        return response
    
    async def handle_payment_transaction(self, commarea: bytes) -> Tuple[int, bytes]:
        """Handle PAYM - Payment transaction"""
        logger.info("💰 Processing payment transaction")
        
        # Parse payment data (simplified)
        # In real scenario, would parse COBOL copybook format
        
        # Simulate successful payment
        transaction_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}"
        auth_code = f"AUTH{random.randint(100000, 999999)}"
        
        # Build response COMMAREA
        response = bytearray(500)
        
        # Transaction ID (20 bytes)
        response[0:20] = transaction_id.encode('ascii').ljust(20)
        
        # Status code (2 bytes) - "00" = success
        response[20:22] = b"00"
        
        # Authorization code (10 bytes)
        response[22:32] = auth_code.encode('ascii').ljust(10)
        
        # Timestamp (14 bytes)
        response[32:46] = datetime.now().strftime("%Y%m%d%H%M%S").encode('ascii')
        
        # Response message (50 bytes)
        response[46:96] = b"Payment processed successfully".ljust(50)
        
        return (0, bytes(response))
    
    async def handle_account_inquiry(self, commarea: bytes) -> Tuple[int, bytes]:
        """Handle AINQ - Account inquiry transaction"""
        logger.info("🔍 Processing account inquiry")
        
        # Parse account number from COMMAREA
        account_number = commarea[4:38].decode('ascii', errors='ignore').strip()
        
        # Look up account
        account = self.accounts.get(account_number, {
            "balance": 0.00,
            "currency": "USD",
            "status": "NOT_FOUND",
            "name": "Unknown"
        })
        
        # Build response
        response = bytearray(200)
        
        # Account number (34 bytes)
        response[0:34] = account_number.encode('ascii').ljust(34)
        
        # Account status (2 bytes)
        status = "01" if account["status"] == "ACTIVE" else "99"
        response[34:36] = status.encode('ascii')
        
        # Balance (8 bytes packed decimal)
        balance_packed = self.pack_decimal(int(account["balance"] * 100))
        response[38:46] = balance_packed
        
        # Currency (3 bytes)
        response[46:49] = account["currency"].encode('ascii')
        
        # Last transaction date (8 bytes)
        response[49:57] = datetime.now().strftime("%Y%m%d").encode('ascii')
        
        return (0, bytes(response))
    
    async def handle_transfer_transaction(self, commarea: bytes) -> Tuple[int, bytes]:
        """Handle XFER - Transfer transaction"""
        logger.info("💸 Processing transfer transaction")
        
        # Simulate transfer processing
        transaction_id = f"XFR{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Build response
        response = bytearray(400)
        
        # Transaction ID
        response[0:20] = transaction_id.encode('ascii').ljust(20)
        
        # Status
        response[20:22] = b"00"  # Success
        
        # Source balance (simulate)
        response[22:30] = self.pack_decimal(4850000)  # $48,500.00
        
        # Target balance (simulate)
        response[30:38] = self.pack_decimal(10150000)  # $101,500.00
        
        # Timestamp
        response[38:52] = datetime.now().strftime("%Y%m%d%H%M%S").encode('ascii')
        
        return (0, bytes(response))
    
    async def handle_balance_inquiry(self, commarea: bytes) -> Tuple[int, bytes]:
        """Handle BALN - Balance inquiry"""
        logger.info("💵 Processing balance inquiry")
        
        # Simple balance response
        response = bytearray(100)
        
        # Balance amount
        balance = random.randint(10000, 1000000)
        response[0:8] = self.pack_decimal(balance)
        
        # Currency
        response[8:11] = b"USD"
        
        # Available balance
        response[11:19] = self.pack_decimal(int(balance * 0.9))
        
        return (0, bytes(response))
    
    async def handle_unknown_transaction(self, commarea: bytes) -> Tuple[int, bytes]:
        """Handle unknown transaction"""
        logger.warning(f"⚠️ Unknown transaction type")
        
        # Return error response
        response = bytearray(100)
        response[0:2] = b"99"  # Error code
        response[2:52] = b"Unknown transaction type".ljust(50)
        
        return (99, bytes(response))
    
    def build_eci_response(self, transaction_id: str, response_data: Tuple[int, bytes]) -> bytes:
        """Build ECI response message"""
        response_code, commarea = response_data
        
        # Build header
        header = bytearray(32)
        
        # Eye-catcher
        header[0:4] = b"ECI "
        
        # Version
        header[4:6] = struct.pack('>H', 1)
        
        # Response code
        header[6:7] = struct.pack('B', response_code)
        
        # Abend code (4 bytes)
        if response_code != 0:
            header[8:12] = b"ABND"
        else:
            header[8:12] = b"\x00\x00\x00\x00"
        
        # Transaction ID
        header[12:20] = transaction_id.encode('ascii').ljust(8)
        
        # Combine header and COMMAREA
        return bytes(header) + commarea
    
    def pack_decimal(self, value: int, length: int = 8) -> bytes:
        """Pack integer into COMP-3 format"""
        # Convert to string with appropriate length
        digits = str(abs(value)).zfill(length * 2 - 1)
        
        packed = bytearray()
        
        # Pack pairs of digits
        for i in range(0, len(digits) - 1, 2):
            high = int(digits[i])
            low = int(digits[i + 1])
            packed.append((high << 4) | low)
        
        # Add sign nibble
        last_digit = int(digits[-1])
        sign = 0xC if value >= 0 else 0xD
        packed.append((last_digit << 4) | sign)
        
        # Pad to required length
        while len(packed) < length:
            packed.insert(0, 0)
        
        return bytes(packed[:length])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get mainframe statistics"""
        avg_time = 0
        if self.transactions_processed > 0:
            avg_time = self.total_processing_time / self.transactions_processed
        
        return {
            "transactions_processed": self.transactions_processed,
            "average_processing_time_ms": round(avg_time, 2),
            "accounts": len(self.accounts),
            "status": "online" if self.is_running else "offline"
        }


async def main():
    """Run the mock mainframe"""
    print("\n" + "="*60)
    print("🖥️ MOCK MAINFRAME SIMULATOR")
    print("="*60)
    print("Simulating IBM z/OS with CICS Transaction Gateway")
    print("Ready to process banking transactions...")
    print("="*60 + "\n")
    
    mainframe = MockMainframe()
    
    try:
        await mainframe.start()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down mock mainframe...")
        stats = mainframe.get_statistics()
        print(f"\n📊 Statistics:")
        print(f"   Transactions: {stats['transactions_processed']}")
        print(f"   Avg Time: {stats['average_processing_time_ms']}ms")


if __name__ == "__main__":
    asyncio.run(main())