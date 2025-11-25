from src.crypto.hashing import Hasher

class State:
    """Quản lý state (key-value store)"""
    
    def __init__(self):
        self.data = {}  # key -> value
    
    def get(self, key):
        """Lấy value theo key"""
        return self.data.get(key)
    
    def set(self, key, value):
        """Set value cho key"""
        self.data[key] = value
    
    def apply_transaction(self, tx):
        """Apply một transaction lên state"""
        if not tx.verify():
            raise ValueError(f"Invalid transaction: {tx}")
        
        # Update state
        self.data[tx.key] = tx.value
    
    def commitment(self):
        """Tạo commitment hash cho state"""
        return Hasher.hash_state(self.data)
    
    def copy(self):
        """Tạo bản copy của state"""
        new_state = State()
        new_state.data = self.data.copy()
        return new_state
    
    def __repr__(self):
        return f"State({len(self.data)} entries, hash={self.commitment()[:8]}...)"