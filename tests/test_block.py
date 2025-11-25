import pytest
from src.execution.block import Block
from src.execution.transaction import Transaction
from src.execution.state import State
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer

CHAIN_ID = "test"

def test_block_creation():
    """Test creating a block"""
    block = Block(
        height=1,
        parent_hash="genesis",
        transactions=[],
        state_hash="abc123"
    )
    
    assert block.height == 1
    assert block.parent_hash == "genesis"
    assert len(block.transactions) == 0
    assert block.state_hash == "abc123"
    assert block.hash is not None

def test_block_hash_deterministic():
    """Test block hash is deterministic"""
    block1 = Block(1, "genesis", [], "state1")
    block2 = Block(1, "genesis", [], "state1")
    
    assert block1.hash == block2.hash

def test_block_hash_changes_with_data():
    """Test block hash changes when data changes"""
    block1 = Block(1, "genesis", [], "state1")
    block2 = Block(1, "genesis", [], "state2")
    block3 = Block(2, "genesis", [], "state1")
    
    assert block1.hash != block2.hash
    assert block1.hash != block3.hash

def test_block_with_transactions():
    """Test block with transactions"""
    kp = KeyPair()
    signer = Signer(CHAIN_ID)
    
    tx_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    tx = Transaction("alice", "alice/balance", "100", signature, kp.public_key)
    
    block = Block(
        height=1,
        parent_hash="genesis",
        transactions=[tx],
        state_hash="abc123"
    )
    
    assert len(block.transactions) == 1
    assert block.transactions[0] == tx

def test_block_header_data():
    """Test block header data format"""
    block = Block(1, "genesis", [], "state1")
    header = block.header_data()
    
    assert header["height"] == 1
    assert header["parent_hash"] == "genesis"
    assert header["state_hash"] == "state1"

def test_block_compute_correct_state_hash():
    """Test computing correct state hash from transactions"""
    kp1 = KeyPair()
    kp2 = KeyPair()
    signer = Signer(CHAIN_ID)
    
    # Create transactions
    tx1_data = {"sender": "alice", "key": "alice/balance", "value": "100"}
    sig1 = signer.sign_transaction(kp1.private_key, tx1_data)
    tx1 = Transaction("alice", "alice/balance", "100", sig1, kp1.public_key)
    
    tx2_data = {"sender": "bob", "key": "bob/balance", "value": "50"}
    sig2 = signer.sign_transaction(kp2.private_key, tx2_data)
    tx2 = Transaction("bob", "bob/balance", "50", sig2, kp2.public_key)
    
    # Apply to state
    state = State(CHAIN_ID)  # <-- FIX: Pass chain_id
    state.apply_transaction(tx1)
    state.apply_transaction(tx2)
    expected_hash = state.commitment()
    
    # Create block
    block = Block(
        height=1,
        parent_hash="genesis",
        transactions=[tx1, tx2],
        state_hash=expected_hash
    )
    
    assert block.state_hash == expected_hash

def test_block_repr():
    """Test block string representation"""
    block = Block(1, "genesis", [], "state1")
    repr_str = repr(block)
    
    assert "Block" in repr_str
    assert "h=1" in repr_str