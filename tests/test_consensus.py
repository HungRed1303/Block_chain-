import pytest
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer
from src.consensus.vote import Vote, VoteCollector
from src.consensus.finality import FinalityManager
from src.execution.block import Block

def test_vote_creation_and_verification():
    """Test vote creation and verification"""
    kp = KeyPair()
    signer = Signer("test")
    
    vote_data = {
        "height": 1,
        "block_hash": "abc123",
        "phase": "prevote",
        "voter": "node1"
    }
    
    signature = signer.sign_vote(kp.private_key, vote_data)
    
    vote = Vote(
        height=1,
        block_hash="abc123",
        phase="prevote",
        voter_id="node1",
        signature=signature,
        public_key=kp.public_key
    )
    
    assert vote.verify(chain_id="test")

def test_vote_collector_majority():
    """Test vote collector với majority voting"""
    validators = ["node1", "node2", "node3", "node4", "node5"]
    collector = VoteCollector(validators)
    
    # Create votes from 3 nodes (majority)
    for i in range(3):
        kp = KeyPair()
        signer = Signer("test")
        vote_data = {
            "height": 1,
            "block_hash": "abc123",
            "phase": "prevote",
            "voter": f"node{i+1}"
        }
        signature = signer.sign_vote(kp.private_key, vote_data)
        vote = Vote(1, "abc123", "prevote", f"node{i+1}", signature, kp.public_key)
        collector.add_vote(vote)
    
    assert collector.has_prevote_majority(1, "abc123")
    assert collector.get_prevote_count(1, "abc123") == 3

def test_finality_manager():
    """Test finality manager"""
    validators = ["node1", "node2", "node3"]
    fm = FinalityManager(validators)
    
    # Create block
    block = Block(1, "genesis", [], "state_hash_1")
    fm.add_pending_block(block)
    
    # Create precommit votes (majority: 2/3)
    votes = []
    for i in range(2):
        kp = KeyPair()
        signer = Signer("test")
        vote_data = {
            "height": 1,
            "block_hash": block.hash,
            "phase": "precommit",
            "voter": f"node{i+1}"
        }
        signature = signer.sign_vote(kp.private_key, vote_data)
        vote = Vote(1, block.hash, "precommit", f"node{i+1}", signature, kp.public_key)
        votes.append(vote)
    
    # Try finalize
    result = fm.try_finalize(1, block.hash, votes)
    assert result
    assert fm.is_finalized(1, block.hash)
    assert fm.check_safety()

def test_finality_safety():
    """Test that two different blocks at same height cannot be finalized"""
    validators = ["node1", "node2", "node3"]
    fm = FinalityManager(validators)
    
    # First block
    block1 = Block(1, "genesis", [], "state_hash_1")
    fm.add_pending_block(block1)
    
    votes1 = []
    for i in range(2):
        kp = KeyPair()
        signer = Signer("test")
        vote_data = {
            "height": 1,
            "block_hash": block1.hash,
            "phase": "precommit",
            "voter": f"node{i+1}"
        }
        signature = signer.sign_vote(kp.private_key, vote_data)
        vote = Vote(1, block1.hash, "precommit", f"node{i+1}", signature, kp.public_key)
        votes1.append(vote)
    
    fm.try_finalize(1, block1.hash, votes1)
    
    # Try to finalize different block at same height
    block2 = Block(1, "genesis", [], "state_hash_2")
    fm.add_pending_block(block2)
    
    votes2 = []
    for i in range(2):
        kp = KeyPair()
        signer = Signer("test")
        vote_data = {
            "height": 1,
            "block_hash": block2.hash,
            "phase": "precommit",
            "voter": f"node{i+1}"
        }
        signature = signer.sign_vote(kp.private_key, vote_data)
        vote = Vote(1, block2.hash, "precommit", f"node{i+1}", signature, kp.public_key)
        votes2.append(vote)
    
    result = fm.try_finalize(1, block2.hash, votes2)
    assert not result  # Should fail - already finalized