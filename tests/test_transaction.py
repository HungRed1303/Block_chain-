import pytest
from src.execution.transaction import Transaction
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer

def test_transaction_creation():
    """Test creating a transaction"""
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="100"
    )
    
    assert tx.sender == "alice"
    assert tx.key == "alice/balance"
    assert tx.value == "100"

def test_transaction_to_dict():
    """Test transaction serialization"""
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="100"
    )
    
    data = tx.to_dict()
    assert data["sender"] == "alice"
    assert data["key"] == "alice/balance"
    assert data["value"] == "100"

def test_transaction_valid_signature():
    """Test transaction with valid signature"""
    kp = KeyPair()
    signer = Signer("test")
    
    tx_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="100",
        signature=signature,
        public_key=kp.public_key
    )
    
    assert tx.verify(chain_id="test")

def test_transaction_invalid_signature():
    """Test transaction with invalid signature"""
    kp1 = KeyPair()
    kp2 = KeyPair()
    signer = Signer("test")
    
    tx_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    
    # Sign with kp1
    signature = signer.sign_transaction(kp1.private_key, tx_data)
    
    # But use kp2's public key
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="100",
        signature=signature,
        public_key=kp2.public_key
    )
    
    assert not tx.verify(chain_id="test")

def test_transaction_wrong_sender():
    """Test transaction where key doesn't match sender"""
    kp = KeyPair()
    signer = Signer("test")
    
    tx_data = {
        "sender": "alice",
        "key": "bob/balance",  # Wrong! Should be alice/balance
        "value": "100"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    
    tx = Transaction(
        sender="alice",
        key="bob/balance",
        value="100",
        signature=signature,
        public_key=kp.public_key
    )
    
    # Should fail because key doesn't start with "alice/"
    assert not tx.verify(chain_id="test")

def test_transaction_no_signature():
    """Test transaction without signature"""
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="100"
    )
    
    assert not tx.verify(chain_id="test")

def test_transaction_tampered_data():
    """Test transaction with tampered data"""
    kp = KeyPair()
    signer = Signer("test")
    
    tx_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    
    # Create transaction but change value
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="1000",  # Changed!
        signature=signature,
        public_key=kp.public_key
    )
    
    assert not tx.verify(chain_id="test")

def test_transaction_different_chain_id():
    """Test transaction fails on different chain_id"""
    kp = KeyPair()
    signer = Signer("mainnet")
    
    tx_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    
    tx = Transaction(
        sender="alice",
        key="alice/balance",
        value="100",
        signature=signature,
        public_key=kp.public_key
    )
    
    # Signed with "mainnet" but verified with "testnet"
    assert not tx.verify(chain_id="testnet")