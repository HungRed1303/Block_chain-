import json
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

class Signer:
    """Xử lý ký và verify signatures với domain separation"""
    
    DOMAIN_TX = "TX"
    DOMAIN_HEADER = "HEADER"
    DOMAIN_VOTE = "VOTE"
    
    def __init__(self, chain_id="mainnet"):
        self.chain_id = chain_id
    
    def _create_message(self, domain, data):
        """Tạo message với domain separation"""
        # Format: DOMAIN:chain_id:data
        message_str = f"{domain}:{self.chain_id}:{json.dumps(data, sort_keys=True)}"
        return message_str.encode('utf-8')
    
    def sign_transaction(self, private_key, tx_data):
        """Ký transaction"""
        message = self._create_message(self.DOMAIN_TX, tx_data)
        signature = private_key.sign(message)
        return signature
    
    def verify_transaction(self, public_key, tx_data, signature):
        """Verify transaction signature"""
        message = self._create_message(self.DOMAIN_TX, tx_data)
        try:
            public_key.verify(signature, message)
            return True
        except InvalidSignature:
            return False
    
    def sign_header(self, private_key, header_data):
        """Ký block header"""
        message = self._create_message(self.DOMAIN_HEADER, header_data)
        return private_key.sign(message)
    
    def verify_header(self, public_key, header_data, signature):
        """Verify block header signature"""
        message = self._create_message(self.DOMAIN_HEADER, header_data)
        try:
            public_key.verify(signature, message)
            return True
        except InvalidSignature:
            return False
    
    def sign_vote(self, private_key, vote_data):
        """Ký vote (Prevote/Precommit)"""
        message = self._create_message(self.DOMAIN_VOTE, vote_data)
        return private_key.sign(message)
    
    def verify_vote(self, public_key, vote_data, signature):
        """Verify vote signature"""
        message = self._create_message(self.DOMAIN_VOTE, vote_data)
        try:
            public_key.verify(signature, message)
            return True
        except InvalidSignature:
            return False