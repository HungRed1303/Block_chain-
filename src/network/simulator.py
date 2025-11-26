"""
Network Simulator with Enhanced Logging
FIX: Add height to all network events as required by spec
"""
import random
import time
from queue import PriorityQueue
from src.network.message import NetworkEvent
from src.utils.logger import Logger

class NetworkSimulator:
    """Network simulator with complete event logging"""
    
    def __init__(self, config):
        self.config = config
        self.nodes = {}
        self.message_queue = PriorityQueue()
        self.current_time = 0
        self.events = []
        self.logger = Logger("network")
        
        self.min_delay = config.get("min_delay", 0.01)
        self.max_delay = config.get("max_delay", 0.5)
        self.drop_rate = config.get("drop_rate", 0.05)
        self.duplicate_rate = config.get("duplicate_rate", 0.02)
        self.rate_limit = config.get("rate_limit", 100)
        self.node_send_counts = {}
    
    def register_node(self, node):
        self.nodes[node.node_id] = node
        self.node_send_counts[node.node_id] = (0, self.current_time)
        self.logger.log(f"Node {node.node_id} registered")
    
    def _extract_height(self, message):
        """Extract height from message data for logging"""
        try:
            if hasattr(message.data, 'height'):
                return message.data.height
            elif isinstance(message.data, dict):
                if 'height' in message.data:
                    return message.data['height']
                elif 'data' in message.data and isinstance(message.data['data'], dict):
                    return message.data['data'].get('height')
        except:
            pass
        return None
    
    def _check_rate_limit(self, node_id):
        count, window_start = self.node_send_counts[node_id]
        
        if self.current_time - window_start >= 1.0:
            self.node_send_counts[node_id] = (1, self.current_time)
            return True
        
        if count >= self.rate_limit:
            self.logger.log(f"Rate limit exceeded for node {node_id}")
            return False
        
        self.node_send_counts[node_id] = (count + 1, window_start)
        return True
    
    def broadcast(self, sender_id, message):
        """Broadcast with height logging"""
        if not self._check_rate_limit(sender_id):
            height = self._extract_height(message)
            event = NetworkEvent(
                "rate_limited", 
                self.current_time, 
                sender_id, 
                message,
                {"broadcast": True, "height": height}
            )
            self.events.append(event)
            return
        
        height = self._extract_height(message)
        send_event = NetworkEvent(
            "send", 
            self.current_time, 
            sender_id, 
            message, 
            {"broadcast": True, "height": height}
        )
        self.events.append(send_event)
        
        for node_id in self.nodes:
            if node_id != sender_id:
                self._deliver_message(sender_id, node_id, message)
    
    def send(self, sender_id, recipient_id, message):
        """Send with height logging"""
        if not self._check_rate_limit(sender_id):
            height = self._extract_height(message)
            event = NetworkEvent(
                "rate_limited", 
                self.current_time, 
                sender_id, 
                message,
                {"recipient": recipient_id, "height": height}
            )
            self.events.append(event)
            return
        
        height = self._extract_height(message)
        send_event = NetworkEvent(
            "send", 
            self.current_time, 
            sender_id, 
            message,
            {"recipient": recipient_id, "height": height}
        )
        self.events.append(send_event)
        
        self._deliver_message(sender_id, recipient_id, message)
    
    def _deliver_message(self, sender_id, recipient_id, message):
        """Deliver with complete logging including height"""
        height = self._extract_height(message)
        
        # Random drop
        if random.random() < self.drop_rate:
            event = NetworkEvent(
                "drop", 
                self.current_time, 
                recipient_id, 
                message,
                {"reason": "random_drop", "height": height}
            )
            self.events.append(event)
            self.logger.log(f"Message dropped: {message.msg_id} to {recipient_id} (height={height})")
            return
        
        # Calculate delivery time
        delay = random.uniform(self.min_delay, self.max_delay)
        delivery_time = self.current_time + delay
        
        # Add to queue
        self.message_queue.put((delivery_time, message, recipient_id, sender_id))
        
        event = NetworkEvent(
            "delay", 
            self.current_time, 
            recipient_id, 
            message,
            {"delay": delay, "delivery_time": delivery_time, "height": height}
        )
        self.events.append(event)
        
        # Random duplicate
        if random.random() < self.duplicate_rate:
            dup_delay = delay + random.uniform(0.01, 0.1)
            dup_delivery_time = self.current_time + dup_delay
            self.message_queue.put((dup_delivery_time, message, recipient_id, sender_id))
            
            dup_event = NetworkEvent(
                "duplicate", 
                self.current_time, 
                recipient_id, 
                message,
                {"original_delay": delay, "dup_delay": dup_delay, "height": height}
            )
            self.events.append(dup_event)
    
    def process_messages(self, until_time=None):
        """Process messages with height logging"""
        if until_time is None:
            until_time = self.current_time + 1.0
        
        while not self.message_queue.empty():
            delivery_time, message, recipient_id, sender_id = self.message_queue.queue[0]
            
            if delivery_time > until_time:
                break
            
            self.message_queue.get()
            self.current_time = delivery_time
            
            if recipient_id in self.nodes:
                self.nodes[recipient_id].receive_message(message)
                
                height = self._extract_height(message)
                receive_event = NetworkEvent(
                    "receive", 
                    self.current_time, 
                    recipient_id, 
                    message,
                    {"from": sender_id, "height": height}
                )
                self.events.append(receive_event)
                self.logger.log(
                    f"Node {recipient_id} received {message.msg_type.value} "
                    f"from {sender_id} (height={height})"
                )
        
        self.current_time = until_time
    
    def get_events(self):
        """Return all logged events"""
        return [event.to_dict() for event in self.events]
    
    def step(self, duration=0.1):
        """Execute one simulation step"""
        self.process_messages(self.current_time + duration)