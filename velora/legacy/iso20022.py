"""
ISO 20022 Message Handler for Banking Transactions

ISO 20022 is the universal financial industry message scheme.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from velora.core.logging import LoggerMixin
from velora.core.exceptions import ValidationError


class ISO20022MessageType(Enum):
    """Common ISO 20022 message types"""
    # Payment Initiation
    PAIN_001 = "pain.001"  # Customer Credit Transfer Initiation
    PAIN_002 = "pain.002"  # Payment Status Report
    PAIN_008 = "pain.008"  # Customer Direct Debit Initiation
    
    # Payment Clearing and Settlement
    PACS_008 = "pacs.008"  # FI to FI Customer Credit Transfer
    PACS_004 = "pacs.004"  # Payment Return
    PACS_002 = "pacs.002"  # Payment Status Report
    
    # Cash Management
    CAMT_053 = "camt.053"  # Bank to Customer Statement
    CAMT_054 = "camt.054"  # Bank to Customer Debit/Credit Notification
    CAMT_056 = "camt.056"  # FI to FI Payment Cancellation Request


@dataclass
class PaymentInstruction:
    """Payment instruction data"""
    instruction_id: str
    end_to_end_id: str
    amount: float
    currency: str
    debtor_account: str
    debtor_name: str
    creditor_account: str
    creditor_name: str
    remittance_info: Optional[str] = None
    execution_date: Optional[datetime] = None
    charge_bearer: str = "SLEV"  # Shared charges


@dataclass
class ISO20022Message:
    """ISO 20022 message container"""
    message_type: ISO20022MessageType
    message_id: str
    creation_date_time: datetime
    initiating_party: str
    group_header: Dict[str, Any]
    payment_instructions: List[PaymentInstruction] = field(default_factory=list)
    supplementary_data: Dict[str, Any] = field(default_factory=dict)


class ISO20022Handler(LoggerMixin):
    """
    Handles ISO 20022 message parsing, validation, and generation
    """
    
    def __init__(self):
        """Initialize ISO 20022 handler"""
        self.namespace = {
            'ns': 'urn:iso:std:iso:20022:tech:xsd:pain.001.001.03'
        }
        
        # Message validators
        self.validators = self._initialize_validators()
        
        # Field mappings for different message types
        self.field_mappings = self._initialize_field_mappings()
        
        self.log_info("ISO 20022 handler initialized")
    
    def _initialize_validators(self) -> Dict[str, Any]:
        """Initialize message validators"""
        return {
            "IBAN": self._validate_iban,
            "BIC": self._validate_bic,
            "amount": self._validate_amount,
            "currency": self._validate_currency
        }
    
    def _initialize_field_mappings(self) -> Dict[str, Dict[str, str]]:
        """Initialize field mappings for message types"""
        return {
            "pain.001": {
                "message_id": "GrpHdr/MsgId",
                "creation_date": "GrpHdr/CreDtTm",
                "initiating_party": "GrpHdr/InitgPty/Nm",
                "number_of_transactions": "GrpHdr/NbOfTxs",
                "control_sum": "GrpHdr/CtrlSum"
            },
            "pacs.008": {
                "message_id": "GrpHdr/MsgId",
                "creation_date": "GrpHdr/CreDtTm",
                "settlement_method": "GrpHdr/SttlmInf/SttlmMtd",
                "instructing_agent": "GrpHdr/InstgAgt/FinInstnId/BIC"
            }
        }
    
    def parse_message(self, xml_content: str) -> ISO20022Message:
        """
        Parse ISO 20022 XML message
        
        Args:
            xml_content: XML message content
        
        Returns:
            Parsed ISO 20022 message
        """
        try:
            root = ET.fromstring(xml_content)
            
            # Detect message type
            message_type = self._detect_message_type(root)
            
            # Parse group header
            group_header = self._parse_group_header(root, message_type)
            
            # Parse payment instructions
            payment_instructions = self._parse_payment_instructions(root, message_type)
            
            # Create message object
            message = ISO20022Message(
                message_type=message_type,
                message_id=group_header.get("message_id"),
                creation_date_time=datetime.fromisoformat(group_header.get("creation_date")),
                initiating_party=group_header.get("initiating_party"),
                group_header=group_header,
                payment_instructions=payment_instructions
            )
            
            self.log_info(f"Parsed ISO 20022 message: {message.message_id}")
            return message
            
        except ET.ParseError as e:
            raise ValidationError(f"Invalid XML: {e}")
        except Exception as e:
            raise ValidationError(f"Failed to parse ISO 20022 message: {e}")
    
    def _detect_message_type(self, root: ET.Element) -> ISO20022MessageType:
        """Detect ISO 20022 message type from XML"""
        # Check root tag for message type
        tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag
        
        for msg_type in ISO20022MessageType:
            if msg_type.value.replace('.', '') in tag.lower():
                return msg_type
        
        raise ValidationError(f"Unknown ISO 20022 message type: {tag}")
    
    def _parse_group_header(self, root: ET.Element, message_type: ISO20022MessageType) -> Dict[str, Any]:
        """Parse group header from ISO 20022 message"""
        header = {}
        
        # Find group header element
        grp_hdr = root.find('.//GrpHdr', self.namespace)
        if grp_hdr is None:
            grp_hdr = root.find('.//GrpHdr')
        
        if grp_hdr is not None:
            header["message_id"] = self._get_text(grp_hdr, 'MsgId')
            header["creation_date"] = self._get_text(grp_hdr, 'CreDtTm')
            header["number_of_transactions"] = self._get_text(grp_hdr, 'NbOfTxs')
            header["control_sum"] = self._get_text(grp_hdr, 'CtrlSum')
            
            # Initiating party
            initg_pty = grp_hdr.find('.//InitgPty')
            if initg_pty is not None:
                header["initiating_party"] = self._get_text(initg_pty, 'Nm')
        
        return header
    
    def _parse_payment_instructions(self, root: ET.Element, message_type: ISO20022MessageType) -> List[PaymentInstruction]:
        """Parse payment instructions from ISO 20022 message"""
        instructions = []
        
        # Find payment information elements
        pmt_inf_elements = root.findall('.//PmtInf')
        
        for pmt_inf in pmt_inf_elements:
            # Parse credit transfer transactions
            cdt_trf_tx_inf_elements = pmt_inf.findall('.//CdtTrfTxInf')
            
            for tx_inf in cdt_trf_tx_inf_elements:
                instruction = self._parse_transaction(tx_inf)
                if instruction:
                    instructions.append(instruction)
        
        return instructions
    
    def _parse_transaction(self, tx_element: ET.Element) -> Optional[PaymentInstruction]:
        """Parse individual transaction"""
        try:
            # Payment identification
            pmt_id = tx_element.find('.//PmtId')
            instruction_id = self._get_text(pmt_id, 'InstrId')
            end_to_end_id = self._get_text(pmt_id, 'EndToEndId')
            
            # Amount
            amt_element = tx_element.find('.//Amt/InstdAmt')
            if amt_element is not None:
                amount = float(amt_element.text)
                currency = amt_element.get('Ccy')
            else:
                amount = 0.0
                currency = "EUR"
            
            # Debtor
            dbtr = tx_element.find('.//Dbtr')
            debtor_name = self._get_text(dbtr, 'Nm') if dbtr is not None else ""
            dbtr_acct = tx_element.find('.//DbtrAcct/Id/IBAN')
            debtor_account = dbtr_acct.text if dbtr_acct is not None else ""
            
            # Creditor
            cdtr = tx_element.find('.//Cdtr')
            creditor_name = self._get_text(cdtr, 'Nm') if cdtr is not None else ""
            cdtr_acct = tx_element.find('.//CdtrAcct/Id/IBAN')
            creditor_account = cdtr_acct.text if cdtr_acct is not None else ""
            
            # Remittance information
            rmt_inf = tx_element.find('.//RmtInf/Ustrd')
            remittance_info = rmt_inf.text if rmt_inf is not None else None
            
            return PaymentInstruction(
                instruction_id=instruction_id or "",
                end_to_end_id=end_to_end_id or "",
                amount=amount,
                currency=currency,
                debtor_account=debtor_account,
                debtor_name=debtor_name,
                creditor_account=creditor_account,
                creditor_name=creditor_name,
                remittance_info=remittance_info
            )
            
        except Exception as e:
            self.log_error(f"Failed to parse transaction: {e}")
            return None
    
    def generate_message(self, message: ISO20022Message) -> str:
        """
        Generate ISO 20022 XML message
        
        Args:
            message: ISO 20022 message object
        
        Returns:
            XML string
        """
        # Create root element based on message type
        namespace = f"urn:iso:std:iso:20022:tech:xsd:{message.message_type.value}.001.03"
        root = ET.Element(f"{{{namespace}}}Document")
        
        # Create message type element
        msg_element = ET.SubElement(root, message.message_type.value.replace('.', ''))
        
        # Add group header
        grp_hdr = ET.SubElement(msg_element, "GrpHdr")
        ET.SubElement(grp_hdr, "MsgId").text = message.message_id
        ET.SubElement(grp_hdr, "CreDtTm").text = message.creation_date_time.isoformat()
        ET.SubElement(grp_hdr, "NbOfTxs").text = str(len(message.payment_instructions))
        
        # Calculate control sum
        control_sum = sum(instr.amount for instr in message.payment_instructions)
        ET.SubElement(grp_hdr, "CtrlSum").text = f"{control_sum:.2f}"
        
        # Add initiating party
        initg_pty = ET.SubElement(grp_hdr, "InitgPty")
        ET.SubElement(initg_pty, "Nm").text = message.initiating_party
        
        # Add payment information
        if message.payment_instructions:
            pmt_inf = ET.SubElement(msg_element, "PmtInf")
            
            for instruction in message.payment_instructions:
                self._add_payment_instruction(pmt_inf, instruction)
        
        # Convert to string
        xml_str = ET.tostring(root, encoding='unicode', method='xml')
        
        self.log_info(f"Generated ISO 20022 message: {message.message_id}")
        return xml_str
    
    def _add_payment_instruction(self, parent: ET.Element, instruction: PaymentInstruction) -> None:
        """Add payment instruction to XML"""
        cdt_trf_tx_inf = ET.SubElement(parent, "CdtTrfTxInf")
        
        # Payment ID
        pmt_id = ET.SubElement(cdt_trf_tx_inf, "PmtId")
        ET.SubElement(pmt_id, "InstrId").text = instruction.instruction_id
        ET.SubElement(pmt_id, "EndToEndId").text = instruction.end_to_end_id
        
        # Amount
        amt = ET.SubElement(cdt_trf_tx_inf, "Amt")
        instd_amt = ET.SubElement(amt, "InstdAmt", Ccy=instruction.currency)
        instd_amt.text = f"{instruction.amount:.2f}"
        
        # Debtor
        dbtr = ET.SubElement(cdt_trf_tx_inf, "Dbtr")
        ET.SubElement(dbtr, "Nm").text = instruction.debtor_name
        dbtr_acct = ET.SubElement(cdt_trf_tx_inf, "DbtrAcct")
        dbtr_id = ET.SubElement(dbtr_acct, "Id")
        ET.SubElement(dbtr_id, "IBAN").text = instruction.debtor_account
        
        # Creditor
        cdtr = ET.SubElement(cdt_trf_tx_inf, "Cdtr")
        ET.SubElement(cdtr, "Nm").text = instruction.creditor_name
        cdtr_acct = ET.SubElement(cdt_trf_tx_inf, "CdtrAcct")
        cdtr_id = ET.SubElement(cdtr_acct, "Id")
        ET.SubElement(cdtr_id, "IBAN").text = instruction.creditor_account
        
        # Remittance information
        if instruction.remittance_info:
            rmt_inf = ET.SubElement(cdt_trf_tx_inf, "RmtInf")
            ET.SubElement(rmt_inf, "Ustrd").text = instruction.remittance_info
    
    def _get_text(self, element: Optional[ET.Element], tag: str) -> Optional[str]:
        """Get text from child element"""
        if element is None:
            return None
        child = element.find(tag)
        return child.text if child is not None else None
    
    def _validate_iban(self, iban: str) -> bool:
        """Validate IBAN format"""
        # Basic IBAN validation (simplified)
        iban = iban.replace(' ', '').upper()
        if len(iban) < 15 or len(iban) > 34:
            return False
        # More validation logic would go here
        return True
    
    def _validate_bic(self, bic: str) -> bool:
        """Validate BIC/SWIFT code"""
        # BIC is 8 or 11 characters
        return len(bic) in [8, 11] and bic.isalnum()
    
    def _validate_amount(self, amount: float) -> bool:
        """Validate amount"""
        return amount > 0
    
    def _validate_currency(self, currency: str) -> bool:
        """Validate currency code"""
        # ISO 4217 currency codes are 3 letters
        return len(currency) == 3 and currency.isalpha()
    
    def convert_to_cobol_format(self, message: ISO20022Message) -> Dict[str, Any]:
        """
        Convert ISO 20022 message to COBOL-friendly format
        
        Args:
            message: ISO 20022 message
        
        Returns:
            Dictionary with COBOL-compatible field names and formats
        """
        cobol_data = {
            "MSG-ID": message.message_id[:20],  # COBOL typically has fixed-length fields
            "CREATE-DATE": message.creation_date_time.strftime("%Y%m%d"),
            "CREATE-TIME": message.creation_date_time.strftime("%H%M%S"),
            "INIT-PARTY": message.initiating_party[:35],
            "NUM-TRANS": f"{len(message.payment_instructions):05d}",
            "TRANSACTIONS": []
        }
        
        for i, instruction in enumerate(message.payment_instructions[:99]):  # Limit to 99 transactions
            trans_data = {
                "TRANS-NUM": f"{i+1:03d}",
                "INSTR-ID": instruction.instruction_id[:16],
                "END-TO-END": instruction.end_to_end_id[:16],
                "AMOUNT": f"{int(instruction.amount * 100):015d}",  # Store as cents
                "CURRENCY": instruction.currency,
                "DEBTOR-ACCT": instruction.debtor_account[:34],
                "DEBTOR-NAME": instruction.debtor_name[:35],
                "CREDITOR-ACCT": instruction.creditor_account[:34],
                "CREDITOR-NAME": instruction.creditor_name[:35],
                "REMIT-INFO": (instruction.remittance_info or "")[:140]
            }
            cobol_data["TRANSACTIONS"].append(trans_data)
        
        return cobol_data