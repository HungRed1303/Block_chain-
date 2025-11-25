from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer
from src.execution.state import State
from src.execution.block import Block
from src.network.message import Message, MessageType

class Node:
    """Đại diện cho một node trong network"""
    
    def __init__(self, node_id, is_validator=True, chain_id="mainnet"):
        self.node_id = node_id
        self.is_validator = is_validator
        self.chain_id = chain_id
        
        # Cryptography
        self.key_pair = KeyPair()
        self.signer = Signer(chain_id)
        
        # State & Ledger
        self.state = State()
        self.ledger = []  # List of finalized blocks
        self.pending_transactions = []
        
        # Consensus
        self.current_height = 0
        self.pending_blocks = {}  # height -> Block
        self.prevotes = {}  # height -> {block_hash -> [votes]}
        self.precommits = {}  # height -> {block_hash -> [votes]}
        
        # Network
        self.network = None
        self.seen_messages = set()  # Để tránh process duplicate
        
        # Validator set (simplified - all nodes are validators)
        self.validators = set()
    
    def set_network(self, network):
        """Set network simulator"""
        self.network = network
    
    def set_validators(self, validator_ids):
        """Set danh sách validators"""
        self.validators = set(validator_ids)
    
    def receive_message(self, message):
        """Nhận và xử lý message"""
        # Check duplicate
        if message.msg_id in self.seen_messages:
            return
        
        self.seen_messages.add(message.msg_id)
        
        # Route message based on type
        if message.msg_type == MessageType.TRANSACTION:
            self._handle_transaction(message)
        elif message.msg_type == MessageType.BLOCK_HEADER:
            self._handle_block_header(message)
        elif message.msg_type == MessageType.PREVOTE:
            self._handle_prevote(message)
        elif message.msg_type == MessageType.PRECOMMIT:
            self._handle_precommit(message)
    
    def _handle_transaction(self, message):
        """Xử lý transaction"""
        tx = message.data
        if tx.verify(self.chain_id):
            self.pending_transactions.append(tx)
    
    def _handle_block_header(self, message):
        """Xử lý block header"""
        block = message.data
        
        # Validate block
        if not self._validate_block(block):
            return
        
        # Store pending block
        self.pending_blocks[block.height] = block
        
        # If validator, send prevote
        if self.is_validator:
            self._send_prevote(block)
    
    def _validate_block(self, block):
        """Validate một block"""
        # Check height
        if block.height != self.current_height + 1:
            return False
        
        # Check parent hash
        if self.ledger:
            if block.parent_hash != self.ledger[-1].hash:
                return False
        
        # Verify state hash
        temp_state = self.state.copy()
        for tx in block.transactions:
            if not tx.verify(self.chain_id):
                return False
            temp_state.apply_transaction(tx)
        
        if temp_state.commitment() != block.state_hash:
            return False
        
        return True
    
    def _send_prevote(self, block):
        """Gửi prevote cho block"""
        vote_data = {
            "height": block.height,
            "block_hash": block.hash,
            "phase": "prevote",
            "voter": self.node_id
        }
        
        signature = self.signer.sign_vote(self.key_pair.private_key, vote_data)
        
        vote = {
            "data": vote_data,
            "signature": signature,
            "public_key": self.key_pair.public_key
        }
        
        message = Message(MessageType.PREVOTE, self.node_id, vote)
        self.network.broadcast(self.node_id, message)
    
    def _handle_prevote(self, message):
        """Xử lý prevote"""
        vote = message.data
        vote_data = vote["data"]
        
        # Verify signature
        if not self.signer.verify_vote(vote["public_key"], vote_data, vote["signature"]):
            return
        
        height = vote_data["height"]
        block_hash = vote_data["block_hash"]
        
        # Store vote
        if height not in self.prevotes:
            self.prevotes[height] = {}
        if block_hash not in self.prevotes[height]:
            self.prevotes[height][block_hash] = []
        
        self.prevotes[height][block_hash].append(vote)
        
        # Check if we have majority prevotes
        if len(self.prevotes[height][block_hash]) > len(self.validators) / 2:
            # Send precommit
            if self.is_validator:
                self._send_precommit(height, block_hash)
    
    def _send_precommit(self, height, block_hash):
        """Gửi precommit cho block"""
        vote_data = {
            "height": height,
            "block_hash": block_hash,
            "phase": "precommit",
            "voter": self.node_id
        }
        
        signature = self.signer.sign_vote(self.key_pair.private_key, vote_data)
        
        vote = {
            "data": vote_data,
            "signature": signature,
            "public_key": self.key_pair.public_key
        }
        
        message = Message(MessageType.PRECOMMIT, self.node_id, vote)
        self.network.broadcast(self.node_id, message)
    
    def _handle_precommit(self, message):
        """Xử lý precommit"""
        vote = message.data
        vote_data = vote["data"]
        
        # Verify signature
        if not self.signer.verify_vote(vote["public_key"], vote_data, vote["signature"]):
            return
        
        height = vote_data["height"]
        block_hash = vote_data["block_hash"]
        
        # Store vote
        if height not in self.precommits:
            self.precommits[height] = {}
        if block_hash not in self.precommits[height]:
            self.precommits[height][block_hash] = []
        
        self.precommits[height][block_hash].append(vote)
        
        # Check if we have majority precommits -> FINALIZE
        if len(self.precommits[height][block_hash]) > len(self.validators) / 2:
            self._finalize_block(height, block_hash)
    
    def _finalize_block(self, height, block_hash):
        """Finalize một block"""
        if height != self.current_height + 1:
            return
        
        block = self.pending_blocks.get(height)
        if not block or block.hash != block_hash:
            return
        
        # Apply block to state
        for tx in block.transactions:
            self.state.apply_transaction(tx)
        
        # Add to ledger
        self.ledger.append(block)
        self.current_height = height
        
        print(f"[Node {self.node_id}] Finalized block {height} (hash: {block_hash[:8]}...)")
    
    def propose_block(self):
        """Propose một block mới (chỉ cho proposer)"""
        if not self.pending_transactions:
            return
        
        # Create new block
        parent_hash = self.ledger[-1].hash if self.ledger else "genesis"
        
        # Apply transactions to compute state hash
        temp_state = self.state.copy()
        valid_txs = []
        for tx in self.pending_transactions:
            try:
                temp_state.apply_transaction(tx)
                valid_txs.append(tx)
            except:
                pass
        
        block = Block(
            height=self.current_height + 1,
            parent_hash=parent_hash,
            transactions=valid_txs,
            state_hash=temp_state.commitment()
        )
        
        # Sign header
        header_sig = self.signer.sign_header(self.key_pair.private_key, block.header_data())
        block.proposer_signature = header_sig
        
        # Broadcast block header
        message = Message(MessageType.BLOCK_HEADER, self.node_id, block)
        self.network.broadcast(self.node_id, message)
        
        # Clear pending transactions
        self.pending_transactions = []
        
        print(f"[Node {self.node_id}] Proposed block {block.height}")
    
    def get_ledger_state(self):
        """Trả về state hiện tại của ledger"""
        return {
            "height": self.current_height,
            "state_hash": self.state.commitment(),
            "num_blocks": len(self.ledger)
        }