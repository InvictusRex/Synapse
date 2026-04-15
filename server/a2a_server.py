"""
A2A HTTP Server
RESTful API for external agent communication
"""
import json
import threading
import time
from typing import Dict, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import uuid


class A2ARequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for A2A server"""
    
    # Class-level reference to server instance
    server_instance = None
    message_handler: Optional[Callable] = None
    
    def log_message(self, format, *args):
        """Suppress default logging"""
        pass
    
    def _send_json_response(self, data: Dict, status: int = 200):
        """Send JSON response"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def _send_error_response(self, message: str, status: int = 400):
        """Send error response"""
        self._send_json_response({"error": message, "success": False}, status)
    
    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/health':
            self._send_json_response({
                "status": "healthy",
                "timestamp": time.time(),
                "server": "synapse-a2a"
            })
        
        elif path == '/status':
            if self.server_instance:
                self._send_json_response(self.server_instance.get_status())
            else:
                self._send_error_response("Server not initialized", 500)
        
        elif path == '/agents':
            if self.server_instance:
                self._send_json_response({
                    "agents": self.server_instance.get_registered_agents()
                })
            else:
                self._send_error_response("Server not initialized", 500)
        
        elif path == '/messages':
            if self.server_instance:
                self._send_json_response({
                    "messages": self.server_instance.get_message_history()
                })
            else:
                self._send_error_response("Server not initialized", 500)
        
        else:
            self._send_error_response("Not found", 404)
    
    def do_POST(self):
        """Handle POST requests"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Read body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error_response("Invalid JSON")
            return
        
        if path == '/message':
            # Send a message to an agent
            required = ['recipient', 'type', 'payload']
            if not all(k in data for k in required):
                self._send_error_response(f"Missing required fields: {required}")
                return
            
            if self.server_instance:
                result = self.server_instance.send_message(
                    sender=data.get('sender', 'external'),
                    recipient=data['recipient'],
                    msg_type=data['type'],
                    payload=data['payload']
                )
                self._send_json_response(result)
            else:
                self._send_error_response("Server not initialized", 500)
        
        elif path == '/task':
            # Submit a task
            if 'task' not in data:
                self._send_error_response("Missing 'task' field")
                return
            
            if self.message_handler:
                try:
                    result = self.message_handler(data['task'])
                    self._send_json_response({"success": True, "result": result})
                except Exception as e:
                    self._send_error_response(str(e), 500)
            else:
                self._send_error_response("No task handler configured", 500)
        
        elif path == '/register':
            # Register an external agent
            if 'agent_id' not in data:
                self._send_error_response("Missing 'agent_id'")
                return
            
            if self.server_instance:
                self.server_instance.register_external_agent(
                    data['agent_id'],
                    data.get('capabilities', [])
                )
                self._send_json_response({"success": True, "agent_id": data['agent_id']})
            else:
                self._send_error_response("Server not initialized", 500)
        
        else:
            self._send_error_response("Not found", 404)


class A2AServer:
    """
    A2A HTTP Server
    
    Provides REST API for external systems to:
    - Send messages to agents
    - Submit tasks
    - Query system status
    - Register external agents
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._external_agents: Dict[str, Dict] = {}
        self._message_history: list = []
        self._task_handler: Optional[Callable] = None
        
        # Link handler to class
        A2ARequestHandler.server_instance = self
    
    def set_task_handler(self, handler: Callable):
        """Set handler for incoming tasks"""
        self._task_handler = handler
        A2ARequestHandler.message_handler = handler
    
    def start(self) -> bool:
        """Start the server"""
        if self._running:
            return True
        
        try:
            self._server = HTTPServer((self.host, self.port), A2ARequestHandler)
            self._server.timeout = 0.5  # Short timeout for checking _running flag
            self._running = True
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            return True
        except Exception as e:
            print(f"[A2A Server] Failed to start: {e}")
            return False
    
    def _run(self):
        """Server loop"""
        while self._running:
            try:
                self._server.handle_request()
            except:
                break
    
    def stop(self):
        """Stop the server"""
        self._running = False
        
        # Give the server loop a moment to exit
        time.sleep(0.1)
        
        if self._server:
            try:
                self._server.server_close()
            except:
                pass
            self._server = None
        
        self._thread = None
    
    def is_running(self) -> bool:
        """Check if server is running"""
        return self._running
    
    def register_external_agent(self, agent_id: str, capabilities: list = None):
        """Register an external agent"""
        self._external_agents[agent_id] = {
            "id": agent_id,
            "capabilities": capabilities or [],
            "registered_at": time.time()
        }
    
    def unregister_external_agent(self, agent_id: str):
        """Unregister an external agent"""
        if agent_id in self._external_agents:
            del self._external_agents[agent_id]
    
    def send_message(self, sender: str, recipient: str, msg_type: str, 
                    payload: Dict) -> Dict[str, Any]:
        """Send a message through the bus"""
        from core.a2a_bus import get_bus, Message, MessageType
        
        try:
            bus = get_bus()
            
            # Map string type to MessageType
            type_map = {
                "task_request": MessageType.TASK_REQUEST,
                "task_result": MessageType.TASK_RESULT,
                "query": MessageType.QUERY,
                "response": MessageType.RESPONSE,
                "broadcast": MessageType.BROADCAST
            }
            
            msg_type_enum = type_map.get(msg_type, MessageType.TASK_REQUEST)
            
            msg = Message.create(
                sender=sender,
                recipient=recipient,
                msg_type=msg_type_enum,
                payload=payload
            )
            
            success = bus.send(msg)
            
            self._message_history.append({
                "id": msg.id,
                "sender": sender,
                "recipient": recipient,
                "type": msg_type,
                "timestamp": time.time(),
                "success": success
            })
            
            # Keep history limited
            if len(self._message_history) > 100:
                self._message_history = self._message_history[-50:]
            
            return {"success": success, "message_id": msg.id}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_registered_agents(self) -> list:
        """Get list of registered external agents"""
        return list(self._external_agents.values())
    
    def get_message_history(self) -> list:
        """Get recent message history"""
        return self._message_history[-50:]
    
    def get_status(self) -> Dict[str, Any]:
        """Get server status"""
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "url": f"http://{self.host}:{self.port}",
            "external_agents": len(self._external_agents),
            "messages_handled": len(self._message_history)
        }


# Global server instance
_server: Optional[A2AServer] = None

def get_a2a_server(host: str = None, port: int = None) -> A2AServer:
    """Get or create A2A server"""
    global _server
    if _server is None:
        from config import A2A_SERVER_HOST, A2A_SERVER_PORT
        _server = A2AServer(
            host=host or A2A_SERVER_HOST,
            port=port or A2A_SERVER_PORT
        )
    return _server

def start_a2a_server() -> bool:
    """Start the A2A server"""
    server = get_a2a_server()
    return server.start()

def stop_a2a_server():
    """Stop the A2A server"""
    global _server
    if _server:
        _server.stop()
