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
    
    # Run simulation with extended time and progress checking
    max_steps = 40  # Increased from 20
    for step in range(max_steps):
        network.step(0.05)
        
        # Check progress every 10 steps
        if step % 10 == 9:
            finalized = sum(1 for n in nodes if n.current_height == 1)
            print(f"  Step {step+1}/{max_steps}: {finalized}/5 nodes finalized")
            
            # If all finalized, break early
            if finalized == 5:
                print(f"  ✓ All nodes finalized at step {step+1}")
                break
    
    # Check all nodes finalized the same block
    finalized_heights = [node.current_height for node in nodes]
    
    # Debug output if failed
    if not all(h == 1 for h in finalized_heights):
        print(f"\n  Heights: {finalized_heights}")
        for i, node in enumerate(nodes):
            print(f"  node{i}: height={node.current_height}, "
                  f"pending_blocks={list(node.pending_blocks.keys())}, "
                  f"prevotes={[(h, len(v)) for h, vdict in node.prevotes.items() for bhash, v in vdict.items()]}, "
                  f"precommits={[(h, len(v)) for h, vdict in node.precommits.items() for bhash, v in vdict.items()]}")
    
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
        print(f"\n  Proposing block {block_num + 1}/3...")
        
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
        
        # Add to proposer - find node at correct height
        proposer = None
        for node in nodes:
            if node.current_height == block_num:
                proposer = node
                break
        
        if proposer is None:
            # Fallback to round-robin if all nodes ahead
            proposer = nodes[block_num % len(nodes)]
        
        proposer.pending_transactions.append(tx)
        proposer.propose_block()
        
        # Run simulation with extended time
        max_steps = 40
        for step in range(max_steps):
            network.step(0.05)
            
            # Check progress
            if step % 10 == 9:
                finalized = sum(1 for n in nodes if n.current_height == block_num + 1)
                print(f"    Step {step+1}/{max_steps}: {finalized}/8 nodes at height {block_num + 1}")
                
                if finalized == 8:
                    print(f"    ✓ All nodes finalized block {block_num + 1}")
                    break
        
        # Check progress after this block
        finalized = sum(1 for n in nodes if n.current_height == block_num + 1)
        if finalized < 8:
            print(f"    ⚠️  Only {finalized}/8 nodes finalized block {block_num + 1}")
            heights = [n.current_height for n in nodes]
            print(f"    Heights: {heights}")
    
    # Final check
    final_heights = [node.current_height for node in nodes]
    print(f"\n  Final heights: {final_heights}")
    
    # Check all nodes at height 3
    assert all(node.current_height == 3 for node in nodes), f"Final heights: {final_heights}"
    
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