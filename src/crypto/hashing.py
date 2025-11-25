import hashlib
import json

class Hasher:
    """Xử lý hashing với deterministic encoding"""
    
    @staticmethod
    def hash_data(data):
        """Hash dict/list với deterministic encoding"""
        # Convert to JSON với sorted keys
        json_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        # SHA-256
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
    
    @staticmethod
    def hash_bytes(data_bytes):
        """Hash raw bytes"""
        return hashlib.sha256(data_bytes).hexdigest()
    
    @staticmethod
    def hash_state(state_dict):
        """Hash state (key-value store)"""
        # Sort keys để đảm bảo deterministic
        sorted_items = sorted(state_dict.items())
        return Hasher.hash_data(sorted_items)