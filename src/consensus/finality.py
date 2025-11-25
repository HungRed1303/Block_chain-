class FinalityManager:
    """Quản lý finality của blocks"""
    
    def __init__(self, validator_set):
        self.validators = set(validator_set)
        self.finalized_blocks = {}  # height -> block_hash
        self.pending_blocks = {}  # height -> {block_hash -> block}
    
    def add_pending_block(self, block):
        """Thêm block đang chờ finalize"""
        height = block.height
        if height not in self.pending_blocks:
            self.pending_blocks[height] = {}
        self.pending_blocks[height][block.hash] = block
    
    def try_finalize(self, height, block_hash, precommit_votes):
        """Thử finalize một block"""
        # Check if already finalized
        if height in self.finalized_blocks:
            return False
        
        # Check majority
        if len(precommit_votes) <= len(self.validators) / 2:
            return False
        
        # Verify all votes
        for vote in precommit_votes:
            if not vote.verify():
                return False
            if vote.voter_id not in self.validators:
                return False
        
        # Mark as finalized
        self.finalized_blocks[height] = block_hash
        return True
    
    def is_finalized(self, height, block_hash):
        """Kiểm tra block đã finalized chưa"""
        return self.finalized_blocks.get(height) == block_hash
    
    def get_finalized_height(self):
        """Trả về height cao nhất đã finalized"""
        return max(self.finalized_blocks.keys()) if self.finalized_blocks else 0
    
    def check_safety(self):
        """Kiểm tra safety: không có 2 blocks khác nhau cùng height được finalized"""
        heights = {}
        for height, block_hash in self.finalized_blocks.items():
            if height in heights and heights[height] != block_hash:
                return False
            heights[height] = block_hash
        return True