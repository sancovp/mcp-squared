"""Phase 2: Workflow Design (design workflows, create agent configs)"""

import logging
import traceback
import re
import os
from ..models.requests import ToolsFileRequest, DesignsFileRequest
from ..utils.helpers import _load_tools_data, _build_error_response
from ..agents.subagents import _design_workflows_with_subagent, _create_agent_configs_with_subagent


async def debug_environment_tool() -> dict:
    """Debug tool to check environment variables in Phase Tools MCP server"""
    import os
    import sys
    return {
        "status": "success",
        "environment": {
            "OPENAI_API_KEY": "SET" if os.getenv('OPENAI_API_KEY') else "NOT SET",
            "SCHEMA_MCP_SERVER_PATH": os.getenv('SCHEMA_MCP_SERVER_PATH', 'NOT SET'),
            "WORK_DIR": os.getenv('WORK_DIR', 'NOT SET'),
            "MCPSQUARED_CONFIG_DIR": os.getenv('MCPSQUARED_CONFIG_DIR', 'NOT SET'),
            "PYTHONPATH": os.getenv('PYTHONPATH', 'NOT SET'),
            "PATH": os.getenv('PATH', 'NOT SET')[:200] + "..." if len(os.getenv('PATH', '')) > 200 else os.getenv('PATH', 'NOT SET'),
            "current_working_directory": os.getcwd(),
            "python_executable": sys.executable,
            "python_path": sys.path[:5],  # First 5 entries
            "python_version": sys.version,
            "process_id": os.getpid(),
            "parent_process_id": os.getppid(),
            "all_env_keys": sorted([k for k in os.environ.keys() if any(word in k.upper() for word in ['MCP', 'SCHEMA', 'WORK', 'API', 'PATH'])])
        }
    }

async def debug_schema_import_test() -> dict:
    """Test if Phase Tools can import schema server files when running nested"""
    import_results = {}
    import sys
    import os
    
    # Test if we can find the schema server directory
    schema_paths_to_test = [
        "/home/GOD/mcpsquared_separated/schema_mcp",
        "/home/GOD/mcpsquared_separated/schema_mcp/schema_tools_mcp_server.py",
        "/home/GOD/mcpsquared_separated/schema_mcp/schema_tools.py"
    ]
    
    for path in schema_paths_to_test:
        if os.path.exists(path):
            import_results[f"path_exists_{path}"] = "SUCCESS"
        else:
            import_results[f"path_exists_{path}"] = "FAILED - PATH NOT FOUND"
    
    # Test if we can import schema_tools when schema_mcp is in sys.path
    try:
        # Add schema_mcp to path temporarily
        schema_dir = "/home/GOD/mcpsquared_separated/schema_mcp"
        if schema_dir not in sys.path:
            sys.path.insert(0, schema_dir)
            
        import schema_tools
        import_results["schema_tools_import"] = "SUCCESS"
        
        # Test specific schema functions
        from schema_tools import create_workflow_config
        import_results["create_workflow_config_import"] = "SUCCESS"
        
    except Exception as e:
        import traceback
        import_results["schema_tools_import"] = f"FAILED: {str(e)}"
        import_results["schema_tools_import_traceback"] = traceback.format_exc()
    
    return {
        "status": "schema_import_test_complete",
        "import_results": import_results,
        "current_directory": os.getcwd(),
        "python_path_first_5": sys.path[:5],
        "schema_mcp_in_path": "/home/GOD/mcpsquared_separated/schema_mcp" in sys.path
    }

logger = logging.getLogger(__name__)


async def phase2_1_call_workflow_designer_subagent_tool(tools_file_path: str, user_requirements: str = "") -> dict:
    """
    Phase 2.1: Subagent analyzes tools and designs workflow types using LLM
    
    Args:
        tools_file_path: Path to tools data from Phase 1.2
        user_requirements: Optional user requirements
        
    Returns:
        Workflow design results
    """
    logger.info(f"Phase 2.1: Designing workflows from tools file: {tools_file_path}")
    
    # DEBUG: Check environment variables
    import os
    logger.info(f"DEBUG - Environment variables:")
    logger.info(f"  OPENAI_API_KEY: {'SET' if os.getenv('OPENAI_API_KEY') else 'NOT SET'}")
    logger.info(f"  SCHEMA_MCP_SERVER_PATH: {os.getenv('SCHEMA_MCP_SERVER_PATH', 'NOT SET')}")
    logger.info(f"  WORK_DIR: {os.getenv('WORK_DIR', 'NOT SET')}")
    logger.info(f"  Current working directory: {os.getcwd()}")
    
    try:
        # Load tools data
        tools_data = _load_tools_data(tools_file_path)
        
        # Use real LLM subagent to design workflows - LLM writes to /tmp/mcpsquared/{mcp_name}_project/
        workflow_designs = await _design_workflows_with_subagent(tools_data, user_requirements)
        
        # Agent writes files directly - extract path from response
        designs_file = _extract_file_path_from_response(workflow_designs, tools_file_path, tools_data)
        
        return {
            "status": "success",
            "phase": "2.1",
            "designs_file_path": designs_file,
            "message": "Workflow designs generated using LLM subagent"
        }
        
    except Exception as e:
        logger.error(f"Phase 2.1 error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return _build_error_response(f"Phase 2.1 failed: {str(e)}", traceback.format_exc())


async def phase2_2_call_agent_designer_subagent_tool(designs_file_path: str) -> dict:
    """
    Phase 2.2: Subagent creates detailed agent configs for each workflow using LLM
    
    Args:
        designs_file_path: Path to workflow designs from Phase 2.1
        
    Returns:
        Agent configuration results
    """
    logger.info(f"Phase 2.2: Creating agent configs from designs: {designs_file_path}")
    
    try:
        # Agent will read the workflow designs file directly via filesystem MCP
        agent_configs = await _create_agent_configs_with_subagent(designs_file_path)
        
        # Agent writes files directly - extract path from response
        configs_dir = _extract_configs_dir_from_response(agent_configs, designs_file_path)
        
        return {
            "status": "success",
            "phase": "2.2",
            "configs_directory": configs_dir,
            "message": "Agent configurations generated using LLM subagent"
        }
        
    except Exception as e:
        logger.error(f"Phase 2.2 error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return _build_error_response(f"Phase 2.2 failed: {str(e)}", traceback.format_exc())


def _extract_file_path_from_response(workflow_designs: str, tools_file_path: str, tools_data: dict) -> str:
    """Extract file path from workflow designs response"""
    path_match = re.search(r"Workflows written to ([^\n]+)", workflow_designs)
    if path_match:
        return path_match.group(1).strip()
    else:
        # Fallback - extract from tools file path
        project_dir = os.path.dirname(tools_file_path)
        return os.path.join(project_dir, f"workflow_designs_{tools_data['mcp_name']}.json")


def _extract_configs_dir_from_response(agent_configs: str, designs_file_path: str) -> str:
    """Extract configs directory from agent configs response"""
    path_match = re.search(r"Agent configs written to ([^\n]+)", agent_configs)
    if path_match:
        return path_match.group(1).strip()
    else:
        # Fallback
        project_dir = os.path.dirname(designs_file_path)
        return os.path.join(project_dir, "agent_configs")