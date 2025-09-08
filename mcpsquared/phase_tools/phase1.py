"""Phase 1: MCP Analysis (install, discover tools)"""

import logging
import traceback
from typing import List
from mcp_use import MCPClient
from ..models.requests import MCPConfig
from ..utils.helpers import _validate_mcp_config, _build_error_response, _save_tools_data

logger = logging.getLogger(__name__)


async def _validate_config_and_test_connection(mcp_config: MCPConfig) -> tuple[bool, str]:
    """Validate MCP config and test connection"""
    config_dict = mcp_config.model_dump()
    if not _validate_mcp_config(config_dict):
        return False, "Invalid MCP configuration format"
    
    # Create MCPClient from user's config for testing
    client_config = {"mcpServers": {mcp_config.name: config_dict}}
    
    # CONNECT and CHECK IF CAN GET TOOLS
    logger.debug(f"Testing connection to MCP: {mcp_config.name}")
    client = MCPClient.from_dict(client_config)
    
    try:
        session = await client.create_session(mcp_config.name)
        
        # Check if we can get tools using correct method
        available_tools = await session.list_tools()
        logger.debug(f"Successfully connected and found {len(available_tools)} tools")
        return True, "connection_tested: True, connection_resources: tool"
            
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False, f"Connection failed: {str(e)}"
    finally:
        await client.close_all_sessions()


def _build_success_response(mcp_name: str) -> dict:
    """Build success response for phase 1.1"""
    return {
        "status": "success",
        "phase": "1.1",
        "mcp_name": mcp_name,
        "connection_tested": True,
        "message": f"Successfully validated configuration for {mcp_name} MCP",
        "config_validated": True
    }


async def phase1_1_install_mcp_tool(name: str, command: str, args: List[str]) -> dict:
    """
    Phase 1.1: Install user's MCP locally and test connection
    
    Args:
        name: MCP server name
        command: Command to run MCP server
        args: Command arguments
        
    Returns:
        Installation and connection test results
    """
    # Reconstruct MCPConfig from flat parameters
    mcp_config = MCPConfig(name=name, command=command, args=args)
    
    logger.info(f"Phase 1.1: Installing MCP {mcp_config.name}")
    
    try:
        is_valid, message = await _validate_config_and_test_connection(mcp_config)
        if not is_valid:
            return _build_error_response(message)
        
        # Save MCP config for Phase 2.2 to use
        _save_mcp_config(mcp_config)
        
        return _build_success_response(mcp_config.name)
        
    except Exception as e:
        logger.error(f"Phase 1.1 error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return _build_error_response(f"Phase 1.1 failed: {str(e)}", traceback.format_exc())


async def phase1_2_list_mcp_tools_tool(name: str, command: str, args: List[str]) -> dict:
    """
    Phase 1.2: Connect to the REAL MCP and discover actual tools
    
    Args:
        name: MCP server name
        command: Command to run MCP server
        args: Command arguments
        
    Returns:
        Tool discovery results with schemas
    """
    # Reconstruct MCPConfig from flat parameters
    mcp_config = MCPConfig(name=name, command=command, args=args)
    
    logger.info(f"Phase 1.2: Connecting to REAL MCP {mcp_config.name} to discover tools")
    
    try:
        # Connect to the ACTUAL MCP and get REAL tools
        tools_data = await _discover_real_mcp_tools(mcp_config)
        
        # Save tools data to file for next phase
        tools_file = _save_tools_data(mcp_config.name, tools_data)
        
        return {
            "status": "success",
            "phase": "1.2", 
            "mcp_name": mcp_config.name,
            "tools_count": len(tools_data["tools"]),
            "tools": tools_data["tools"][:5],  # First 5 for display
            "schemas": tools_data["schemas"][:3] if tools_data.get("schemas") else [],
            "tools_file_path": tools_file,
            "message": f"Discovered {len(tools_data['tools'])} REAL tools from {mcp_config.name}"
        }
        
    except Exception as e:
        logger.error(f"Phase 1.2 error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return _build_error_response(f"Phase 1.2 failed: {str(e)}", traceback.format_exc())


async def _discover_real_mcp_tools(mcp_config: MCPConfig) -> dict:
    """Connect to REAL MCP and discover ACTUAL tools"""
    logger.info(f"Connecting to REAL MCP {mcp_config.name} to discover tools")
    
    # Create MCPClient with the user's MCP config
    client_config = {
        "mcpServers": {
            mcp_config.name: mcp_config.model_dump()
        }
    }
    
    client = MCPClient.from_dict(client_config)
    
    try:
        # Create session and get REAL tools
        session = await client.create_session(mcp_config.name)
        
        tools = []
        schemas = []
        
        # Use session.list_tools() method to get actual tools
        available_tools = await session.list_tools()
        for tool in available_tools:
            # Use prefixed naming convention: mcp__{{name}}__{{tool}}
            prefixed_name = f"mcp__{mcp_config.name}__{tool.name}"
            tools.append(prefixed_name)
            schemas.append({
                "name": prefixed_name,
                "description": tool.description if hasattr(tool, 'description') else "",
                "parameters": tool.inputSchema if hasattr(tool, 'inputSchema') else {}
            })
        
        logger.info(f"Discovered {len(tools)} REAL tools from {mcp_config.name}")
        
        return {
            "mcp_name": mcp_config.name,
            "tools": tools,
            "schemas": schemas
        }
        
    finally:
        await client.close_all_sessions()


def _save_mcp_config(mcp_config: MCPConfig) -> None:
    """Save MCP config to registry for Phase 2.2 to use"""
    import json
    import os
    from pathlib import Path
    
    # Create mcp_configs directory
    work_dir = os.getenv("WORK_DIR")
    if not work_dir:
        raise ValueError("WORK_DIR environment variable not set")
    mcp_configs_dir = Path(f"{work_dir}/mcp_configs")
    mcp_configs_dir.mkdir(parents=True, exist_ok=True)
    
    # Save MCP config
    config_file = mcp_configs_dir / f"{mcp_config.name}_config.json"
    with open(config_file, 'w') as f:
        json.dump(mcp_config.model_dump(), f, indent=2)
    
    logger.info(f"Saved MCP config to: {config_file}")