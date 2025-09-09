"""
Encryption and cryptographic operations for Velora
"""

import os
import secrets
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime, timedelta

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ed25519, x25519
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

from velora.core.logging import LoggerMixin
from velora.core.exceptions import SecurityError


@dataclass
class KeyPair:
    """Cryptographic key pair"""
    private_key: Any
    public_key: Any
    key_type: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    key_id: Optional[str] = None


@dataclass
class EncryptedData:
    """Encrypted data container"""
    ciphertext: bytes
    nonce: Optional[bytes] = None
    tag: Optional[bytes] = None
    algorithm: str = "AES-256-GCM"
    key_id: Optional[str] = None
    metadata: Dict[str, Any] = None


class EncryptionEngine(LoggerMixin):
    """
    Handles all encryption and cryptographic operations
    """
    
    def __init__(self):
        """Initialize encryption engine"""
        # Key storage
        self.key_pairs: Dict[str, KeyPair] = {}
        self.symmetric_keys: Dict[str, bytes] = {}
        
        # Master key for key encryption (KEK)
        self._master_key = self._generate_master_key()
        
        # Generate system keys
        self._generate_system_keys()
        
        self.log_info("Encryption engine initialized")
    
    def _generate_master_key(self) -> bytes:
        """Generate or load master key"""
        # In production, this should be loaded from a secure key store
        # For now, generate a random key
        return Fernet.generate_key()
    
    def _generate_system_keys(self) -> None:
        """Generate system cryptographic keys"""
        # Generate signing key pair
        signing_pair = self.generate_signing_keypair()
        self.key_pairs["system_signing"] = signing_pair
        
        # Generate encryption key pair
        encryption_pair = self.generate_encryption_keypair()
        self.key_pairs["system_encryption"] = encryption_pair
        
        # Generate symmetric key for internal use
        system_key = self.generate_symmetric_key()
        self.symmetric_keys["system"] = system_key
    
    def generate_signing_keypair(
        self,
        key_id: Optional[str] = None
    ) -> KeyPair:
        """
        Generate Ed25519 signing key pair
        
        Args:
            key_id: Optional key identifier
        
        Returns:
            KeyPair with signing keys
        """
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        key_pair = KeyPair(
            private_key=private_key,
            public_key=public_key,
            key_type="Ed25519",
            created_at=datetime.utcnow(),
            key_id=key_id or secrets.token_urlsafe(16)
        )
        
        if key_id:
            self.key_pairs[key_id] = key_pair
        
        self.log_debug(f"Generated Ed25519 key pair: {key_pair.key_id}")
        return key_pair
    
    def generate_encryption_keypair(
        self,
        key_id: Optional[str] = None
    ) -> KeyPair:
        """
        Generate X25519 encryption key pair
        
        Args:
            key_id: Optional key identifier
        
        Returns:
            KeyPair with encryption keys
        """
        private_key = x25519.X25519PrivateKey.generate()
        public_key = private_key.public_key()
        
        key_pair = KeyPair(
            private_key=private_key,
            public_key=public_key,
            key_type="X25519",
            created_at=datetime.utcnow(),
            key_id=key_id or secrets.token_urlsafe(16)
        )
        
        if key_id:
            self.key_pairs[key_id] = key_pair
        
        self.log_debug(f"Generated X25519 key pair: {key_pair.key_id}")
        return key_pair
    
    def generate_symmetric_key(
        self,
        key_id: Optional[str] = None,
        key_size: int = 32
    ) -> bytes:
        """
        Generate symmetric encryption key
        
        Args:
            key_id: Optional key identifier
            key_size: Key size in bytes (32 for AES-256)
        
        Returns:
            Symmetric key bytes
        """
        key = secrets.token_bytes(key_size)
        
        if key_id:
            self.symmetric_keys[key_id] = key
        
        self.log_debug(f"Generated symmetric key: {key_id}")
        return key
    
    def encrypt_symmetric(
        self,
        data: bytes,
        key: Optional[bytes] = None,
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Data to encrypt
            key: Encryption key (or use key_id)
            key_id: Key identifier to use
        
        Returns:
            Encrypted data container
        """
        # Get key
        if key is None:
            if key_id is None:
                key_id = "system"
            key = self.symmetric_keys.get(key_id)
            if not key:
                raise SecurityError(f"Key not found: {key_id}")
        
        # Generate nonce
        nonce = os.urandom(12)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Encrypt data
        ciphertext = encryptor.update(data) + encryptor.finalize()
        
        return EncryptedData(
            ciphertext=ciphertext,
            nonce=nonce,
            tag=encryptor.tag,
            algorithm="AES-256-GCM",
            key_id=key_id
        )
    
    def decrypt_symmetric(
        self,
        encrypted_data: EncryptedData,
        key: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_data: Encrypted data container
            key: Decryption key (or use key_id from container)
        
        Returns:
            Decrypted data
        """
        # Get key
        if key is None:
            key_id = encrypted_data.key_id or "system"
            key = self.symmetric_keys.get(key_id)
            if not key:
                raise SecurityError(f"Key not found: {key_id}")
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(key),
            modes.GCM(encrypted_data.nonce, encrypted_data.tag),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt data
        try:
            plaintext = decryptor.update(encrypted_data.ciphertext) + decryptor.finalize()
            return plaintext
        except Exception as e:
            raise SecurityError(f"Decryption failed: {e}")
    
    def encrypt_asymmetric(
        self,
        data: bytes,
        recipient_public_key: x25519.X25519PublicKey,
        sender_private_key: Optional[x25519.X25519PrivateKey] = None
    ) -> EncryptedData:
        """
        Encrypt data using X25519 + AES-256-GCM
        
        Args:
            data: Data to encrypt
            recipient_public_key: Recipient's public key
            sender_private_key: Sender's private key (optional)
        
        Returns:
            Encrypted data container
        """
        # Use system key if not provided
        if sender_private_key is None:
            key_pair = self.key_pairs.get("system_encryption")
            if not key_pair:
                raise SecurityError("System encryption key not found")
            sender_private_key = key_pair.private_key
        
        # Perform ECDH key exchange
        shared_secret = sender_private_key.exchange(recipient_public_key)
        
        # Derive encryption key
        derived_key = hashlib.sha256(shared_secret).digest()
        
        # Encrypt with derived key
        return self.encrypt_symmetric(data, derived_key)
    
    def decrypt_asymmetric(
        self,
        encrypted_data: EncryptedData,
        recipient_private_key: x25519.X25519PrivateKey,
        sender_public_key: x25519.X25519PublicKey
    ) -> bytes:
        """
        Decrypt data using X25519 + AES-256-GCM
        
        Args:
            encrypted_data: Encrypted data container
            recipient_private_key: Recipient's private key
            sender_public_key: Sender's public key
        
        Returns:
            Decrypted data
        """
        # Perform ECDH key exchange
        shared_secret = recipient_private_key.exchange(sender_public_key)
        
        # Derive decryption key
        derived_key = hashlib.sha256(shared_secret).digest()
        
        # Decrypt with derived key
        return self.decrypt_symmetric(encrypted_data, derived_key)
    
    def sign_data(
        self,
        data: bytes,
        private_key: Optional[ed25519.Ed25519PrivateKey] = None,
        key_id: Optional[str] = None
    ) -> bytes:
        """
        Sign data using Ed25519
        
        Args:
            data: Data to sign
            private_key: Signing key (or use key_id)
            key_id: Key identifier to use
        
        Returns:
            Digital signature
        """
        # Get key
        if private_key is None:
            if key_id is None:
                key_id = "system_signing"
            key_pair = self.key_pairs.get(key_id)
            if not key_pair or key_pair.key_type != "Ed25519":
                raise SecurityError(f"Signing key not found: {key_id}")
            private_key = key_pair.private_key
        
        # Sign data
        signature = private_key.sign(data)
        return signature
    
    def verify_signature(
        self,
        data: bytes,
        signature: bytes,
        public_key: ed25519.Ed25519PublicKey
    ) -> bool:
        """
        Verify signature using Ed25519
        
        Args:
            data: Original data
            signature: Digital signature
            public_key: Verification key
        
        Returns:
            True if signature is valid
        """
        try:
            public_key.verify(signature, data)
            return True
        except Exception:
            return False
    
    def hash_data(
        self,
        data: bytes,
        algorithm: str = "SHA256"
    ) -> str:
        """
        Hash data using specified algorithm
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm (SHA256, SHA512, etc.)
        
        Returns:
            Hex-encoded hash
        """
        if algorithm == "SHA256":
            digest = hashlib.sha256(data).hexdigest()
        elif algorithm == "SHA512":
            digest = hashlib.sha512(data).hexdigest()
        elif algorithm == "SHA3-256":
            digest = hashlib.sha3_256(data).hexdigest()
        elif algorithm == "BLAKE2b":
            digest = hashlib.blake2b(data).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        return digest
    
    def derive_key(
        self,
        password: str,
        salt: Optional[bytes] = None,
        iterations: int = 100000,
        key_length: int = 32
    ) -> Tuple[bytes, bytes]:
        """
        Derive key from password using PBKDF2
        
        Args:
            password: Password string
            salt: Salt bytes (generated if not provided)
            iterations: PBKDF2 iterations
            key_length: Desired key length
        
        Returns:
            Tuple of (derived_key, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=key_length,
            salt=salt,
            iterations=iterations,
            backend=default_backend()
        )
        
        key = kdf.derive(password.encode())
        return key, salt
    
    def secure_random(self, num_bytes: int) -> bytes:
        """Generate cryptographically secure random bytes"""
        return secrets.token_bytes(num_bytes)
    
    def secure_token(self, length: int = 32) -> str:
        """Generate secure URL-safe token"""
        return secrets.token_urlsafe(length)
    
    def export_public_key(
        self,
        key_id: str,
        format: str = "PEM"
    ) -> str:
        """
        Export public key
        
        Args:
            key_id: Key identifier
            format: Export format (PEM or DER)
        
        Returns:
            Exported public key
        """
        key_pair = self.key_pairs.get(key_id)
        if not key_pair:
            raise SecurityError(f"Key not found: {key_id}")
        
        if key_pair.key_type == "Ed25519":
            if format == "PEM":
                pem = key_pair.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return pem.decode()
            else:
                der = key_pair.public_key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return der.hex()
        elif key_pair.key_type == "X25519":
            if format == "PEM":
                pem = key_pair.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return pem.decode()
            else:
                der = key_pair.public_key.public_bytes(
                    encoding=serialization.Encoding.DER,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                )
                return der.hex()
        else:
            raise ValueError(f"Unsupported key type: {key_pair.key_type}")
    
    def rotate_keys(self) -> None:
        """Rotate cryptographic keys"""
        self.log_info("Starting key rotation")
        
        # Generate new keys
        new_signing = self.generate_signing_keypair()
        new_encryption = self.generate_encryption_keypair()
        new_symmetric = self.generate_symmetric_key()
        
        # Archive old keys (keep for decryption of old data)
        old_signing = self.key_pairs.get("system_signing")
        if old_signing:
            self.key_pairs[f"archived_signing_{datetime.utcnow().isoformat()}"] = old_signing
        
        old_encryption = self.key_pairs.get("system_encryption")
        if old_encryption:
            self.key_pairs[f"archived_encryption_{datetime.utcnow().isoformat()}"] = old_encryption
        
        # Update current keys
        self.key_pairs["system_signing"] = new_signing
        self.key_pairs["system_encryption"] = new_encryption
        self.symmetric_keys["system"] = new_symmetric
        
        self.log_info("Key rotation completed")