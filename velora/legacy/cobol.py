"""
COBOL Copybook Parser and Data Handler

Handles COBOL copybook layouts and data conversion for mainframe integration.
"""

import re
import struct
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum

from velora.core.logging import LoggerMixin
from velora.core.exceptions import ValidationError


class COBOLDataType(Enum):
    """COBOL data types"""
    ALPHANUMERIC = "X"  # Character data
    NUMERIC = "9"       # Numeric data
    SIGNED = "S9"       # Signed numeric
    PACKED = "COMP-3"   # Packed decimal
    BINARY = "COMP"     # Binary
    FLOAT = "COMP-1"    # Single precision float
    DOUBLE = "COMP-2"   # Double precision float


@dataclass
class COBOLField:
    """COBOL field definition"""
    level: int
    name: str
    picture: str
    usage: Optional[str] = None
    occurs: Optional[int] = None
    redefines: Optional[str] = None
    value: Optional[str] = None
    offset: int = 0
    length: int = 0
    data_type: Optional[COBOLDataType] = None
    children: List['COBOLField'] = field(default_factory=list)


@dataclass
class COBOLCopybook:
    """COBOL copybook structure"""
    name: str
    fields: List[COBOLField]
    record_length: int
    encoding: str = "cp037"  # EBCDIC encoding


class COBOLCopybookParser(LoggerMixin):
    """
    Parses COBOL copybooks and handles data conversion
    """
    
    def __init__(self, encoding: str = "cp037"):
        """
        Initialize COBOL parser
        
        Args:
            encoding: Character encoding (default: EBCDIC cp037)
        """
        self.encoding = encoding
        self.copybooks: Dict[str, COBOLCopybook] = {}
        
        # COBOL picture clause patterns
        self.picture_patterns = {
            r'X\((\d+)\)': (COBOLDataType.ALPHANUMERIC, lambda n: int(n)),
            r'X{1,}': (COBOLDataType.ALPHANUMERIC, lambda s: len(s)),
            r'9\((\d+)\)': (COBOLDataType.NUMERIC, lambda n: int(n)),
            r'9{1,}': (COBOLDataType.NUMERIC, lambda s: len(s)),
            r'S9\((\d+)\)': (COBOLDataType.SIGNED, lambda n: int(n)),
            r'9\((\d+)\)V9\((\d+)\)': (COBOLDataType.NUMERIC, self._parse_decimal),
            r'S9\((\d+)\)V9\((\d+)\)': (COBOLDataType.SIGNED, self._parse_decimal),
        }
        
        self.log_info("COBOL copybook parser initialized")
    
    def parse_copybook(self, copybook_content: str, name: str = "DEFAULT") -> COBOLCopybook:
        """
        Parse COBOL copybook definition
        
        Args:
            copybook_content: COBOL copybook text
            name: Copybook name
        
        Returns:
            Parsed copybook structure
        """
        lines = copybook_content.strip().split('\n')
        fields = []
        current_offset = 0
        
        for line in lines:
            field = self._parse_field_definition(line.strip())
            if field:
                # Calculate offset and length
                field.offset = current_offset
                field.length = self._calculate_field_length(field)
                current_offset += field.length
                
                fields.append(field)
        
        # Build field hierarchy
        root_fields = self._build_hierarchy(fields)
        
        copybook = COBOLCopybook(
            name=name,
            fields=root_fields,
            record_length=current_offset,
            encoding=self.encoding
        )
        
        self.copybooks[name] = copybook
        self.log_info(f"Parsed copybook '{name}' with {len(fields)} fields, record length: {current_offset}")
        
        return copybook
    
    def _parse_field_definition(self, line: str) -> Optional[COBOLField]:
        """Parse a single COBOL field definition line"""
        if not line or line.startswith('*'):  # Skip comments
            return None
        
        # Basic COBOL field pattern: level number, name, PIC clause
        pattern = r'(\d{2})\s+([A-Z0-9-]+)\s+(?:PIC|PICTURE)\s+(?:IS\s+)?([X9SV\(\)\.]+)(?:\s+USAGE\s+(?:IS\s+)?([A-Z0-9-]+))?'
        match = re.match(pattern, line, re.IGNORECASE)
        
        if not match:
            # Try simpler pattern for group items
            pattern = r'(\d{2})\s+([A-Z0-9-]+)'
            match = re.match(pattern, line, re.IGNORECASE)
            if not match:
                return None
            
            return COBOLField(
                level=int(match.group(1)),
                name=match.group(2),
                picture=""
            )
        
        field = COBOLField(
            level=int(match.group(1)),
            name=match.group(2),
            picture=match.group(3),
            usage=match.group(4) if len(match.groups()) > 3 else None
        )
        
        # Parse additional clauses
        if 'OCCURS' in line:
            occurs_match = re.search(r'OCCURS\s+(\d+)', line, re.IGNORECASE)
            if occurs_match:
                field.occurs = int(occurs_match.group(1))
        
        if 'REDEFINES' in line:
            redefines_match = re.search(r'REDEFINES\s+([A-Z0-9-]+)', line, re.IGNORECASE)
            if redefines_match:
                field.redefines = redefines_match.group(1)
        
        if 'VALUE' in line:
            value_match = re.search(r'VALUE\s+(?:IS\s+)?([\'"]?)([^\'"]*)\\1', line, re.IGNORECASE)
            if value_match:
                field.value = value_match.group(2)
        
        # Determine data type
        field.data_type = self._determine_data_type(field)
        
        return field
    
    def _determine_data_type(self, field: COBOLField) -> Optional[COBOLDataType]:
        """Determine COBOL data type from picture clause"""
        if not field.picture:
            return None
        
        picture = field.picture.upper()
        
        if field.usage:
            usage = field.usage.upper()
            if 'COMP-3' in usage:
                return COBOLDataType.PACKED
            elif 'COMP-2' in usage:
                return COBOLDataType.DOUBLE
            elif 'COMP-1' in usage:
                return COBOLDataType.FLOAT
            elif 'COMP' in usage:
                return COBOLDataType.BINARY
        
        if 'X' in picture:
            return COBOLDataType.ALPHANUMERIC
        elif 'S' in picture:
            return COBOLDataType.SIGNED
        elif '9' in picture:
            return COBOLDataType.NUMERIC
        
        return None
    
    def _calculate_field_length(self, field: COBOLField) -> int:
        """Calculate field length in bytes"""
        if not field.picture:
            return 0
        
        picture = field.picture.upper()
        
        # Handle different data types
        if field.data_type == COBOLDataType.PACKED:
            # Packed decimal: (digits + 1) / 2
            digits = self._count_digits(picture)
            return (digits + 1) // 2
        
        elif field.data_type == COBOLDataType.BINARY:
            digits = self._count_digits(picture)
            if digits <= 4:
                return 2  # SMALLINT
            elif digits <= 9:
                return 4  # INTEGER
            else:
                return 8  # BIGINT
        
        elif field.data_type == COBOLDataType.FLOAT:
            return 4
        
        elif field.data_type == COBOLDataType.DOUBLE:
            return 8
        
        else:
            # Character or display numeric
            length = 0
            
            # Parse picture clause
            for pattern, (dtype, calc) in self.picture_patterns.items():
                match = re.match(pattern, picture)
                if match:
                    if match.groups():
                        length = calc(*match.groups())
                    else:
                        length = calc(picture)
                    break
            
            if length == 0:
                # Simple count of X or 9
                length = len(re.findall(r'[X9]', picture))
            
            # Apply OCCURS clause
            if field.occurs:
                length *= field.occurs
            
            return length
    
    def _count_digits(self, picture: str) -> int:
        """Count total digits in picture clause"""
        count = 0
        
        # Handle 9(n) notation
        match = re.search(r'9\((\d+)\)', picture)
        if match:
            count += int(match.group(1))
        
        # Count individual 9s
        count += len(re.findall(r'9(?!\()', picture))
        
        # Handle decimal places
        if 'V' in picture:
            # V doesn't take space but indicates decimal position
            pass
        
        return count
    
    def _parse_decimal(self, *args) -> int:
        """Parse decimal picture clause"""
        if len(args) == 2:
            return int(args[0]) + int(args[1])
        return 0
    
    def _build_hierarchy(self, fields: List[COBOLField]) -> List[COBOLField]:
        """Build field hierarchy based on level numbers"""
        if not fields:
            return []
        
        root_fields = []
        stack = []
        
        for field in fields:
            # Find parent based on level
            while stack and stack[-1].level >= field.level:
                stack.pop()
            
            if stack:
                # Add as child to parent
                stack[-1].children.append(field)
            else:
                # Root level field
                root_fields.append(field)
            
            # Add to stack if it might have children
            if field.level < 88:  # Level 88 is condition name
                stack.append(field)
        
        return root_fields
    
    def parse_data(self, copybook_name: str, data: bytes) -> Dict[str, Any]:
        """
        Parse binary data using copybook definition
        
        Args:
            copybook_name: Name of copybook to use
            data: Binary data to parse
        
        Returns:
            Parsed data as dictionary
        """
        if copybook_name not in self.copybooks:
            raise ValueError(f"Copybook '{copybook_name}' not found")
        
        copybook = self.copybooks[copybook_name]
        result = {}
        
        for field in copybook.fields:
            value = self._extract_field_value(field, data, copybook.encoding)
            result[field.name] = value
        
        return result
    
    def _extract_field_value(self, field: COBOLField, data: bytes, encoding: str) -> Any:
        """Extract field value from binary data"""
        if field.children:
            # Group item - process children
            result = {}
            for child in field.children:
                result[child.name] = self._extract_field_value(child, data, encoding)
            return result
        
        # Extract bytes for this field
        field_data = data[field.offset:field.offset + field.length]
        
        if not field_data:
            return None
        
        # Convert based on data type
        if field.data_type == COBOLDataType.ALPHANUMERIC:
            # Convert from EBCDIC to ASCII
            try:
                value = field_data.decode(encoding).strip()
            except:
                value = field_data.decode('latin-1').strip()
            return value
        
        elif field.data_type == COBOLDataType.NUMERIC:
            # Display numeric - stored as characters
            try:
                numeric_str = field_data.decode(encoding)
                # Handle decimal point
                if 'V' in field.picture:
                    # Insert decimal point
                    decimal_pos = field.picture.index('V')
                    integer_part = numeric_str[:decimal_pos]
                    decimal_part = numeric_str[decimal_pos:]
                    value = float(f"{integer_part}.{decimal_part}")
                else:
                    value = int(numeric_str)
            except:
                value = 0
            return value
        
        elif field.data_type == COBOLDataType.PACKED:
            # Packed decimal (COMP-3)
            return self._unpack_decimal(field_data)
        
        elif field.data_type == COBOLDataType.BINARY:
            # Binary integer (COMP)
            if field.length == 2:
                return struct.unpack('>h', field_data)[0]
            elif field.length == 4:
                return struct.unpack('>i', field_data)[0]
            elif field.length == 8:
                return struct.unpack('>q', field_data)[0]
            else:
                return 0
        
        return None
    
    def _unpack_decimal(self, packed_data: bytes) -> float:
        """Unpack COMP-3 packed decimal"""
        digits = []
        for byte in packed_data[:-1]:
            digits.append(byte >> 4)
            digits.append(byte & 0x0F)
        
        # Last byte contains last digit and sign
        last_byte = packed_data[-1]
        digits.append(last_byte >> 4)
        sign = last_byte & 0x0F
        
        # Convert to number
        value = int(''.join(str(d) for d in digits))
        
        # Apply sign (0xC = positive, 0xD = negative)
        if sign == 0xD:
            value = -value
        
        return value
    
    def format_data(self, copybook_name: str, data: Dict[str, Any]) -> bytes:
        """
        Format data according to copybook definition
        
        Args:
            copybook_name: Name of copybook to use
            data: Data to format
        
        Returns:
            Formatted binary data
        """
        if copybook_name not in self.copybooks:
            raise ValueError(f"Copybook '{copybook_name}' not found")
        
        copybook = self.copybooks[copybook_name]
        result = bytearray(copybook.record_length)
        
        for field in copybook.fields:
            self._format_field_value(field, data, result, copybook.encoding)
        
        return bytes(result)
    
    def _format_field_value(self, field: COBOLField, data: Dict[str, Any], result: bytearray, encoding: str) -> None:
        """Format field value into binary data"""
        if field.name not in data:
            return
        
        value = data[field.name]
        
        if field.children:
            # Group item - process children
            for child in field.children:
                self._format_field_value(child, value if isinstance(value, dict) else data, result, encoding)
            return
        
        # Format based on data type
        if field.data_type == COBOLDataType.ALPHANUMERIC:
            # Convert to EBCDIC
            str_value = str(value)[:field.length].ljust(field.length)
            field_bytes = str_value.encode(encoding)
            
        elif field.data_type == COBOLDataType.NUMERIC:
            # Display numeric
            if isinstance(value, float):
                # Handle decimal
                str_value = f"{value:.2f}".replace('.', '')
            else:
                str_value = str(int(value))
            
            str_value = str_value.zfill(field.length)[:field.length]
            field_bytes = str_value.encode(encoding)
        
        elif field.data_type == COBOLDataType.PACKED:
            # Pack decimal
            field_bytes = self._pack_decimal(value, field.length)
        
        elif field.data_type == COBOLDataType.BINARY:
            # Binary integer
            if field.length == 2:
                field_bytes = struct.pack('>h', int(value))
            elif field.length == 4:
                field_bytes = struct.pack('>i', int(value))
            elif field.length == 8:
                field_bytes = struct.pack('>q', int(value))
            else:
                field_bytes = bytes(field.length)
        
        else:
            field_bytes = bytes(field.length)
        
        # Copy to result buffer
        result[field.offset:field.offset + len(field_bytes)] = field_bytes
    
    def _pack_decimal(self, value: Union[int, float], length: int) -> bytes:
        """Pack decimal into COMP-3 format"""
        # Convert to integer (multiply by 100 for 2 decimal places)
        int_value = abs(int(value * 100)) if isinstance(value, float) else abs(int(value))
        
        # Convert to string and pad with zeros
        str_value = str(int_value).zfill(length * 2 - 1)
        
        # Pack digits
        packed = bytearray()
        for i in range(0, len(str_value) - 1, 2):
            high_nibble = int(str_value[i])
            low_nibble = int(str_value[i + 1])
            packed.append((high_nibble << 4) | low_nibble)
        
        # Add last digit and sign
        last_digit = int(str_value[-1])
        sign = 0xC if value >= 0 else 0xD
        packed.append((last_digit << 4) | sign)
        
        return bytes(packed)
    
    def create_sample_copybook(self) -> str:
        """Create a sample COBOL copybook for payment transactions"""
        return """
       01  PAYMENT-RECORD.
           05  TRANS-ID            PIC X(20).
           05  TRANS-DATE.
               10  TRANS-YEAR      PIC 9(4).
               10  TRANS-MONTH     PIC 9(2).
               10  TRANS-DAY       PIC 9(2).
           05  TRANS-TIME          PIC 9(6).
           05  AMOUNT              PIC S9(13)V99 COMP-3.
           05  CURRENCY            PIC X(3).
           05  DEBTOR-INFO.
               10  DEBTOR-ACCT     PIC X(34).
               10  DEBTOR-NAME     PIC X(35).
               10  DEBTOR-BANK     PIC X(11).
           05  CREDITOR-INFO.
               10  CREDITOR-ACCT   PIC X(34).
               10  CREDITOR-NAME   PIC X(35).
               10  CREDITOR-BANK   PIC X(11).
           05  REMIT-INFO          PIC X(140).
           05  STATUS-CODE         PIC X(2).
           05  ERROR-MSG           PIC X(50).
           05  FILLER              PIC X(50).
        """