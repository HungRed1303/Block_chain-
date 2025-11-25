import pytest
import time
from src.network.simulator import NetworkSimulator
from src.network.node import Node
from src.network.message import Message, MessageType
from src.execution.transaction import Transaction
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer

CHAIN_ID = "mainnet"

def test_end_to_end_single_block():
    """Test end-to-end: propose, vote, finalize một block"""
    # Setup network
    config = {
        "min_delay": 0.01,
        "max_delay": 0.05,
        "drop_rate": 0.0,
        "duplicate_rate": 0.0,
        "rate_limit": 1000
    }
    
    network = NetworkSimulator(config)
    
    # Create 5 nodes
    nodes = [Node(f"node{i}", is_validator=True, chain_id=CHAIN_ID) for i in range(5)]
    validator_ids = [f"node{i}" for i in range(5)]
    
    for node in nodes:
        network.register_node(node)
        node.set_network(network)
        node.set_validators(validator_ids)
    
    # Create transaction
    kp = KeyPair()
    signer = Signer(CHAIN_ID)
    tx_data = {
        "sender": "alice",
        "key": "alice/balance",
        "value": "100"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    tx = Transaction("alice", "alice/balance", "100", signature, kp.public_key)
    
    # Add transaction to node0
    nodes[0].pending_transactions.append(tx)
    
    # Node0 proposes block
    nodes[0].propose_block()
    
    # Run simulation for 1 second
    for _ in range(20):  # 20 steps of 0.05s
        network.step(0.05)
    
    # Check all nodes finalized the same block
    finalized_heights = [node.current_height for node in nodes]
    assert all(h == 1 for h in finalized_heights), f"Heights: {finalized_heights}"
    
    # Check state hash is consistent
    state_hashes = [node.state.commitment() for node in nodes]
    assert len(set(state_hashes)) == 1, f"State hashes differ: {state_hashes}"
    
    print(f"✅ All nodes finalized block 1 with same state hash: {state_hashes[0][:16]}...")

def test_end_to_end_multiple_blocks():
    """Test end-to-end với nhiều blocks"""
    config = {
        "min_delay": 0.01,
        "max_delay": 0.05,
        "drop_rate": 0.0,
        "duplicate_rate": 0.0,
        "rate_limit": 1000
    }
    
    network = NetworkSimulator(config)
    
    # Create 8 nodes (minimum required)
    nodes = [Node(f"node{i}", is_validator=True, chain_id=CHAIN_ID) for i in range(8)]
    validator_ids = [f"node{i}" for i in range(8)]
    
    for node in nodes:
        network.register_node(node)
        node.set_network(network)
        node.set_validators(validator_ids)
    
    signer = Signer(CHAIN_ID)
    
    # Propose 3 blocks
    for block_num in range(3):
        # Create transaction
        kp = KeyPair()
        tx_data = {
            "sender": f"user{block_num}",
            "key": f"user{block_num}/message",
            "value": f"hello_{block_num}"
        }
        signature = signer.sign_transaction(kp.private_key, tx_data)
        tx = Transaction(f"user{block_num}", f"user{block_num}/message", 
                         f"hello_{block_num}", signature, kp.public_key)
        
        # Add to proposer
        proposer_idx = block_num % len(nodes)
        nodes[proposer_idx].pending_transactions.append(tx)
        nodes[proposer_idx].propose_block()
        
        # Run simulation
        for _ in range(20):
            network.step(0.05)
    
    # Check all nodes at height 3
    assert all(node.current_height == 3 for node in nodes)
    
    # Check consistent state
    state_hashes = [node.state.commitment() for node in nodes]
    assert len(set(state_hashes)) == 1
    
    print(f"✅ All 8 nodes finalized 3 blocks with consistent state")

def test_network_with_delays_and_drops():
    """Test với network không ổn định"""
    config = {
        "min_delay": 0.01,
        "max_delay": 0.2,  # Longer delays
        "drop_rate": 0.1,  # 10% drop
        "duplicate_rate": 0.05,  # 5% duplicate
        "rate_limit": 1000
    }
    
    network = NetworkSimulator(config)
    
    nodes = [Node(f"node{i}", is_validator=True, chain_id=CHAIN_ID) for i in range(8)]
    validator_ids = [f"node{i}" for i in range(8)]
    
    for node in nodes:
        network.register_node(node)
        node.set_network(network)
        node.set_validators(validator_ids)
    
    # Create and propose block
    kp = KeyPair()
    signer = Signer(CHAIN_ID)
    tx_data = {
        "sender": "alice",
        "key": "alice/test",
        "value": "unreliable_network"
    }
    signature = signer.sign_transaction(kp.private_key, tx_data)
    tx = Transaction("alice", "alice/test", "unreliable_network", signature, kp.public_key)
    
    nodes[0].pending_transactions.append(tx)
    nodes[0].propose_block()
    
    # Run longer to account for delays
    for _ in range(50):
        network.step(0.1)
    
    # Most nodes should eventually finalize
    finalized_count = sum(1 for node in nodes if node.current_height == 1)
    assert finalized_count >= 5, f"Only {finalized_count}/8 nodes finalized"
    
    # Nodes that finalized should have same state
    finalized_nodes = [node for node in nodes if node.current_height == 1]
    if finalized_nodes:
        state_hashes = [node.state.commitment() for node in finalized_nodes]
        assert len(set(state_hashes)) == 1
    
    print(f"✅ {finalized_count}/8 nodes finalized despite network issues")