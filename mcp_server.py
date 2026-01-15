#!/usr/bin/env python3
"""
MCP Server for DonPAPI
Automated secrets dump remotely on multiple Windows computers.
"""

import asyncio
import json
import os
import subprocess
import sys
import signal
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Initialize MCP server
server = Server("donpapi-mcp")

# Configuration
OUTPUT_DIR = os.environ.get("DONPAPI_OUTPUT", "/root/.donpapi/loot")
GUI_PORT = int(os.environ.get("DONPAPI_GUI_PORT", "8088"))

# Global process for GUI
gui_process = None

def run_donpapi_command(args: List[str], timeout: int = 600) -> Dict[str, Any]:
    """Execute DonPAPI CLI command"""
    try:
        cmd = ["donpapi"] + args
        
        # Run command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": " ".join(cmd)
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@server.list_tools()
async def list_tools() -> List[Tool]:
    return [
        Tool(
            name="donpapi_collect",
            description="Collect secrets from remote targets",
            inputSchema={
                "type": "object",
                "properties": {
                    "targets": {
                        "type": "string",
                        "description": "Target IP(s), range(s), hostname(s), or 'ALL' for domain scan. Space separated."
                    },
                    "domain": {"type": "string", "description": "Target Domain"},
                    "username": {"type": "string", "description": "Username for authentication"},
                    "password": {"type": "string", "description": "Password for authentication"},
                    "hashes": {"type": "string", "description": "NTLM hashes (LMHASH:NTHASH)"},
                    "use_kerberos": {"type": "boolean", "description": "Use Kerberos authentication (-k)"},
                    "collectors": {
                        "type": "string",
                        "description": "Specific collectors (e.g. 'Chromium,Firefox'). Default: All"
                    },
                    "threads": {"type": "integer", "default": 50}
                },
                "required": ["targets", "username"]
            }
        ),
        Tool(
            name="donpapi_start_gui",
            description="Start DonPAPI Web GUI to browse collected secrets",
            inputSchema={
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "default": 8088},
                    "bind": {"type": "string", "default": "0.0.0.0"}
                }
            }
        ),
        Tool(
            name="donpapi_stop_gui",
            description="Stop DonPAPI Web GUI",
            inputSchema={"type": "object", "properties": {}}
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    global gui_process
    
    if name == "donpapi_collect":
        args = ["collect"]
        
        # Auth
        if "username" in arguments:
            args.extend(["-u", arguments["username"]])
        if "password" in arguments:
            args.extend(["-p", arguments["password"]])
        if "domain" in arguments:
            args.extend(["-d", arguments["domain"]])
        if "hashes" in arguments:
            args.extend(["-H", arguments["hashes"]])
        if arguments.get("use_kerberos"):
            args.append("-k")
            
        # Targets
        if "targets" in arguments:
            args.extend(["-t"] + arguments["targets"].split())
            
        # Options
        if "collectors" in arguments:
            args.extend(["-c", arguments["collectors"]])
        if "threads" in arguments:
            args.extend(["--threads", str(arguments["threads"])])
            
        result = run_donpapi_command(args)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
    elif name == "donpapi_start_gui":
        if gui_process and gui_process.poll() is None:
            return [TextContent(type="text", text="GUI is already running.")]
            
        port = arguments.get("port", GUI_PORT)
        bind = arguments.get("bind", "0.0.0.0")
        
        cmd = ["donpapi", "gui", "--bind", bind, "--port", str(port)]
        
        try:
            gui_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return [TextContent(type="text", text=f"DonPAPI GUI started on http://{bind}:{port}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Failed to start GUI: {str(e)}")]
            
    elif name == "donpapi_stop_gui":
        if gui_process:
            gui_process.terminate()
            gui_process = None
            return [TextContent(type="text", text="DonPAPI GUI stopped.")]
        else:
            return [TextContent(type="text", text="GUI is not running.")]
            
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
