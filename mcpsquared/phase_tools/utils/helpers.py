"""Helper functions for phase tools"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _validate_mcp_config(config: dict) -> bool:
    """Validate MCP configuration format"""
    required_fields = ["name", "command", "args"]
    return all(field in config for field in required_fields)


def _build_error_response(error_msg: str, traceback_info: str = None) -> dict:
    """Build standardized error response"""
    response = {
        "status": "error",
        "error": error_msg
    }
    if traceback_info:
        response["traceback"] = traceback_info
    return response

def _save_tools_data(mcp_name: str, tools_data: dict) -> str:
    """Save tools data to timestamped project directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = os.getenv("WORK_DIR")
    if not work_dir:
        raise ValueError("WORK_DIR environment variable not set")
    project_dir = os.path.join(work_dir, f"{mcp_name}_project_{timestamp}")
    os.makedirs(project_dir, exist_ok=True)
    file_path = os.path.join(project_dir, f"mcp_tools_{mcp_name}.json")
    
    logger.debug(f"Saving tools data for {mcp_name} to {file_path}")
    with open(file_path, 'w') as f:
        json.dump(tools_data, f, indent=2)
    logger.info(f"Tools data saved to {file_path}")
    
    return file_path


def _load_tools_data(file_path: str) -> dict:
    """Load tools data from file"""
    logger.debug(f"Loading tools data from {file_path}")
    with open(file_path, 'r') as f:
        data = json.load(f)
    logger.info(f"Loaded tools data for {data.get('mcp_name', 'unknown')}")
    return data


def _load_workflow_designs(file_path: str) -> str:
    """Load workflow designs from file"""
    with open(file_path, 'r') as f:
        return f.read()