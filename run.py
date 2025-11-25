import sys
import json
from src.network.simulator import NetworkSimulator
from src.network.node import Node
from src.network.message import Message, MessageType
from src.execution.transaction import Transaction
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer
from src.utils.logger import DeterministicLogger

# Force UTF-8 encoding for stdout (Windows safe)
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def load_config(config_file):
    """Load configuration from file"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_simulation(config):
    """Run blockchain simulation"""
    print("=" * 60)
    print("BLOCKCHAIN SIMULATOR - Starting...")
    print("=" * 60)
    
    # Create logger
    log_file = config.get("log_file", "logs/simulation.log")
    det_logger = DeterministicLogger(log_file)  # Ensure UTF-8 for file
    
    # Setup network
    network_config = config.get("network", {})
    network = NetworkSimulator(network_config)
    
    # Create nodes
    num_nodes = config.get("num_nodes", 8)
    nodes = []
    validator_ids = []
    
    print(f"\nCreating {num_nodes} nodes...")
    for i in range(num_nodes):
        node_id = f"node{i}"
        node = Node(node_id, is_validator=True, chain_id=config.get("chain_id", "mainnet"))
        network.register_node(node)
        node.set_network(network)
        nodes.append(node)
        validator_ids.append(node_id)
        print(f"  [OK] {node_id} created")
    
    # Set validators for all nodes
    for node in nodes:
        node.set_validators(validator_ids)
    
    print(f"\n{num_nodes} nodes initialized")
    
    # Create transactions
    signer = Signer(config.get("chain_id", "mainnet"))
    transactions = []
    
    print(f"\nCreating transactions...")
    num_txs = config.get("num_transactions", 5)
    for i in range(num_txs):
        kp = KeyPair()
        tx_data = {
            "sender": f"user{i}",
            "key": f"user{i}/balance",
            "value": str((i + 1) * 100)
        }
        signature = signer.sign_transaction(kp.private_key, tx_data)
        tx = Transaction(f"user{i}", f"user{i}/balance", str((i + 1) * 100), 
                        signature, kp.public_key)
        transactions.append(tx)
        print(f"  [OK] Transaction {i}: user{i}/balance = {(i+1)*100}")
        
        det_logger.log_event("transaction_created", {
            "tx_id": i,
            "sender": f"user{i}",
            "key": f"user{i}/balance",
            "value": str((i + 1) * 100)
        })
    
    # Distribute transactions to nodes
    print(f"\nDistributing transactions to nodes...")
    for i, tx in enumerate(transactions):
        node_idx = i % num_nodes
        nodes[node_idx].pending_transactions.append(tx)
        print(f"  [OK] Transaction {i} → node{node_idx}")
    
    # Run simulation
    num_blocks = config.get("num_blocks", 3)
    simulation_duration = config.get("simulation_duration", 2.0)
    
    print(f"\nStarting simulation ({num_blocks} blocks, {simulation_duration}s per block)...")
    print("-" * 60)
    
    for block_num in range(num_blocks):
        print(f"\nBlock {block_num + 1}/{num_blocks}")
        
        # Proposer rotates
        proposer_idx = block_num % num_nodes
        proposer = nodes[proposer_idx]
        
        if proposer.pending_transactions:
            print(f"  node{proposer_idx} proposing block...")
            proposer.propose_block()
            
            det_logger.log_event("block_proposed", {
                "height": block_num + 1,
                "proposer": proposer.node_id,
                "num_txs": len(proposer.pending_transactions)
            })
        
        # Run network simulation
        steps = int(simulation_duration / 0.05)
        for step in range(steps):
            network.step(0.05)
            
            # Print progress
            if step % 10 == 0:
                finalized_count = sum(1 for n in nodes if n.current_height == block_num + 1)
                print(f"  Step {step}/{steps}: {finalized_count}/{num_nodes} nodes finalized", end='\r')
        
        print()  # New line
        
        # Check finalization
        finalized_count = sum(1 for n in nodes if n.current_height == block_num + 1)
        print(f"  Finalization: {finalized_count}/{num_nodes} nodes")
        
        det_logger.log_event("block_finalized", {
            "height": block_num + 1,
            "finalized_nodes": finalized_count,
            "total_nodes": num_nodes
        })
    
    # Final verification
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    # Check heights
    heights = [node.current_height for node in nodes]
    print(f"\nNode heights: {heights}")
    print(f"  Min: {min(heights)}, Max: {max(heights)}, Avg: {sum(heights)/len(heights):.1f}")
    
    # Check state consistency
    state_hashes = [node.state.commitment() for node in nodes]
    unique_hashes = set(state_hashes)
    
    print(f"\nState hashes:")
    for i, h in enumerate(state_hashes):
        print(f"  node{i}: {h[:16]}...")
    
    if len(unique_hashes) == 1:
        print(f"\nALL NODES HAVE CONSISTENT STATE")
        print(f"  Final state hash: {list(unique_hashes)[0]}")
    else:
        print(f"\nWARNING: {len(unique_hashes)} different state hashes detected!")
    
    # Network statistics
    events = network.get_events()
    event_types = {}
    for event in events:
        event_type = event["event"]
        event_types[event_type] = event_types.get(event_type, 0) + 1
    
    print(f"\nNetwork Statistics:")
    for event_type, count in sorted(event_types.items()):
        print(f"  {event_type}: {count}")
    
    # Save logs
    det_logger.save()
    print(f"\nLogs saved to: {log_file}")
    print(f"  Log hash: {det_logger.get_hash()[:16]}...")
    
    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    
    return len(unique_hashes) == 1


def main():
    """Main function"""
    if len(sys.argv) < 2:
        config_file = "config/chain_config.json"
        print(f"Using default config: {config_file}")
    else:
        config_file = sys.argv[1]
    
    try:
        config = load_config(config_file)
        success = run_simulation(config)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
