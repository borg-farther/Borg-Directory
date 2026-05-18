"""Message queue handler."""
import json


class MessageQueue:
    """Handle message queue operations."""

    def __init__(self, queueName, brokerURL):
        self.queueName = queueName
        self.brokerURL = brokerURL

    def publish(self, messageBody):
        """Publish message to queue."""
        return True

    def consume(self):
        """Consume message from queue."""
        return {"body": "sample"}
