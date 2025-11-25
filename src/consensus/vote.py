from src.crypto.signatures import Signer

class Vote:
    """Đại diện cho một vote (Prevote hoặc Precommit)"""
    
    PHASE_PREVOTE = "prevote"
    PHASE_PRECOMMIT = "precommit"
    
    def __init__(self, height, block_hash, phase, voter_id, signature, public_key):
        self.height = height
        self.block_hash = block_hash
        self.phase = phase  # "prevote" or "precommit"
        self.voter_id = voter_id
        self.signature = signature
        self.public_key = public_key
    
    def to_dict(self):
        return {
            "height": self.height,
            "block_hash": self.block_hash,
            "phase": self.phase,
            "voter": self.voter_id
        }
    
    def verify(self, chain_id="mainnet"):
        """Verify vote signature"""
        signer = Signer(chain_id)
        return signer.verify_vote(self.public_key, self.to_dict(), self.signature)
    
    def __repr__(self):
        return f"Vote({self.phase}, h={self.height}, voter={self.voter_id})"

class VoteCollector:
    """Thu thập và đếm votes"""
    
    def __init__(self, validator_set, chain_id="mainnet"):
        self.validators = set(validator_set)
        self.total_validators = len(validator_set)
        self.chain_id = chain_id
        self.prevotes = {}  # (height, block_hash) -> set of voter_ids
        self.precommits = {}  # (height, block_hash) -> set of voter_ids
    
    def add_vote(self, vote):
        """Thêm một vote"""
        if not vote.verify(self.chain_id):
            return False
        
        if vote.voter_id not in self.validators:
            return False
        
        key = (vote.height, vote.block_hash)
        
        if vote.phase == Vote.PHASE_PREVOTE:
            if key not in self.prevotes:
                self.prevotes[key] = set()
            self.prevotes[key].add(vote.voter_id)
        elif vote.phase == Vote.PHASE_PRECOMMIT:
            if key not in self.precommits:
                self.precommits[key] = set()
            self.precommits[key].add(vote.voter_id)
        
        return True
    
    def has_prevote_majority(self, height, block_hash):
        """Kiểm tra có majority prevotes không"""
        key = (height, block_hash)
        if key not in self.prevotes:
            return False
        return len(self.prevotes[key]) > self.total_validators / 2
    
    def has_precommit_majority(self, height, block_hash):
        """Kiểm tra có majority precommits không"""
        key = (height, block_hash)
        if key not in self.precommits:
            return False
        return len(self.precommits[key]) > self.total_validators / 2
    
    def get_prevote_count(self, height, block_hash):
        """Đếm số prevotes"""
        key = (height, block_hash)
        return len(self.prevotes.get(key, set()))
    
    def get_precommit_count(self, height, block_hash):
        """Đếm số precommits"""
        key = (height, block_hash)
        return len(self.precommits.get(key, set()))