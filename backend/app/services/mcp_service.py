"""
MCP (Model Context Protocol) Service
Manages MCP server connections and tool execution for Private AI
"""
import asyncio
import json
import subprocess
from typing import Dict, List, Optional, Any
from pathlib import Path
import httpx
from app.core.config import settings


class MCPTool:
    """Represents an MCP tool/function"""
    def __init__(self, name: str, description: str, parameters: dict):
        self.name = name
        self.description = description
        self.parameters = parameters
    
    def to_openai_format(self) -> dict:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class MCPServer:
    """Represents an MCP server connection"""
    def __init__(self, name: str, config: dict):
        self.name = name
        self.config = config
        self.type = config.get("type", "stdio")  # stdio or streamable
        self.process = None
        self.tools: List[MCPTool] = []
        self.client = None
    
    async def start(self):
        """Start the MCP server process"""
        if self.type == "stdio":
            # Start subprocess for stdio-based MCP servers
            command = self.config.get("command")
            args = self.config.get("args", [])
            env = self.config.get("env", {})
            
            if not command:
                raise ValueError(f"MCP server {self.name} missing 'command'")
            
            # Merge environment variables
            import os
            full_env = os.environ.copy()
            full_env.update(env)
            
            # Start the process
            self.process = await asyncio.create_subprocess_exec(
                command,
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=full_env
            )
            
            # Give the process time to start (especially for npx downloads)
            await asyncio.sleep(2.0)
            
            # Check if process is still alive
            if self.process.returncode is not None:
                stderr = await self.process.stderr.read()
                raise RuntimeError(f"MCP server {self.name} died immediately: {stderr.decode()}")
            
            # Initialize MCP protocol handshake
            await self._initialize_stdio()
        
        elif self.type == "streamable":
            # HTTP-based MCP server
            url = self.config.get("url")
            if not url:
                raise ValueError(f"MCP server {self.name} missing 'url'")
            
            self.client = httpx.AsyncClient(timeout=30.0)
            await self._initialize_http(url)
    
    async def _initialize_stdio(self):
        """Initialize stdio-based MCP server"""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "PrivateAI",
                    "version": "1.0.0"
                }
            }
        }
        
        await self._send_stdio_message(init_request)
        response = await self._read_stdio_message()
        
        # List available tools
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        await self._send_stdio_message(list_tools_request)
        tools_response = await self._read_stdio_message()
        
        if tools_response and "result" in tools_response:
            for tool_data in tools_response["result"].get("tools", []):
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("inputSchema", {})
                )
                self.tools.append(tool)
    
    async def _initialize_http(self, url: str):
        """Initialize HTTP-based MCP server"""
        try:
            response = await self.client.post(
                url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }
            )
            data = response.json()
            
            if "result" in data:
                for tool_data in data["result"].get("tools", []):
                    tool = MCPTool(
                        name=tool_data["name"],
                        description=tool_data.get("description", ""),
                        parameters=tool_data.get("inputSchema", {})
                    )
                    self.tools.append(tool)
        except Exception as e:
            print(f"Failed to initialize HTTP MCP server {self.name}: {e}")
    
    async def _send_stdio_message(self, message: dict):
        """Send JSON-RPC message to stdio process"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("MCP server process not running")
        
        try:
            json_str = json.dumps(message) + "\n"
            self.process.stdin.write(json_str.encode())
            await self.process.stdin.drain()
        except Exception as e:
            print(f"Error sending message to MCP server {self.name}: {e}")
            raise
    
    async def _read_stdio_message(self) -> Optional[dict]:
        """Read JSON-RPC message from stdio process"""
        if not self.process or not self.process.stdout:
            raise RuntimeError("MCP server process not running")
        
        try:
            line = await asyncio.wait_for(
                self.process.stdout.readline(),
                timeout=30.0  # Increased timeout for slow package downloads
            )
            if line:
                decoded = line.decode().strip()
                if decoded:
                    return json.loads(decoded)
        except asyncio.TimeoutError:
            print(f"Timeout reading from MCP server {self.name}")
            # Check if process is still alive
            if self.process.returncode is not None:
                stderr = await self.process.stderr.read()
                print(f"MCP server {self.name} stderr: {stderr.decode()}")
        except json.JSONDecodeError as e:
            print(f"Invalid JSON from MCP server {self.name}: {e}")
            print(f"Received line: {line.decode()}")
        
        return None
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute an MCP tool"""
        if self.type == "stdio":
            return await self._call_tool_stdio(tool_name, arguments)
        elif self.type == "streamable":
            return await self._call_tool_http(tool_name, arguments)
    
    async def _call_tool_stdio(self, tool_name: str, arguments: dict) -> Any:
        """Call tool via stdio"""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        await self._send_stdio_message(request)
        response = await self._read_stdio_message()
        
        if response and "result" in response:
            return response["result"]
        elif response and "error" in response:
            raise RuntimeError(f"MCP tool error: {response['error']}")
        
        return None
    
    async def _call_tool_http(self, tool_name: str, arguments: dict) -> Any:
        """Call tool via HTTP"""
        if not self.client:
            raise RuntimeError("HTTP client not initialized")
        
        url = self.config.get("url")
        response = await self.client.post(
            url,
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }
        )
        
        data = response.json()
        if "result" in data:
            return data["result"]
        elif "error" in data:
            raise RuntimeError(f"MCP tool error: {data['error']}")
        
        return None
    
    async def stop(self):
        """Stop the MCP server"""
        if self.process:
            self.process.terminate()
            await self.process.wait()
        
        if self.client:
            await self.client.aclose()


class MCPService:
    """Manages MCP servers and tool execution"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        # Use local path in development, /data in production
        if settings.STORAGE_PATH == "/data" and not Path("/data").exists():
            # Development mode - use local directory
            self.config_path = Path(__file__).parent / "mcp_servers.json"
        else:
            self.config_path = Path(settings.STORAGE_PATH) / "mcp_servers.json"
        self.initialized = False
    
    async def initialize(self):
        """Initialize MCP service and load configuration"""
        if self.initialized:
            return
        
        await self.load_config()
        self.initialized = True
    
    async def load_config(self):
        """Load MCP server configuration"""
        if not self.config_path.exists():
            # Create default config from mcp_config.json
            default_config_path = Path(__file__).parent / "mcp_config.json"
            if default_config_path.exists():
                with open(default_config_path) as f:
                    default_config = json.load(f)
            else:
                default_config = {"mcpServers": {}}
            
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=2)
        
        with open(self.config_path) as f:
            config = json.load(f)
        
        # Substitute environment variables
        config = self._substitute_env_vars(config)
        
        # Initialize servers
        for name, server_config in config.get("mcpServers", {}).items():
            await self.register_server(name, server_config)
    
    def _substitute_env_vars(self, config: dict) -> dict:
        """Substitute ${VAR} with environment variable values"""
        import os
        import re
        
        def substitute(obj):
            if isinstance(obj, dict):
                return {k: substitute(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [substitute(item) for item in obj]
            elif isinstance(obj, str):
                # Replace ${VAR} with os.environ.get('VAR', '')
                pattern = r'\$\{([^}]+)\}'
                return re.sub(pattern, lambda m: os.environ.get(m.group(1), ''), obj)
            return obj
        
        return substitute(config)
    
    async def register_server(self, name: str, config: dict):
        """Register and start an MCP server"""
        server = MCPServer(name, config)
        try:
            await server.start()
            self.servers[name] = server
            print(f"MCP server '{name}' started with {len(server.tools)} tools")
        except Exception as e:
            print(f"Failed to start MCP server '{name}': {e}")
    
    async def get_available_tools(self) -> List[dict]:
        """Get all available tools in OpenAI format (async for consistency)"""
        return self.get_all_tools()
    
    def get_all_tools(self) -> List[dict]:
        """Get all available tools in OpenAI format"""
        tools = []
        for server in self.servers.values():
            for tool in server.tools:
                tools.append(tool.to_openai_format())
        return tools
    
    async def call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Execute a tool by name"""
        # Find which server has this tool
        for server in self.servers.values():
            for tool in server.tools:
                if tool.name == tool_name:
                    return await server.call_tool(tool_name, arguments)
        
        raise ValueError(f"Tool '{tool_name}' not found in any MCP server")
    
    async def shutdown(self):
        """Shutdown all MCP servers"""
        for server in self.servers.values():
            await server.stop()
        self.servers.clear()


# Global MCP service instance
mcp_service = MCPService()
