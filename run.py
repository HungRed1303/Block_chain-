import sys
import json
import time
from src.network.simulator import NetworkSimulator
from src.network.node import Node
from src.network.message import Message, MessageType
from src.execution.transaction import Transaction
from src.crypto.keys import KeyPair
from src.crypto.signatures import Signer
from src.utils.logger import DeterministicLogger

# Force UTF-8 encoding for stdout
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def load_config(config_file):
    """Load configuration from file"""
    with open(config_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_simulation(config):
    """Run blockchain simulation - FINAL VERSION"""
    print("=" * 60)
    print("BLOCKCHAIN SIMULATOR - Starting...")
    print("=" * 60)
    
    # Create logger
    log_file = config.get("log_file", "logs/simulation.json")
    det_logger = DeterministicLogger(log_file)
    
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
    
    # Run simulation
    num_blocks = config.get("num_blocks", 3)
    simulation_duration = config.get("simulation_duration", 2.0)
    
    print(f"\nStarting simulation ({num_blocks} blocks, {simulation_duration}s per block)...")
    print("-" * 60)
    
    for block_num in range(num_blocks):
        print(f"\nBlock {block_num + 1}/{num_blocks}")
        
        # Distribute transactions for this block
        txs_this_block = []
        txs_per_block = len(transactions) // num_blocks
        start_idx = block_num * txs_per_block
        end_idx = start_idx + txs_per_block if block_num < num_blocks - 1 else len(transactions)
        txs_this_block = transactions[start_idx:end_idx]
        
        # Find proposer at correct height
        proposer = None
        for i, node in enumerate(nodes):
            if node.current_height == block_num:
                proposer = node
                proposer_idx = i
                break
        
        if proposer is None:
            print(f"  WARNING: No node at height {block_num}, using node0")
            proposer = nodes[0]
            proposer_idx = 0
        
        # Add transactions to proposer
        proposer.pending_transactions = txs_this_block
        
        print(f"  node{proposer_idx} (height={proposer.current_height}) proposing with {len(txs_this_block)} txs...")
        proposer.propose_block()
        
        det_logger.log_event("block_proposed", {
            "height": block_num + 1,
            "proposer": proposer.node_id,
            "num_txs": len(txs_this_block)
        })
        
        # Run simulation with extended wait for stragglers
        steps = int(simulation_duration / 0.05)
        last_finalized = 0
        stagnant_count = 0
        
        for step in range(steps):
            network.step(0.05)
            
            # Check finalization
            finalized_count = sum(1 for n in nodes if n.current_height == block_num + 1)
            
            # Print progress
            if step % 10 == 0:
                print(f"  Step {step}/{steps}: {finalized_count}/{num_nodes} nodes finalized", end='\r')
            
            # FIX: Extended wait if making progress
            if finalized_count == num_nodes:
                print(f"  Step {step}/{steps}: {finalized_count}/{num_nodes} nodes finalized ✓")
                break
            
            # Track stagnation
            if finalized_count == last_finalized:
                stagnant_count += 1
            else:
                stagnant_count = 0
                last_finalized = finalized_count
            
            # FIX: If stagnant for too long, continue extra steps
            if stagnant_count > 20 and finalized_count >= num_nodes * 0.75:
                # 75% nodes finalized and no progress for 1s -> acceptable
                break
        
        # FIX: Extra rounds for stragglers
        if finalized_count < num_nodes and finalized_count >= num_nodes * 0.5:
            print(f"\n  Running extra rounds for {num_nodes - finalized_count} stragglers...")
            extra_steps = 20
            for step in range(extra_steps):
                network.step(0.1)
                new_count = sum(1 for n in nodes if n.current_height == block_num + 1)
                if new_count > finalized_count:
                    finalized_count = new_count
                    print(f"  Extra step {step}: {finalized_count}/{num_nodes} nodes finalized", end='\r')
                if finalized_count == num_nodes:
                    print(f"  Extra step {step}: {finalized_count}/{num_nodes} nodes finalized ✓")
                    break
        
        print()  # New line
        
        # Final check
        finalized_count = sum(1 for n in nodes if n.current_height == block_num + 1)
        print(f"  Finalization: {finalized_count}/{num_nodes} nodes")
        
        if finalized_count < num_nodes:
            behind = [f"node{i}(h={n.current_height})" for i, n in enumerate(nodes) 
                     if n.current_height != block_num + 1]
            print(f"  Behind: {', '.join(behind)}")
            
            # FIX: Last resort - retry votes
            for node in nodes:
                if node.current_height == block_num:
                    # Check if node has the block
                    if block_num + 1 in node.pending_blocks:
                        block = node.pending_blocks[block_num + 1]
                        # Resend votes if we haven't
                        if (block.height, block.hash) not in node.sent_prevotes:
                            node._send_prevote(block)
            
            # Run a few more steps
            for _ in range(10):
                network.step(0.1)
            
            # Final final check
            finalized_count = sum(1 for n in nodes if n.current_height == block_num + 1)
            if finalized_count == num_nodes:
                print(f"  ✓ All nodes caught up!")
        
        det_logger.log_event("block_finalized", {
            "height": block_num + 1,
            "finalized_nodes": finalized_count,
            "total_nodes": num_nodes
        })
        
        # Wait before next block
        if block_num < num_blocks - 1:
            time.sleep(0.1)
    
    # Final verification
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    # Check heights
    heights = [node.current_height for node in nodes]
    print(f"\nNode heights: {heights}")
    print(f"  Min: {min(heights)}, Max: {max(heights)}, Avg: {sum(heights)/len(heights):.1f}")
    
    success = True
    
    if min(heights) != max(heights):
        print(f"  ⚠️  WARNING: Nodes at different heights!")
        success = False
    else:
        print(f"  ✓ All nodes at same height")
    
    # Check state consistency
    state_hashes = [node.state.commitment() for node in nodes]
    unique_hashes = set(state_hashes)
    
    print(f"\nState hashes:")
    for i, h in enumerate(state_hashes):
        print(f"  node{i}: {h[:16]}...")
    
    if len(unique_hashes) == 1:
        print(f"\n✓ ALL NODES HAVE CONSISTENT STATE")
        print(f"  Final state hash: {list(unique_hashes)[0]}")
    else:
        print(f"\n✗ FAILURE: {len(unique_hashes)} different state hashes detected!")
        for h in unique_hashes:
            nodes_with_hash = [i for i, node_hash in enumerate(state_hashes) if node_hash == h]
            print(f"  {h[:16]}...: nodes {nodes_with_hash}")
        success = False
    
    # Ledger verification
    print(f"\nLedger verification:")
    for height in range(1, num_blocks + 1):
        hashes_at_height = set()
        nodes_with_block = []
        for i, node in enumerate(nodes):
            if len(node.ledger) >= height:
                hashes_at_height.add(node.ledger[height-1].hash)
                nodes_with_block.append(i)
        
        if len(hashes_at_height) == 0:
            print(f"  Height {height}: ✗ No nodes have block")
            success = False
        elif len(hashes_at_height) == 1:
            print(f"  Height {height}: ✓ All nodes agree on {list(hashes_at_height)[0][:8]}...")
        else:
            print(f"  Height {height}: ✗ {len(hashes_at_height)} different blocks!")
            success = False
    
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
    if success:
        print("✓ SIMULATION SUCCESSFUL")
    else:
        print("✗ SIMULATION FAILED")
    print("=" * 60)
    
    return success


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