"""
Security and Safety Tests - REQUIRED BY LAB SPEC
Tests for signature validation, replay attacks, and safety guarantees
"""
import pytest
from src.network.simulator import NetworkSimulator
from src.network.node import Node
from src.network.message import Message, MessageType
from src.execution.transaction import Transaction
from src.execution.block import Block
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer
from src.consensus.vote import Vote

CHAIN_ID = "mainnet"


class TestInvalidSignatures:
    """Test rejection of invalid signatures (Requirement 9.2)"""
    
    def test_reject_transaction_wrong_signature(self):
        """Transaction with wrong signature must be rejected"""
        config = {
            "min_delay": 0.001,
            "max_delay": 0.01,
            "drop_rate": 0.0,
            "duplicate_rate": 0.0,
            "rate_limit": 1000
        }
        
        network = NetworkSimulator(config)
        node = Node("node0", is_validator=True, chain_id=CHAIN_ID)
        network.register_node(node)
        node.set_network(network)
        
        # Create transaction signed by kp1
        kp1 = KeyPair()
        kp2 = KeyPair()
        signer = Signer(CHAIN_ID)
        
        tx_data = {
            "sender": "alice",
            "key": "alice/balance",
            "value": "100"
        }
        signature = signer.sign_transaction(kp1.private_key, tx_data)
        
        # But attach kp2's public key (WRONG!)
        tx = Transaction("alice", "alice/balance", "100", signature, kp2.public_key)
        
        # Send to node
        msg = Message(MessageType.TRANSACTION, "external", tx)
        node.receive_message(msg)
        
        # Transaction should NOT be in pending
        assert len(node.pending_transactions) == 0, "Invalid tx should be rejected"
    
    def test_reject_vote_wrong_context(self):
        """Vote with wrong domain context must be rejected"""
        config = {
            "min_delay": 0.001,
            "max_delay": 0.01,
            "drop_rate": 0.0,
            "duplicate_rate": 0.0,
            "rate_limit": 1000
        }
        
        network = NetworkSimulator(config)
        node1 = Node("node1", is_validator=True, chain_id=CHAIN_ID)
        node2 = Node("node2", is_validator=True, chain_id=CHAIN_ID)
        
        network.register_node(node1)
        network.register_node(node2)
        node1.set_network(network)
        node2.set_network(network)
        node1.set_validators(["node1", "node2"])
        node2.set_validators(["node1", "node2"])
        
        # Create vote data
        vote_data = {
            "height": 1,
            "block_hash": "abc123",
            "phase": "prevote",
            "voter": "node1"
        }
        
        # Sign with HEADER domain instead of VOTE (WRONG!)
        wrong_signature = node1.signer.sign_header(node1.key_pair.private_key, vote_data)
        
        vote = {
            "data": vote_data,
            "signature": wrong_signature,
            "public_key": node1.key_pair.public_key
        }
        
        msg = Message(MessageType.PREVOTE, "node1", vote)
        
        # Track prevotes before
        prevotes_before = len(node2.prevotes.get(1, {}).get("abc123", set()))
        
        # Send message
        node2.receive_message(msg)
        
        # Prevotes should NOT increase (wrong signature context)
        prevotes_after = len(node2.prevotes.get(1, {}).get("abc123", set()))
        assert prevotes_after == prevotes_before, "Vote with wrong context should be rejected"
    
    def test_reject_transaction_wrong_chain_id(self):
        """Transaction signed for different chain_id must be rejected"""
        node = Node("node0", is_validator=True, chain_id="mainnet")
        
        # Sign for "testnet"
        kp = KeyPair()
        signer_testnet = Signer("testnet")
        
        tx_data = {
            "sender": "alice",
            "key": "alice/balance",
            "value": "100"
        }
        signature = signer_testnet.sign_transaction(kp.private_key, tx_data)
        tx = Transaction("alice", "alice/balance", "100", signature, kp.public_key)
        
        # Try to verify on mainnet
        assert not tx.verify(chain_id="mainnet"), "Wrong chain_id should fail"


class TestReplayAttacks:
    """Test replay attack prevention (Requirement 9.3)"""
    
    def test_duplicate_message_ignored(self):
        """Duplicate messages should be ignored"""
        config = {
            "min_delay": 0.001,
            "max_delay": 0.01,
            "drop_rate": 0.0,
            "duplicate_rate": 0.0,
            "rate_limit": 1000
        }
        
        network = NetworkSimulator(config)
        node = Node("node0", is_validator=True, chain_id=CHAIN_ID)
        network.register_node(node)
        node.set_network(network)
        
        # Create valid transaction
        kp = KeyPair()
        signer = Signer(CHAIN_ID)
        tx_data = {
            "sender": "alice",
            "key": "alice/balance",
            "value": "100"
        }
        signature = signer.sign_transaction(kp.private_key, tx_data)
        tx = Transaction("alice", "alice/balance", "100", signature, kp.public_key)
        
        msg = Message(MessageType.TRANSACTION, "external", tx)
        
        # Send first time
        node.receive_message(msg)
        assert len(node.pending_transactions) == 1
        
        # Send again (duplicate)
        node.receive_message(msg)
        
        # Should still be 1 (not added twice)
        assert len(node.pending_transactions) == 1, "Duplicate should be ignored"
    
    def test_replay_vote_different_height_rejected(self):
        """Vote replayed at different height should be rejected"""
        config = {
            "min_delay": 0.001,
            "max_delay": 0.01,
            "drop_rate": 0.0,
            "duplicate_rate": 0.0,
            "rate_limit": 1000
        }
        
        network = NetworkSimulator(config)
        node = Node("node0", is_validator=True, chain_id=CHAIN_ID)
        network.register_node(node)
        node.set_network(network)
        node.set_validators(["node0"])
        
        # Create vote for height 1
        vote_data_h1 = {
            "height": 1,
            "block_hash": "abc123",
            "phase": "prevote",
            "voter": "node0"
        }
        signature = node.signer.sign_vote(node.key_pair.private_key, vote_data_h1)
        
        # Try to replay at height 2 (just change data, keep same signature)
        vote_data_h2 = {
            "height": 2,  # Changed!
            "block_hash": "abc123",
            "phase": "prevote",
            "voter": "node0"
        }
        
        vote = {
            "data": vote_data_h2,
            "signature": signature,  # Original signature for height 1
            "public_key": node.key_pair.public_key
        }
        
        msg = Message(MessageType.PREVOTE, "node0", vote)
        
        # Should fail verification
        assert not node.signer.verify_vote(node.key_pair.public_key, vote_data_h2, signature), \
            "Replayed vote with different height should fail"


class TestSafetyUnderNetworkFailures:
    """Test safety under network issues (Requirement 9.4)"""
    
    def test_no_conflicting_finalization_with_drops(self):
        """Dropped messages should not cause conflicting finalization"""
        config = {
            "min_delay": 0.01,
            "max_delay": 0.1,
            "drop_rate": 0.3,  # 30% drop rate
            "duplicate_rate": 0.1,
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
        
        nodes[0].pending_transactions.append(tx)
        nodes[0].propose_block()
        
        # Run simulation
        for _ in range(50):
            network.step(0.1)
        
        # Collect finalized blocks at height 1
        finalized_hashes = set()
        for node in nodes:
            if node.current_height == 1 and len(node.ledger) > 0:
                finalized_hashes.add(node.ledger[0].hash)
        
        # SAFETY: At most 1 unique hash should be finalized
        assert len(finalized_hashes) <= 1, \
            f"SAFETY VIOLATION: {len(finalized_hashes)} different blocks finalized at height 1"
    
    def test_delayed_messages_no_conflict(self):
        """Long delays should not cause conflicting finalization"""
        config = {
            "min_delay": 0.1,
            "max_delay": 1.0,  # Very long delays
            "drop_rate": 0.1,
            "duplicate_rate": 0.05,
            "rate_limit": 1000
        }
        
        network = NetworkSimulator(config)
        
        nodes = [Node(f"node{i}", is_validator=True, chain_id=CHAIN_ID) for i in range(5)]
        validator_ids = [f"node{i}" for i in range(5)]
        
        for node in nodes:
            network.register_node(node)
            node.set_network(network)
            node.set_validators(validator_ids)
        
        # Propose block
        kp = KeyPair()
        signer = Signer(CHAIN_ID)
        tx_data = {
            "sender": "alice",
            "key": "alice/test",
            "value": "delayed"
        }
        signature = signer.sign_transaction(kp.private_key, tx_data)
        tx = Transaction("alice", "alice/test", "delayed", signature, kp.public_key)
        
        nodes[0].pending_transactions.append(tx)
        nodes[0].propose_block()
        
        # Run with extended time
        for _ in range(60):
            network.step(0.2)
        
        # Check safety
        finalized_blocks = {}
        for node in nodes:
            if node.current_height == 1 and len(node.ledger) > 0:
                block = node.ledger[0]
                if 1 not in finalized_blocks:
                    finalized_blocks[1] = set()
                finalized_blocks[1].add(block.hash)
        
        # Each height should have at most 1 unique block hash
        for height, hashes in finalized_blocks.items():
            assert len(hashes) == 1, \
                f"SAFETY VIOLATION at height {height}: {len(hashes)} different blocks"


class TestDeterminism:
    """Test deterministic execution (Requirement 9.5)"""
    
    def test_same_config_same_result(self):
        """Same configuration should produce same final state"""
        config = {
            "min_delay": 0.01,
            "max_delay": 0.05,
            "drop_rate": 0.0,
            "duplicate_rate": 0.0,
            "rate_limit": 1000
        }
        
        def run_simulation():
            network = NetworkSimulator(config)
            
            nodes = [Node(f"node{i}", is_validator=True, chain_id=CHAIN_ID) for i in range(4)]
            validator_ids = [f"node{i}" for i in range(4)]
            
            for node in nodes:
                network.register_node(node)
                node.set_network(network)
                node.set_validators(validator_ids)
            
            # Create deterministic transaction
            kp = KeyPair()
            signer = Signer(CHAIN_ID)
            tx_data = {
                "sender": "alice",
                "key": "alice/balance",
                "value": "100"
            }
            signature = signer.sign_transaction(kp.private_key, tx_data)
            tx = Transaction("alice", "alice/balance", "100", signature, kp.public_key)
            
            nodes[0].pending_transactions.append(tx)
            nodes[0].propose_block()
            
            for _ in range(30):
                network.step(0.05)
            
            # Return final state hashes
            return [node.state.commitment() for node in nodes]
        
        # Run twice
        result1 = run_simulation()
        result2 = run_simulation()
        
        # Note: With random delays, final states may differ
        # But nodes within each run should agree
        assert len(set(result1)) == 1, "Nodes in run 1 should agree"
        assert len(set(result2)) == 1, "Nodes in run 2 should agree"
        
        # The consensus state should be the same
        # (even if timing differs, same transactions -> same state)
        assert result1[0] == result2[0], "Final states should be deterministic"


class TestEdgeCases:
    """Additional edge cases for robustness"""
    
    def test_empty_block(self):
        """Node should handle empty block (no transactions)"""
        node = Node("node0", is_validator=True, chain_id=CHAIN_ID)
        node.set_validators(["node0"])
        
        # Propose with no transactions
        node.pending_transactions = []
        node.propose_block()
        
        # Should not crash, just skip
        assert node.current_height == 0
    
    def test_transaction_unauthorized_key(self):
        """Transaction modifying someone else's key should be rejected"""
        kp = KeyPair()
        signer = Signer(CHAIN_ID)
        
        # Alice tries to modify Bob's balance
        tx_data = {
            "sender": "alice",
            "key": "bob/balance",  # Not alice's key!
            "value": "999999"
        }
        signature = signer.sign_transaction(kp.private_key, tx_data)
        tx = Transaction("alice", "bob/balance", "999999", signature, kp.public_key)
        
        # Should fail verification
        assert not tx.verify(chain_id=CHAIN_ID)
    
    def test_vote_from_non_validator(self):
        """Vote from non-validator should be ignored"""
        config = {
            "min_delay": 0.001,
            "max_delay": 0.01,
            "drop_rate": 0.0,
            "duplicate_rate": 0.0,
            "rate_limit": 1000
        }
        
        network = NetworkSimulator(config)
        node = Node("validator1", is_validator=True, chain_id=CHAIN_ID)
        network.register_node(node)
        node.set_network(network)
        node.set_validators(["validator1", "validator2"])  # Only 2 validators
        
        # Create vote from non-validator
        non_validator = Node("attacker", is_validator=False, chain_id=CHAIN_ID)
        
        vote_data = {
            "height": 1,
            "block_hash": "abc123",
            "phase": "prevote",
            "voter": "attacker"
        }
        signature = non_validator.signer.sign_vote(non_validator.key_pair.private_key, vote_data)
        
        vote = {
            "data": vote_data,
            "signature": signature,
            "public_key": non_validator.key_pair.public_key
        }
        
        msg = Message(MessageType.PREVOTE, "attacker", vote)
        
        # Send to validator
        node.receive_message(msg)
        
        # Vote should be ignored (attacker not in validator set)
        assert 1 not in node.prevotes or "abc123" not in node.prevotes.get(1, {})


# Run all tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])