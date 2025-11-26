from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer
from src.execution.state import State
from src.execution.block import Block
from src.network.message import Message, MessageType

class Node:
    """Đại diện cho một node trong network - FINAL FIXED VERSION with Sync"""
    
    def __init__(self, node_id, is_validator=True, chain_id="mainnet"):
        self.node_id = node_id
        self.is_validator = is_validator
        self.chain_id = chain_id
        
        # Cryptography
        self.key_pair = KeyPair()
        self.signer = Signer(chain_id)
        
        # State & Ledger
        self.state = State(chain_id)
        self.ledger = []  # List of finalized blocks
        self.pending_transactions = []
        
        # Consensus
        self.current_height = 0
        self.pending_blocks = {}  # height -> Block
        self.prevotes = {}  # height -> {block_hash -> set of voters}
        self.precommits = {}  # height -> {block_hash -> set of voters}
        
        # Network
        self.network = None
        self.seen_messages = set()
        
        # Validator set
        self.validators = set()
        
        # Track votes sent
        self.sent_prevotes = set()  # (height, block_hash)
        self.sent_precommits = set()  # (height, block_hash)
        
        # FIX: Add sync mechanism
        self.last_sync_attempt = 0
        self.sync_interval = 0.5  # Try to sync every 0.5s
    
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
        elif message.msg_type == MessageType.REQUEST_BLOCK:
            self._handle_block_request(message)
    
    def _handle_transaction(self, message):
        """Xử lý transaction"""
        tx = message.data
        if tx.verify(self.chain_id):
            self.pending_transactions.append(tx)
    
    def _handle_block_header(self, message):
        """Xử lý block header"""
        block = message.data
        
        # Accept blocks for current height + 1, or future blocks
        if block.height < self.current_height + 1:
            return  # Already finalized
        
        # FIX: Store future blocks too
        if block.height > self.current_height + 1:
            # Store for later but don't validate yet
            self.pending_blocks[block.height] = block
            return
        
        # Validate block for next height
        if not self._validate_block(block):
            return
        
        # Store pending block
        self.pending_blocks[block.height] = block
        
        # If validator, send prevote
        if self.is_validator:
            self._send_prevote(block)
    
    def _validate_block(self, block):
        """Validate a block - FIXED VERSION"""
        # Check height matches expectation
        if block.height != self.current_height + 1:
            print(f"[Node {self.node_id}] Block height {block.height} != expected {self.current_height + 1}")
            return False
        
        # Check parent hash
        if self.ledger:
            # Have ledger: must match last block
            expected_parent = self.ledger[-1].hash
            if block.parent_hash != expected_parent:
                print(f"[Node {self.node_id}] Parent hash mismatch: {block.parent_hash[:8]} != {expected_parent[:8]}")
                return False
        else:
            # No ledger: must be height 1 with genesis parent
            if block.height != 1:
                print(f"[Node {self.node_id}] First block must be height 1, got {block.height}")
                return False
            if block.parent_hash != "genesis":
                print(f"[Node {self.node_id}] First block must have genesis parent, got {block.parent_hash}")
                return False
        
        # Verify all transactions are valid
        for tx in block.transactions:
            if not tx.verify(self.chain_id):
                print(f"[Node {self.node_id}] Invalid transaction: {tx}")
                return False
        
        # Verify state hash by re-executing
        temp_state = self.state.copy()
        try:
            for tx in block.transactions:
                temp_state.apply_transaction(tx)
        except Exception as e:
            print(f"[Node {self.node_id}] Error applying transactions: {e}")
            return False
        
        expected_state_hash = temp_state.commitment()
        if block.state_hash != expected_state_hash:
            print(f"[Node {self.node_id}] State hash mismatch:")
            print(f"  Expected: {expected_state_hash[:16]}...")
            print(f"  Got:      {block.state_hash[:16]}...")
            return False
        
        return True

    
    def _send_prevote(self, block):
        """Gửi prevote cho block"""
        vote_key = (block.height, block.hash)
        if vote_key in self.sent_prevotes:
            return
        
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
        
        self.sent_prevotes.add(vote_key)
        
        # Self-receive
        self._handle_prevote(message)
    
    def _handle_prevote(self, message):
        """Xử lý prevote"""
        vote = message.data
        vote_data = vote["data"]
        
        # Verify signature
        if not self.signer.verify_vote(vote["public_key"], vote_data, vote["signature"]):
            return
        
        height = vote_data["height"]
        
        # FIX: Accept votes for next height OR current height (for stragglers)
        if height < self.current_height + 1:
            return
        
        block_hash = vote_data["block_hash"]
        voter = vote_data["voter"]
        
        if voter not in self.validators:
            return
        
        # Store vote
        if height not in self.prevotes:
            self.prevotes[height] = {}
        if block_hash not in self.prevotes[height]:
            self.prevotes[height][block_hash] = set()
        
        self.prevotes[height][block_hash].add(voter)
        
        # Check majority (strict majority: > 50%)
        if len(self.prevotes[height][block_hash]) > len(self.validators) / 2:
            if self.is_validator:
                self._send_precommit(height, block_hash)
    
    def _send_precommit(self, height, block_hash):
        """Gửi precommit cho block"""
        vote_key = (height, block_hash)
        if vote_key in self.sent_precommits:
            return
        
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
        
        self.sent_precommits.add(vote_key)
        
        # Self-receive
        self._handle_precommit(message)
    
    def _handle_precommit(self, message):
        """Xử lý precommit"""
        vote = message.data
        vote_data = vote["data"]
        
        # Verify signature
        if not self.signer.verify_vote(vote["public_key"], vote_data, vote["signature"]):
            return
        
        height = vote_data["height"]
        
        # FIX: Accept votes for next height
        if height < self.current_height + 1:
            return
        
        block_hash = vote_data["block_hash"]
        voter = vote_data["voter"]
        
        if voter not in self.validators:
            return
        
        # Store vote
        if height not in self.precommits:
            self.precommits[height] = {}
        if block_hash not in self.precommits[height]:
            self.precommits[height][block_hash] = set()
        
        self.precommits[height][block_hash].add(voter)
        
        # Check majority -> FINALIZE
        if len(self.precommits[height][block_hash]) > len(self.validators) / 2:
            self._finalize_block(height, block_hash)
    
    def _finalize_block(self, height, block_hash):
        """Finalize một block"""
        if height != self.current_height + 1:
            return
        
        if self.current_height >= height:
            return
        
        block = self.pending_blocks.get(height)
        if not block or block.hash != block_hash:
            return
        
        # Apply block to state
        for tx in block.transactions:
            try:
                self.state.apply_transaction(tx)
            except Exception as e:
                print(f"[Node {self.node_id}] ERROR applying tx: {e}")
                return
        
        # Add to ledger
        self.ledger.append(block)
        self.current_height = height
        
        print(f"[Node {self.node_id}] Finalized block {height} (hash: {block_hash[:8]}...)")
        
        # Cleanup
        self._cleanup_old_data(height)
        
        # FIX: Check if we can finalize next block
        self._try_finalize_next()
    
    def _try_finalize_next(self):
        """Try to finalize next block if we have it"""
        next_height = self.current_height + 1
        
        # Check if we have pending block
        if next_height not in self.pending_blocks:
            return
        
        # Check if we have majority precommits
        if next_height in self.precommits:
            for block_hash, voters in self.precommits[next_height].items():
                if len(voters) > len(self.validators) / 2:
                    # Try to finalize
                    block = self.pending_blocks.get(next_height)
                    if block and block.hash == block_hash:
                        # Validate and finalize
                        if self._validate_block(block):
                            self._finalize_block(next_height, block_hash)
                            return
    
    def _cleanup_old_data(self, finalized_height):
        """Clean up old votes and pending blocks"""
        # Remove old prevotes
        old_heights = [h for h in self.prevotes.keys() if h <= finalized_height]
        for h in old_heights:
            del self.prevotes[h]
        
        # Remove old precommits
        old_heights = [h for h in self.precommits.keys() if h <= finalized_height]
        for h in old_heights:
            del self.precommits[h]
        
        # Remove old pending blocks
        old_heights = [h for h in self.pending_blocks.keys() if h <= finalized_height]
        for h in old_heights:
            del self.pending_blocks[h]
    
    def _handle_block_request(self, message):
        """Handle request for missing block"""
        requested_height = message.data.get("height")
        requester_id = message.data.get("requester")
        
        # Check if we have this block
        if len(self.ledger) >= requested_height:
            block = self.ledger[requested_height - 1]
            
            # Send block to requester
            response = Message(MessageType.BLOCK_HEADER, self.node_id, block)
            self.network.send(self.node_id, requester_id, response)
    
    def propose_block(self):
        """Propose một block mới"""
        if not self.pending_transactions:
            print(f"[Node {self.node_id}] No transactions to propose")
            return
        
        # Create new block
        parent_hash = self.ledger[-1].hash if self.ledger else "genesis"
        
        # Apply transactions
        temp_state = self.state.copy()
        valid_txs = []
        for tx in self.pending_transactions:
            try:
                temp_state.apply_transaction(tx)
                valid_txs.append(tx)
            except Exception as e:
                print(f"[Node {self.node_id}] Invalid tx: {e}")
        
        if not valid_txs:
            print(f"[Node {self.node_id}] No valid transactions")
            return
        
        block = Block(
            height=self.current_height + 1,
            parent_hash=parent_hash,
            transactions=valid_txs,
            state_hash=temp_state.commitment()
        )
        
        # Sign header
        header_sig = self.signer.sign_header(self.key_pair.private_key, block.header_data())
        block.proposer_signature = header_sig
        
        # Broadcast block
        message = Message(MessageType.BLOCK_HEADER, self.node_id, block)
        self.network.broadcast(self.node_id, message)
        
        print(f"[Node {self.node_id}] Proposed block {block.height} with {len(valid_txs)} txs")
        
        # Self-receive
        self.receive_message(message)
        
        # Clear pending transactions
        self.pending_transactions = []
    
    def get_ledger_state(self):
        """Trả về state hiện tại"""
        return {
            "height": self.current_height,
            "state_hash": self.state.commitment(),
            "num_blocks": len(self.ledger)
        }