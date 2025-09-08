"""
MCPSquared Main FastMCP Server

Provides the 5 core tools for MCPSquared workflow generation:
1. generate_flows_for_mcp - Main workflow generator
2. get_flows - List generated workflows  
3. get_flow_domains - List workflow domains
4. sub_chat - Chat interface for planning
5. package_workflow_mcp - Custom packaging
"""

from fastmcp import FastMCP
from typing import Dict, Any, List, Optional
import asyncio
import logging
import traceback
import sys
import os
from pathlib import Path

# Import debug system from mcpsquared_base
from mcpsquared_base.utils.debug import mcp_debug_log, setup_debug_interception

from mcpsquared.simple_orchestrator import SimpleOrchestrator

# Setup logging - do not call basicConfig in library code
logger = logging.getLogger(__name__)

# Debug configuration - read from environment on startup
_DEBUG_LOG_PATH = None
_DEBUG_NICKNAME = None

def _debug_log(message: str):
    """Helper to log debug message with configured path and nickname"""
    mcp_debug_log(message, _DEBUG_LOG_PATH, _DEBUG_NICKNAME)

# Create FastMCP app
app = FastMCP("MCPSquared Workflow Generator")

# Create orchestrator instance
orchestrator = SimpleOrchestrator()


@app.tool()
async def generate_flows_for_mcp(mcp_config: dict) -> str:
    """
    Main generator that analyzes an MCP and creates complete workflow package
    
    Args:
        mcp_config: MCP server configuration dict with name, command, args, transport
        
    Returns:
        JSON string with generation results including package path and installation instructions
    """
    logger.info(f"Generating workflows for MCP: {mcp_config.get('name', 'unknown')}")
    
    try:
        result = await orchestrator.generate_workflows(mcp_config)
        logger.info("Workflow generation completed successfully")
        
        # Convert result dict to JSON string and add handoff message
        import json
        result_json = json.dumps(result, indent=2)
        handoff_message = "\n\nEverything is ready for you and the user to now add more. Help them out with your own filesystem tools and whatever testing they have available (if they have given you bash or other tools to do some kind of code execution). The generated code from MCPSquared is easy to understand and extend. You can help the user add anything else they want!"
        
        return result_json + handoff_message
    except Exception as e:
        logger.error(f"Workflow generation failed: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return f'{{"success": false, "error": "Workflow generation failed: {str(e)}", "traceback": "{traceback.format_exc()}"}}'


@app.tool()
def get_flows(domain: str = None) -> str:
    """
    List available generated workflows, optionally filtered by domain
    
    Args:
        domain: Optional domain filter (e.g., "web", "files", "database")
        
    Returns:
        JSON string with list of available workflows
    """
    logger.info(f"Listing workflows for domain: {domain or 'all'}")
    return orchestrator.get_flows(domain)


@app.tool() 
def get_flow_domains() -> str:
    """
    List all available workflow domains/categories
    
    Returns:
        JSON string with available domains and their descriptions
    """
    logger.info("Listing workflow domains")
    return orchestrator.get_flow_domains()


@app.tool()
def sub_chat(message: str, history_id: str) -> str:
    """
    Chat interface for workflow planning and assistance
    
    Args:
        message: User message about workflow needs
        history_id: Session identifier for conversation continuity
        
    Returns:
        JSON string with chat response and recommendations
    """
    logger.info(f"Processing chat message for session: {history_id}")
    return orchestrator.sub_chat(message, history_id)


@app.tool()
def package_workflow_mcp(workflows: list, base_mcp: str) -> str:
    """
    Package specific workflows into installable MCP (advanced composition)
    
    Args:
        workflows: List of workflow names to include
        base_mcp: Base MCP name to build from
        
    Returns:
        JSON string with packaging results
    """
    logger.info(f"Packaging workflows {workflows} for base MCP: {base_mcp}")
    return orchestrator.package_workflow_mcp(workflows, base_mcp)


@app.tool()
def get_processed_mcps_list() -> str:
    """
    Get list of all MCPs that have been processed by MCPSquared
    
    Returns:
        JSON string with list of MCP names and basic stats about packages and workflows
    """
    logger.info("Getting processed MCPs list via orchestrator")
    return orchestrator.get_processed_mcps_list()


@app.tool()
def search_my_workflows(
    mcp_name: Optional[str] = None,
    domain: Optional[str] = None,
    workflow_name_pattern: Optional[str] = None
) -> str:
    """
    Search workflows across all processed MCPs with filtering options
    
    Args:
        mcp_name: Filter by specific MCP name (e.g., "carton")
        domain: Filter by workflow domain (e.g., "knowledge_management")
        workflow_name_pattern: Search for workflows containing this text
    
    Returns:
        JSON string with search results and metadata
    """
    logger.info(f"Searching workflows via orchestrator: mcp={mcp_name}, domain={domain}, pattern={workflow_name_pattern}")
    return orchestrator.search_my_workflows(mcp_name, domain, workflow_name_pattern)


@app.tool()
def execute_any_workflow(
    workflow_name: str,
    workflow_args: Dict[str, Any],
    package_name: Optional[str] = None
) -> str:
    """
    Execute any workflow from the registry by name
    
    Args:
        workflow_name: Name of the workflow to execute (e.g., "add_concept_workflow")
        workflow_args: Arguments to pass to the workflow (as dict)
        package_name: Optional package name to narrow search if workflow name appears in multiple packages
    
    Returns:
        JSON string with execution results
    """
    logger.info(f"Executing workflow via orchestrator: {workflow_name} from package: {package_name or 'any'}")
    return orchestrator.execute_any_workflow(workflow_name, workflow_args, package_name)


@app.tool()
async def debug_environment_mcpsquared_main() -> dict:
    """Debug tool to check environment variables in MCPSquared main MCP server"""
    import os
    import sys
    return {
        "status": "success",
        "environment": {
            "OPENAI_API_KEY": "SET" if os.getenv('OPENAI_API_KEY') else "NOT SET",
            "SCHEMA_MCP_SERVER_PATH": os.getenv('SCHEMA_MCP_SERVER_PATH', 'NOT SET'),
            "WORK_DIR": os.getenv('WORK_DIR', 'NOT SET'),
            "MCPSQUARED_CONFIG_DIR": os.getenv('MCPSQUARED_CONFIG_DIR', 'NOT SET'),
            "PHASE_TOOLS_MCP_SERVER_PATH": os.getenv('PHASE_TOOLS_MCP_SERVER_PATH', 'NOT SET'),
            "PYTHONPATH": os.getenv('PYTHONPATH', 'NOT SET'),
            "PATH": os.getenv('PATH', 'NOT SET')[:200] + "..." if len(os.getenv('PATH', '')) > 200 else os.getenv('PATH', 'NOT SET'),
            "current_working_directory": os.getcwd(),
            "python_executable": sys.executable,
            "python_path": sys.path[:5],  # First 5 entries
            "python_version": sys.version,
            "process_id": os.getpid(),
            "parent_process_id": os.getppid(),
            "all_env_keys": sorted([k for k in os.environ.keys() if any(word in k.upper() for word in ['MCP', 'SCHEMA', 'WORK', 'API', 'PATH', 'PHASE'])])
        }
    }


def main():
    """Main entry point for console script"""
    # Read debug environment variables for this MCP
    global _DEBUG_LOG_PATH, _DEBUG_NICKNAME
    _DEBUG_LOG_PATH = os.getenv("MAIN_DEBUG_PATH")
    _DEBUG_NICKNAME = os.getenv("MAIN_DEBUG_NICKNAME")
    
    # Set up debug interception if configured
    if _DEBUG_LOG_PATH and _DEBUG_NICKNAME:
        setup_debug_interception(_DEBUG_LOG_PATH, _DEBUG_NICKNAME)
        _debug_log("main: Debug interception set up for main server")
    
    logger.info("Starting MCPSquared FastMCP Server")
    _debug_log("main: Starting MCPSquared FastMCP Server - mcpsquared_main_server")
    app.run()


if __name__ == "__main__":
    main()