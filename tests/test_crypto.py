import pytest
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer
from src.crypto.hashing import Hasher

def test_key_generation():
    """Test key pair generation"""
    kp = KeyPair()
    assert kp.public_key is not None
    assert kp.private_key is not None
    assert len(kp.get_public_key_bytes()) == 32

def test_signature_transaction():
    """Test transaction signing"""
    kp = KeyPair()
    signer = Signer(chain_id="test")
    
    tx_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    
    # Sign
    signature = signer.sign_transaction(kp.private_key, tx_data)
    
    # Verify
    assert signer.verify_transaction(kp.public_key, tx_data, signature)
    
    # Wrong data should fail
    wrong_data = tx_data.copy()
    wrong_data["value"] = "200"
    assert not signer.verify_transaction(kp.public_key, wrong_data, signature)

def test_domain_separation():
    """Test that signatures from different domains don't validate"""
    kp = KeyPair()
    signer = Signer(chain_id="test")
    
    data = {"height": 1, "hash": "abc123"}
    
    # Sign as VOTE
    vote_sig = signer.sign_vote(kp.private_key, data)
    
    # Should not verify as HEADER
    assert not signer.verify_header(kp.public_key, data, vote_sig)

def test_deterministic_hashing():
    """Test that same data produces same hash"""
    data1 = {"b": 2, "a": 1, "c": 3}
    data2 = {"a": 1, "c": 3, "b": 2}
    
    hash1 = Hasher.hash_data(data1)
    hash2 = Hasher.hash_data(data2)
    
    assert hash1 == hash2

def test_state_hashing():
    """Test state commitment hashing"""
    state1 = {"alice/balance": "100", "bob/balance": "50"}
    state2 = {"bob/balance": "50", "alice/balance": "100"}
    
    hash1 = Hasher.hash_state(state1)
    hash2 = Hasher.hash_state(state2)
    
    assert hash1 == hash2