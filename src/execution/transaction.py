import base64
from src.crypto.signatures import Signer

class Transaction:
    """Đại diện cho một transaction"""
    
    def __init__(self, sender, key, value, signature=None, public_key=None):
        self.sender = sender
        self.key = key
        self.value = value
        self.signature = signature  # bytes
        self.public_key = public_key  # Ed25519PublicKey object
    
    def to_dict(self):
        """Convert to dict (không bao gồm signature)"""
        return {
            "sender": self.sender,
            "key": self.key,
            "value": self.value
        }
    
    def verify(self, chain_id="mainnet"):
        """Verify transaction signature"""
        if not self.signature or not self.public_key:
            return False
        
        # Key phải thuộc về sender
        if not self.key.startswith(f"{self.sender}/"):
            return False
        
        signer = Signer(chain_id)
        return signer.verify_transaction(
            self.public_key,
            self.to_dict(),
            self.signature
        )
    
    def __repr__(self):
        return f"Tx({self.sender}: {self.key}={self.value})"