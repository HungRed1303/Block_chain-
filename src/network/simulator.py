import random
import time
from queue import PriorityQueue
from src.network.message import NetworkEvent
from src.utils.logger import Logger

class NetworkSimulator:
    """Mô phỏng mạng không ổn định"""
    
    def __init__(self, config):
        self.config = config
        self.nodes = {}  # node_id -> Node
        self.message_queue = PriorityQueue()  # (delivery_time, message, recipient_id)
        self.current_time = 0
        self.events = []  # Log tất cả events
        self.logger = Logger("network")
        
        # Network parameters
        self.min_delay = config.get("min_delay", 0.01)  # 10ms
        self.max_delay = config.get("max_delay", 0.5)   # 500ms
        self.drop_rate = config.get("drop_rate", 0.05)  # 5% drop
        self.duplicate_rate = config.get("duplicate_rate", 0.02)  # 2% duplicate
        
        # Rate limiting
        self.rate_limit = config.get("rate_limit", 100)  # messages per second
        self.node_send_counts = {}  # node_id -> (count, window_start)
    
    def register_node(self, node):
        """Đăng ký một node vào network"""
        self.nodes[node.node_id] = node
        self.node_send_counts[node.node_id] = (0, self.current_time)
        self.logger.log(f"Node {node.node_id} registered")
    
    def _check_rate_limit(self, node_id):
        """Kiểm tra rate limit cho node"""
        count, window_start = self.node_send_counts[node_id]
        
        # Reset window nếu đã qua 1 giây
        if self.current_time - window_start >= 1.0:
            self.node_send_counts[node_id] = (1, self.current_time)
            return True
        
        # Check limit
        if count >= self.rate_limit:
            self.logger.log(f"Rate limit exceeded for node {node_id}")
            return False
        
        # Increment count
        self.node_send_counts[node_id] = (count + 1, window_start)
        return True
    
    def broadcast(self, sender_id, message):
        """Broadcast message đến tất cả nodes khác"""
        if not self._check_rate_limit(sender_id):
            # Log rate limit event
            event = NetworkEvent("rate_limited", self.current_time, sender_id, message)
            self.events.append(event)
            return
        
        # Log send event
        send_event = NetworkEvent("send", self.current_time, sender_id, message, 
                                   {"broadcast": True})
        self.events.append(send_event)
        
        for node_id in self.nodes:
            if node_id != sender_id:
                self._deliver_message(sender_id, node_id, message)
    
    def send(self, sender_id, recipient_id, message):
        """Gửi message đến một node cụ thể"""
        if not self._check_rate_limit(sender_id):
            event = NetworkEvent("rate_limited", self.current_time, sender_id, message)
            self.events.append(event)
            return
        
        send_event = NetworkEvent("send", self.current_time, sender_id, message,
                                   {"recipient": recipient_id})
        self.events.append(send_event)
        
        self._deliver_message(sender_id, recipient_id, message)
    
    def _deliver_message(self, sender_id, recipient_id, message):
        """Xử lý delivery với delay, drop, duplicate"""
        
        # Random drop
        if random.random() < self.drop_rate:
            event = NetworkEvent("drop", self.current_time, recipient_id, message,
                                 {"reason": "random_drop"})
            self.events.append(event)
            self.logger.log(f"Message dropped: {message.msg_id} to {recipient_id}")
            return
        
        # Calculate delivery time with random delay
        delay = random.uniform(self.min_delay, self.max_delay)
        delivery_time = self.current_time + delay
        
        # Add to queue
        self.message_queue.put((delivery_time, message, recipient_id, sender_id))
        
        event = NetworkEvent("delay", self.current_time, recipient_id, message,
                             {"delay": delay, "delivery_time": delivery_time})
        self.events.append(event)
        
        # Random duplicate
        if random.random() < self.duplicate_rate:
            dup_delay = delay + random.uniform(0.01, 0.1)
            dup_delivery_time = self.current_time + dup_delay
            self.message_queue.put((dup_delivery_time, message, recipient_id, sender_id))
            
            dup_event = NetworkEvent("duplicate", self.current_time, recipient_id, message,
                                     {"original_delay": delay, "dup_delay": dup_delay})
            self.events.append(dup_event)
    
    def process_messages(self, until_time=None):
        """Process messages cho đến một thời điểm"""
        if until_time is None:
            until_time = self.current_time + 1.0
        
        while not self.message_queue.empty():
            delivery_time, message, recipient_id, sender_id = self.message_queue.queue[0]
            
            if delivery_time > until_time:
                break
            
            # Remove from queue
            self.message_queue.get()
            
            # Update current time
            self.current_time = delivery_time
            
            # Deliver to node
            if recipient_id in self.nodes:
                self.nodes[recipient_id].receive_message(message)
                
                receive_event = NetworkEvent("receive", self.current_time, 
                                              recipient_id, message,
                                              {"from": sender_id})
                self.events.append(receive_event)
                self.logger.log(f"Node {recipient_id} received {message.msg_type.value} from {sender_id}")
        
        self.current_time = until_time
    
    def get_events(self):
        """Trả về tất cả events"""
        return [event.to_dict() for event in self.events]
    
    def step(self, duration=0.1):
        """Thực hiện một step simulation"""
        self.process_messages(self.current_time + duration)