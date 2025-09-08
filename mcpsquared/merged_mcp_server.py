"""
Ultra-Minimal MCPSquared Server
Single MCP with all phase + schema tools merged
"""

import os
import sys
import json
import logging
import traceback
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from fastmcp import FastMCP
from pydantic import BaseModel
from mcp_use import MCPClient

# TEMPORARY: sys.path hack until mcpsquared-base is properly installed
# TODO: Remove this hack and use normal imports: from mcpsquared_base.models.schemas import ...
# Requires: pip install /tmp/mcpsquared-base
sys.path.insert(0, '/tmp/mcpsquared-base')
from mcpsquared_base.models.schemas import (
    TemplatedArg, WorkflowConfig, AgentConfig, MCPServerConfig, MCPClientConfig, InputArgs, InputArg
)
from mcpsquared_base.utils.workflow_runner import run_workflow
from mcpsquared_base.utils.debug import agent_debug_log, mcp_debug_log

logger = logging.getLogger(__name__)

# ============= SIMPLE REQUEST MODELS =============

# MCPConfig removed - using MCPServerConfig from _base instead

# ============= PHASE 1 TOOLS (MCP Analysis) =============

async def phase1_1_install_mcp_tool(name: str, command: str, args: List[str]) -> dict:
    """
    Phase 1.1: Test connection to user's MCP
    """
    logger.info(f"Phase 1.1: Testing connection to {name}")
    mcp_debug_log(f"phase1_1_install_mcp_tool: Testing connection to {name}")
    
    mcp_config = MCPServerConfig(name=name, command=command, args=args)
    mcp_debug_log(f"Created MCPServerConfig: {mcp_config.model_dump()}")
    
    # Test connection
    client_config = {"mcpServers": {name: mcp_config.model_dump()}}
    client = MCPClient.from_dict(client_config)
    
    try:
        mcp_debug_log(f"Creating session for {name}")
        session = await client.create_session(name)
        mcp_debug_log(f"Session created successfully, listing tools")
        tools = await session.list_tools()
        logger.info(f"Successfully connected to {name}, found {len(tools)} tools")
        mcp_debug_log(f"Found {len(tools)} tools: {[tool.name for tool in tools]}")
        
        # Save config for later use
        work_dir = os.getenv("WORK_DIR", "/tmp/mcpsquared")
        mcp_configs_dir = Path(work_dir) / "mcp_configs"
        mcp_configs_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = mcp_configs_dir / f"{name}_config.json"
        with open(config_file, 'w') as f:
            json.dump(mcp_config.model_dump(), f, indent=2)
        
        return {
            "status": "success",
            "phase": "1.1",
            "mcp_name": name,
            "connection_tested": True,
            "tools_found": len(tools)
        }
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
    finally:
        await client.close_all_sessions()

async def phase1_2_list_mcp_tools_tool(name: str, command: str, args: List[str]) -> dict:
    """
    Phase 1.2: Discover all tools from MCP
    """
    logger.info(f"Phase 1.2: Discovering tools from {name}")
    
    mcp_config = MCPServerConfig(name=name, command=command, args=args)
    client_config = {"mcpServers": {name: mcp_config.model_dump()}}
    client = MCPClient.from_dict(client_config)
    
    try:
        session = await client.create_session(name)
        available_tools = await session.list_tools()
        
        tools = []
        schemas = []
        
        for tool in available_tools:
            # Use MCP prefixed naming
            prefixed_name = f"mcp__{name}__{tool.name}"
            tools.append(prefixed_name)
            schemas.append({
                "name": prefixed_name,
                "description": getattr(tool, 'description', ''),
                "parameters": getattr(tool, 'inputSchema', {})
            })
        
        # Save tools data
        work_dir = os.getenv("WORK_DIR", "/tmp/mcpsquared")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_dir = Path(work_dir) / f"{name}_project_{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)
        
        tools_file = project_dir / f"mcp_tools_{name}.json"
        tools_data = {
            "mcp_name": name,
            "tools": tools,
            "schemas": schemas
        }
        
        with open(tools_file, 'w') as f:
            json.dump(tools_data, f, indent=2)
        
        logger.info(f"Discovered {len(tools)} tools from {name}")
        
        return {
            "status": "success",
            "phase": "1.2",
            "mcp_name": name,
            "tools_count": len(tools),
            "tools": tools[:5],  # First 5 for display
            "tools_file_path": str(tools_file)
        }
        
    except Exception as e:
        logger.error(f"Tool discovery failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}
    finally:
        await client.close_all_sessions()

# ============= PHASE 2 TOOLS (Workflow Generation) =============

def phase2_1_create_workflow_configs(
    tools_file_path: str,
    user_requirements: str = "Create comprehensive workflows for all tools"
) -> dict:
    """
    Phase 2.1: Generate workflow configurations from tools
    NO SUBAGENTS - just direct config generation
    """
    logger.info(f"Phase 2.1: Creating workflow configs from {tools_file_path}")
    
    try:
        # Load tools data
        with open(tools_file_path, 'r') as f:
            tools_data = json.load(f)
        
        mcp_name = tools_data['mcp_name']
        tools = tools_data['tools']
        
        # Generate workflows based on tool patterns
        workflows = []
        
        # Group tools by operation type
        tool_groups = {
            'create': [],
            'read': [],
            'update': [],
            'delete': [],
            'query': [],
            'other': []
        }
        
        for tool in tools:
            tool_name = tool.split('__')[-1] if '__' in tool else tool
            
            if any(op in tool_name.lower() for op in ['create', 'add', 'new']):
                tool_groups['create'].append(tool)
            elif any(op in tool_name.lower() for op in ['read', 'get', 'list', 'fetch']):
                tool_groups['read'].append(tool)
            elif any(op in tool_name.lower() for op in ['update', 'edit', 'modify']):
                tool_groups['update'].append(tool)
            elif any(op in tool_name.lower() for op in ['delete', 'remove']):
                tool_groups['delete'].append(tool)
            elif any(op in tool_name.lower() for op in ['query', 'search', 'find']):
                tool_groups['query'].append(tool)
            else:
                tool_groups['other'].append(tool)
        
        # Create CRUD workflow if applicable
        if tool_groups['create'] and tool_groups['read']:
            workflow = WorkflowConfig(
                workflow_name=f"{mcp_name}_crud_workflow",
                description=f"Create, read, update, and delete operations for {mcp_name}",
                agent_config_name=f"{mcp_name}_crud_agent",
                input_prompt="Perform {{operation}} on {{entity}} with data: {{data}}",
                templated_args=[
                    TemplatedArg(name="operation", description="CRUD operation to perform"),
                    TemplatedArg(name="entity", description="Entity to operate on"),
                    TemplatedArg(name="data", description="Data for the operation")
                ],
                tool_sequence=tool_groups['create'][:2] + tool_groups['read'][:2],
                domain="data_management"
            )
            workflows.append(workflow)
        
        # Create query workflow if applicable
        if tool_groups['query']:
            workflow = WorkflowConfig(
                workflow_name=f"{mcp_name}_query_workflow",
                description=f"Query and search operations for {mcp_name}",
                agent_config_name=f"{mcp_name}_query_agent",
                input_prompt="Search for {{query}} with filters: {{filters}}",
                templated_args=[
                    TemplatedArg(name="query", description="Search query"),
                    TemplatedArg(name="filters", description="Optional filters", required=False)
                ],
                tool_sequence=tool_groups['query'][:3],
                domain="information_retrieval"
            )
            workflows.append(workflow)
        
        # Create general workflow with all tools
        workflow = WorkflowConfig(
            workflow_name=f"{mcp_name}_general_workflow",
            description=f"General purpose workflow using all {mcp_name} tools",
            agent_config_name=f"{mcp_name}_general_agent",
            input_prompt="{{task_description}}",
            templated_args=[
                TemplatedArg(name="task_description", description="Description of task to perform")
            ],
            tool_sequence=tools[:10],  # Limit to first 10 tools
            domain="general"
        )
        workflows.append(workflow)
        
        # Save workflow configs as individual files
        project_dir = Path(tools_file_path).parent
        workflows_dir = project_dir / "workflows"
        workflows_dir.mkdir(exist_ok=True)
        
        for workflow in workflows:
            workflow_file = workflows_dir / f"{workflow.workflow_name}.json"
            with open(workflow_file, 'w') as f:
                json.dump(workflow.model_dump(), f, indent=2)
        
        logger.info(f"Created {len(workflows)} workflow configs")
        
        return {
            "status": "success",
            "phase": "2.1",
            "workflows_created": len(workflows),
            "workflows_directory": str(workflows_dir)
        }
        
    except Exception as e:
        logger.error(f"Workflow creation failed: {e}")
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

def _analyze_tool_capabilities(tools: List[str]) -> List[str]:
    """Analyze tools to understand MCP capabilities"""
    tool_descriptions = []
    
    for tool in tools[:5]:  # First 5 tools
        if 'add' in tool or 'create' in tool:
            tool_descriptions.append("create new entities")
        elif 'query' in tool or 'search' in tool or 'get' in tool:
            tool_descriptions.append("search and retrieve information")
        elif 'list' in tool:
            tool_descriptions.append("list existing entities")
        elif 'update' in tool or 'edit' in tool:
            tool_descriptions.append("modify existing entities")
    
    return tool_descriptions

def _generate_system_prompt(mcp_name: str, tool_descriptions: List[str]) -> str:
    """Generate intelligent system prompt based on capabilities"""
    capabilities = ", ".join(set(tool_descriptions)) if tool_descriptions else "perform various operations"
    return f"You are an expert agent for the {mcp_name} system. You can {capabilities} using the available tools. Execute tasks efficiently and provide clear results."

def _create_agent_from_workflow(workflow: dict, mcp_name: str) -> AgentConfig:
    """Helper to create agent config from workflow"""
    agent_name = workflow['agent_config_name']
    tools = workflow['tool_sequence']
    
    tool_descriptions = _analyze_tool_capabilities(tools)
    system_prompt = _generate_system_prompt(mcp_name, tool_descriptions)
    
    return AgentConfig(
        agent_name=agent_name,
        mcp_names=[mcp_name],
        system_prompt=system_prompt,
        allowed_tools=tools,
        model="gpt-5-mini",
        provider="openai",
        max_steps=20
    )

def _save_agent_configs(agents: dict, configs_dir: Path) -> None:
    """Helper to save agent configs to files"""
    configs_dir.mkdir(exist_ok=True)
    
    for agent_name, agent in agents.items():
        config_file = configs_dir / f"{agent_name}.json"
        with open(config_file, 'w') as f:
            json.dump(agent.model_dump(), f, indent=2)

def _load_workflow_configs(workflows_directory: str) -> tuple[list, str]:
    """Load all workflow configs from directory"""
    workflows = []
    workflows_dir = Path(workflows_directory)
    for workflow_file in workflows_dir.glob("*.json"):
        with open(workflow_file, 'r') as f:
            workflows.append(json.load(f))
    
    # Extract MCP name from first workflow
    mcp_name = workflows[0]['workflow_name'].rsplit('_', 2)[0] if workflows else "unknown"
    return workflows, mcp_name

def _create_unique_agents(workflows: list, mcp_name: str) -> dict:
    """Create agent configs for each unique agent"""
    agents = {}
    for workflow in workflows:
        agent_name = workflow['agent_config_name']
        if agent_name not in agents:
            agents[agent_name] = _create_agent_from_workflow(workflow, mcp_name)
    return agents

def _create_agent_configs_from_workflows(workflows_directory: str) -> tuple[dict, str]:
    """Create agent configs from workflow directory"""
    workflows, mcp_name = _load_workflow_configs(workflows_directory)
    agents = _create_unique_agents(workflows, mcp_name)
    return agents, str(Path(workflows_directory).parent / "agents")

def _build_phase2_2_success_response(agents: dict, configs_dir_str: str) -> dict:
    """Build success response for phase 2.2"""
    return {
        "status": "success",
        "phase": "2.2", 
        "agents_created": len(agents),
        "configs_directory": configs_dir_str,
        "project_complete": True
    }

def phase2_2_create_agent_configs(workflows_directory: str) -> dict:
    """Phase 2.2: Generate agent configurations from workflows"""
    logger.info(f"Phase 2.2: Creating agent configs from {workflows_directory}")
    
    try:
        agents, configs_dir_str = _create_agent_configs_from_workflows(workflows_directory)
        _save_agent_configs(agents, Path(configs_dir_str))
        
        logger.info(f"Created {len(agents)} agent configs")
        return _build_phase2_2_success_response(agents, configs_dir_str)
        
    except Exception as e:
        logger.error(f"Agent config creation failed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "error": str(e), "traceback": traceback.format_exc()}

# ============= FASTMCP SERVER SETUP =============

app = FastMCP("MCPSquared Minimal")

# Register generation tools
app.tool()(phase1_1_install_mcp_tool)
app.tool()(phase1_2_list_mcp_tools_tool)
app.tool()(phase2_1_create_workflow_configs)
app.tool()(phase2_2_create_agent_configs)

# Merged server only has phase tools - no runtime execution

def main():
    """Run the server"""
    logger.info("Starting MCPSquared Minimal Server")
    app.run()

if __name__ == "__main__":
    main()