import logging
import json
from datetime import datetime

class Logger:
    """Logging utility cho toàn bộ system"""
    
    def __init__(self, name, log_file=None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def log(self, message, level="info"):
        """Log message"""
        if level == "debug":
            self.logger.debug(message)
        elif level == "info":
            self.logger.info(message)
        elif level == "warning":
            self.logger.warning(message)
        elif level == "error":
            self.logger.error(message)

class DeterministicLogger:
    """Logger đảm bảo deterministic output"""
    
    def __init__(self, filename):
        self.filename = filename
        self.events = []
    
    def log_event(self, event_type, data):
        """Log một event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        self.events.append(event)
    
    def save(self):
        """Save logs to file"""
        with open(self.filename, 'w') as f:
            json.dump(self.events, f, indent=2, sort_keys=True)
    
    def load(self):
        """Load logs from file"""
        with open(self.filename, 'r') as f:
            self.events = json.load(f)
    
    def get_hash(self):
        """Get hash của toàn bộ logs"""
        import hashlib
        content = json.dumps(self.events, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()