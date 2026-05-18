"""Server-Sent Events (SSE) manager for broadcasting updates to connected clients."""
import asyncio
import json
from typing import Set
from app.core.logger import app_logger


class SSEManager:
    """Manages SSE connections and broadcasts messages to all connected clients."""
    
    def __init__(self):
        self.connections: Set[asyncio.Queue] = set()
    
    async def connect(self) -> asyncio.Queue:
        """
        Create a new SSE connection.
        
        Returns:
            Queue for sending messages to this client
        """
        queue = asyncio.Queue()
        self.connections.add(queue)
        app_logger.info(f"New SSE connection established. Total connections: {len(self.connections)}")
        return queue
    
    async def disconnect(self, queue: asyncio.Queue):
        """
        Remove an SSE connection.
        
        Args:
            queue: Queue to remove
        """
        if queue in self.connections:
            self.connections.remove(queue)
            app_logger.info(f"SSE connection closed. Total connections: {len(self.connections)}")
    
    async def broadcast(self, event_type: str, data: dict):
        """
        Broadcast a message to all connected clients.
        
        Args:
            event_type: Type of event (e.g., 'test_cases_updated')
            data: Data to send
        """
        if not self.connections:
            return
        
        message = {
            "type": event_type,
            "data": data
        }
        
        message_json = json.dumps(message)
        dead_connections = set()
        
        for queue in self.connections:
            try:
                await queue.put(message_json)
            except Exception as e:
                app_logger.warning(f"Error sending SSE message: {str(e)}")
                dead_connections.add(queue)
        
        # Remove dead connections
        for queue in dead_connections:
            self.connections.discard(queue)
        
        app_logger.info(f"Broadcasted '{event_type}' to {len(self.connections)} clients")
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)


# Global SSE manager instance
sse_manager = SSEManager()

