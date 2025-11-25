from src.crypto.hashing import Hasher

class Block:
    """Đại diện cho một block"""
    
    def __init__(self, height, parent_hash, transactions, state_hash, proposer_signature=None):
        self.height = height
        self.parent_hash = parent_hash
        self.transactions = transactions  # List of Transaction objects
        self.state_hash = state_hash  # Hash của state sau khi apply transactions
        self.proposer_signature = proposer_signature
        self.hash = self._compute_hash()
    
    def _compute_hash(self):
        """Tính hash của block"""
        block_data = {
            "height": self.height,
            "parent_hash": self.parent_hash,
            "tx_count": len(self.transactions),
            "state_hash": self.state_hash
        }
        return Hasher.hash_data(block_data)
    
    def header_data(self):
        """Data để sign header"""
        return {
            "height": self.height,
            "parent_hash": self.parent_hash,
            "state_hash": self.state_hash
        }
    
    def __repr__(self):
        return f"Block(h={self.height}, hash={self.hash[:8]}..., {len(self.transactions)} txs)"