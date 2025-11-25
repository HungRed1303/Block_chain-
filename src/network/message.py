from enum import Enum
import time

class MessageType(Enum):
    """Các loại message"""
    TRANSACTION = "transaction"
    BLOCK_HEADER = "block_header"
    BLOCK_BODY = "block_body"
    PREVOTE = "prevote"
    PRECOMMIT = "precommit"
    REQUEST_BLOCK = "request_block"

class Message:
    """Đại diện cho một message trong network"""
    
    def __init__(self, msg_type, sender_id, data, msg_id=None):
        self.msg_type = msg_type  # MessageType
        self.sender_id = sender_id
        self.data = data
        self.msg_id = msg_id or f"{sender_id}_{time.time()}"
        self.timestamp = time.time()
    
    def __repr__(self):
        return f"Msg({self.msg_type.value}, from={self.sender_id})"

class NetworkEvent:
    """Log một event trong network"""
    
    def __init__(self, event_type, timestamp, node_id, message=None, details=None):
        self.event_type = event_type  # "send", "receive", "drop", "delay"
        self.timestamp = timestamp
        self.node_id = node_id
        self.message = message
        self.details = details or {}
    
    def to_dict(self):
        return {
            "event": self.event_type,
            "time": self.timestamp,
            "node": self.node_id,
            "msg_type": self.message.msg_type.value if self.message else None,
            "msg_id": self.message.msg_id if self.message else None,
            "details": self.details
        }