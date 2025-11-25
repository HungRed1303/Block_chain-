from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

class KeyPair:
    """Quản lý cặp khóa Ed25519"""
    
    def __init__(self):
        self.private_key = ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
    
    def get_public_key_bytes(self):
        """Trả về public key dạng bytes"""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
    
    def get_private_key_bytes(self):
        """Trả về private key dạng bytes"""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    @staticmethod
    def from_bytes(private_bytes):
        """Load key từ bytes"""
        kp = KeyPair.__new__(KeyPair)
        kp.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(private_bytes)
        kp.public_key = kp.private_key.public_key()
        return kp