import pytest
from src.execution.state import State
from src.execution.transaction import Transaction
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer

# Use consistent chain_id
CHAIN_ID = "test"

def test_state_initialization():
    """Test khởi tạo state"""
    state = State()
    assert len(state.data) == 0
    assert state.commitment() is not None

def test_state_get_set():
    """Test get/set operations"""
    state = State()
    
    state.set("alice/balance", "100")
    assert state.get("alice/balance") == "100"
    
    state.set("bob/balance", "50")
    assert state.get("bob/balance") == "50"
    assert state.get("charlie/balance") is None

def test_state_apply_transaction():
    """Test apply transaction to state"""
    kp = KeyPair()
    signer = Signer(CHAIN_ID)
    
    # Create valid transaction
    tx_data = {
        "sender": "alice",
        "key": "alice/message",
        "value": "hello"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    tx = Transaction(
        sender="alice",
        key="alice/message",
        value="hello",
        signature=signature,
        public_key=kp.public_key
    )
    
    state = State()
    state.apply_transaction(tx)
    
    assert state.get("alice/message") == "hello"

def test_state_apply_invalid_transaction():
    """Test reject invalid transaction"""
    # Transaction without signature
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="100",
        signature=None,
        public_key=None
    )
    
    state = State()
    with pytest.raises(ValueError):
        state.apply_transaction(tx)

def test_state_commitment_deterministic():
    """Test state commitment is deterministic"""
    state1 = State()
    state1.set("b", "2")
    state1.set("a", "1")
    state1.set("c", "3")
    
    state2 = State()
    state2.set("a", "1")
    state2.set("c", "3")
    state2.set("b", "2")
    
    # Same data, different order -> same hash
    assert state1.commitment() == state2.commitment()

def test_state_commitment_changes():
    """Test state commitment changes when data changes"""
    state = State()
    hash1 = state.commitment()
    
    state.set("alice/balance", "100")
    hash2 = state.commitment()
    
    assert hash1 != hash2
    
    state.set("bob/balance", "50")
    hash3 = state.commitment()
    
    assert hash2 != hash3

def test_state_copy():
    """Test state copy"""
    state1 = State()
    state1.set("alice/balance", "100")
    state1.set("bob/balance", "50")
    
    state2 = state1.copy()
    
    # Same content
    assert state1.commitment() == state2.commitment()
    
    # Independent copies
    state2.set("charlie/balance", "75")
    assert state1.commitment() != state2.commitment()
    assert state1.get("charlie/balance") is None

def test_state_multiple_transactions():
    """Test applying multiple transactions"""
    kp1 = KeyPair()
    kp2 = KeyPair()
    signer = Signer(CHAIN_ID)
    
    state = State()
    
    # Transaction 1
    tx1_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    sig1 = signer.sign_transaction(kp1.private_key, tx1_data)
    tx1 = Transaction("alice", "alice/balance", "100", sig1, kp1.public_key)
    state.apply_transaction(tx1)
    
    # Transaction 2
    tx2_data = {
        "sender": "bob",
        "key": "bob/balance",
        "value": "50"
    }
    sig2 = signer.sign_transaction(kp2.private_key, tx2_data)
    tx2 = Transaction("bob", "bob/balance", "50", sig2, kp2.public_key)
    state.apply_transaction(tx2)
    
    assert state.get("alice/balance") == "100"
    assert state.get("bob/balance") == "50"
    assert len(state.data) == 2