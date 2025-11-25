import pytest
import time
from src.network.simulator import NetworkSimulator
from src.network.node import Node
from src.network.message import Message, MessageType

def test_network_basic():
    """Test basic network functionality"""
    config = {
        "min_delay": 0.001,
        "max_delay": 0.01,
        "drop_rate": 0.0,
        "duplicate_rate": 0.0,
        "rate_limit": 1000
    }
    
    network = NetworkSimulator(config)
    
    node1 = Node("node1")
    node2 = Node("node2")
    
    network.register_node(node1)
    network.register_node(node2)
    
    node1.set_network(network)
    node2.set_network(network)
    
    # Send message
    msg = Message(MessageType.TRANSACTION, "node1", {"test": "data"})
    network.send("node1", "node2", msg)
    
    # Process with sufficient time for max_delay
    network.step(0.05)
    
    # Check received
    assert msg.msg_id in node2.seen_messages

def test_network_broadcast():
    """Test broadcast to multiple nodes"""
    config = {
        "min_delay": 0.001,
        "max_delay": 0.01,
        "drop_rate": 0.0,
        "duplicate_rate": 0.0,
        "rate_limit": 1000
    }
    
    network = NetworkSimulator(config)
    
    nodes = [Node(f"node{i}") for i in range(5)]
    for node in nodes:
        network.register_node(node)
        node.set_network(network)
    
    # Broadcast from node0
    msg = Message(MessageType.TRANSACTION, "node0", {"test": "broadcast"})
    network.broadcast("node0", msg)
    
    # Process with sufficient time
    network.step(0.05)
    
    # Check all other nodes received
    for i in range(1, 5):
        assert msg.msg_id in nodes[i].seen_messages

def test_network_drop():
    """Test message drop"""
    config = {
        "min_delay": 0.001,
        "max_delay": 0.01,
        "drop_rate": 1.0,  # 100% drop
        "duplicate_rate": 0.0,
        "rate_limit": 1000
    }
    
    network = NetworkSimulator(config)
    
    node1 = Node("node1")
    node2 = Node("node2")
    
    network.register_node(node1)
    network.register_node(node2)
    
    node1.set_network(network)
    node2.set_network(network)
    
    # Send message
    msg = Message(MessageType.TRANSACTION, "node1", {"test": "drop"})
    network.send("node1", "node2", msg)
    
    # Process
    network.step(0.05)
    
    # Should be dropped
    assert msg.msg_id not in node2.seen_messages
    
    # Check drop event logged
    events = network.get_events()
    drop_events = [e for e in events if e["event"] == "drop"]
    assert len(drop_events) > 0

def test_rate_limiting():
    """Test rate limiting"""
    config = {
        "min_delay": 0.001,
        "max_delay": 0.01,
        "drop_rate": 0.0,
        "duplicate_rate": 0.0,
        "rate_limit": 5  # Only 5 messages per second
    }
    
    network = NetworkSimulator(config)
    
    node1 = Node("node1")
    node2 = Node("node2")
    
    network.register_node(node1)
    network.register_node(node2)
    
    node1.set_network(network)
    node2.set_network(network)
    
    # Send 10 messages
    for i in range(10):
        msg = Message(MessageType.TRANSACTION, "node1", {"id": i})
        network.send("node1", "node2", msg)
    
    # Check rate limit events
    events = network.get_events()
    rate_limit_events = [e for e in events if e["event"] == "rate_limited"]
    assert len(rate_limit_events) >= 5  # At least 5 should be rate limited