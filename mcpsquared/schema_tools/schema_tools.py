"""
Schema-enforced tools for creating workflow and agent configurations
"""

import json
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from schema_mcp.models.schemas import (
    WorkflowConfig, AgentConfig, WorkflowDesigns, AgentConfigs,
    TemplatedArg, MCPClientConfig, MCPServerConfig
)

logger = logging.getLogger(__name__)


def extract_mcp_names_from_tools(allowed_tools: List[str]) -> List[str]:
    """
    Extract unique MCP names from prefixed tool names
    
    Args:
        allowed_tools: List of prefixed tool names like ["mcp__carton__add_concept", "mcp__carton__query_wiki_graph"]
        
    Returns:
        List of unique MCP names like ["carton"]
    """
    mcp_names = set()
    for tool in allowed_tools:
        if tool.startswith("mcp__"):
            parts = tool.split("__")
            if len(parts) >= 3:  # mcp__name__tool
                mcp_name = parts[1]
                mcp_names.add(mcp_name)
    return list(mcp_names)


def create_workflow_config(
    workflow_name: str,
    description: str,
    agent_config_name: str,
    input_prompt: str,
    tool_sequence: List[str],
    templated_args: Optional[List[Dict[str, Any]]] = None,
    domain: Optional[str] = None
) -> WorkflowConfig:
    """
    Create a validated WorkflowConfig object
    
    Args:
        workflow_name: Name of the workflow
        description: Clear description of what the workflow does
        agent_config_name: Name of the agent config to use
        input_prompt: Template prompt with {{placeholders}}
        templated_args: List of dicts with name, description, type, required, default
        tool_sequence: Ordered list of tools to execute
        domain: Optional domain category
        
    Returns:
        Validated WorkflowConfig object
    """
    logger.debug(f"Creating workflow config for: {workflow_name}")
    
    # Convert templated_args dicts to TemplatedArg objects
    template_args = [TemplatedArg(**arg) for arg in (templated_args or [])]
    
    workflow = WorkflowConfig(
        workflow_name=workflow_name,
        description=description,
        agent_config_name=agent_config_name,
        input_prompt=input_prompt,
        templated_args=template_args,
        tool_sequence=tool_sequence,
        domain=domain
    )
    
    logger.debug(f"Successfully created workflow config: {workflow_name}")
    return workflow


def create_agent_config(
    agent_name: str,
    system_prompt: str,
    allowed_tools: List[str],
    model: str = "gpt-5-mini",
    provider: str = "openai",
    max_steps: int = 20
) -> AgentConfig:
    """
    Create a validated AgentConfig object with mcp_names (for agent loader resolution)
    
    Args:
        agent_name: Name of the agent
        system_prompt: System prompt for the agent
        allowed_tools: List of prefixed tool names (e.g. ["mcp__carton__add_concept"])
        model: LLM model to use
        provider: LLM provider
        max_steps: Maximum steps for agent execution
        
    Returns:
        Validated AgentConfig object with mcp_names list for loader to resolve
    """
    logger.debug(f"Creating agent config for: {agent_name}")
    
    # Extract MCP names from prefixed tool names
    mcp_names = extract_mcp_names_from_tools(allowed_tools)
    logger.debug(f"Extracted MCP names from tools: {mcp_names}")
    
    agent = AgentConfig(
        agent_name=agent_name,
        mcp_names=mcp_names,  # Store MCP names for loader to resolve
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        model=model,
        provider=provider,
        max_steps=max_steps
    )
    
    logger.debug(f"Successfully created agent config: {agent_name}")
    return agent


def create_agent_config_from_strings(
    agent_name: str,
    mcp_names_str: str,  # Comma-separated string like "carton,filesystem"
    system_prompt: str,
    allowed_tools_str: str,  # Comma-separated string like "mcp__carton__add_concept,mcp__carton__query_wiki_graph"
    model: str = "gpt-5-mini",
    provider: str = "openai",
    max_steps: int = 20
) -> AgentConfig:
    """
    Agent-friendly function to create AgentConfig from string parameters
    
    Args:
        agent_name: Name of the agent
        mcp_names_str: Comma-separated MCP names (e.g. "carton,filesystem")
        system_prompt: System prompt for the agent
        allowed_tools_str: Comma-separated tool names (e.g. "mcp__carton__add_concept,mcp__carton__query_wiki_graph")
        model: LLM model to use
        provider: LLM provider
        max_steps: Maximum steps for agent execution
        
    Returns:
        Validated AgentConfig object with mcp_names
    """
    logger.debug(f"Creating agent config from strings for: {agent_name}")
    
    # Parse comma-separated strings
    mcp_names = [name.strip() for name in mcp_names_str.split(',') if name.strip()]
    allowed_tools = [tool.strip() for tool in allowed_tools_str.split(',') if tool.strip()]
    
    logger.debug(f"Parsed MCP names: {mcp_names}")
    logger.debug(f"Parsed allowed tools: {allowed_tools}")
    
    agent = AgentConfig(
        agent_name=agent_name,
        mcp_names=mcp_names,
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        model=model,
        provider=provider,
        max_steps=max_steps
    )
    
    logger.debug(f"Successfully created agent config from strings: {agent_name}")
    return agent


def write_workflow_designs_file(
    workflows: List[WorkflowConfig],
    file_path: str,
    mcp_name: str
) -> Dict[str, Any]:
    """
    Write validated workflow designs to JSON file
    
    Args:
        workflows: List of WorkflowConfig objects
        file_path: Path to write the JSON file
        mcp_name: Name of the source MCP
        
    Returns:
        Result dict with status and file path
    """
    logger.info(f"Writing {len(workflows)} workflow designs to: {file_path}")
    
    try:
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Create WorkflowDesigns object
        designs = WorkflowDesigns(
            workflows=workflows,
            mcp_name=mcp_name,
            generated_at=datetime.now().isoformat()
        )
        
        # Write to file
        with open(file_path, 'w') as f:
            json.dump(designs.to_json_list(), f, indent=2)
        
        logger.info(f"Successfully wrote workflow designs to: {file_path}")
        return {
            "status": "success",
            "file_path": file_path,
            "workflow_count": len(workflows),
            "message": f"Workflows written to {file_path}"
        }
        
    except Exception as e:
        logger.error(f"Failed to write workflow designs: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "file_path": file_path
        }


def write_agent_configs_directory(
    agent_name: str,
    mcp_names: List[str],
    system_prompt: str,
    allowed_tools: List[str],
    directory_path: str,
    model: str = "gpt-5-mini",
    provider: str = "openai",
    max_steps: int = 20
) -> Dict[str, Any]:
    """
    Create and write agent config JSON file from parameters
    
    Args:
        agent_name: Name of the agent
        mcp_names: List of MCP names (e.g. ["carton"])
        system_prompt: System prompt for the agent
        allowed_tools: List of tool names (e.g. ["mcp__carton__add_concept"])
        directory_path: Directory path to write the config file
        model: LLM model to use
        provider: LLM provider
        max_steps: Maximum steps for agent execution
        
    Returns:
        Result dict with status and file path
    """
    logger.info(f"Creating agent config file for: {agent_name}")
    
    try:
        # Ensure directory exists
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        
        # Create agent config JSON data
        config_data = {
            "agent_name": agent_name,
            "mcp_names": mcp_names,
            "system_prompt": system_prompt,
            "allowed_tools": allowed_tools,
            "model": model,
            "provider": provider,
            "max_steps": max_steps
        }
        
        # Write config file
        filename = f"{agent_name}.json"
        file_path = os.path.join(directory_path, filename)
        with open(file_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Successfully wrote agent config to: {file_path}")
        return {
            "status": "success",
            "directory_path": directory_path,
            "file_path": file_path,
            "agent_name": agent_name,
            "message": f"Agent config written to {file_path}"
        }
        
    except Exception as e:
        logger.error(f"Failed to write agent configs: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "directory_path": directory_path
        }


def validate_workflow_json(file_path: str) -> Dict[str, Any]:
    """
    Validate an existing workflow JSON file against schema
    
    Args:
        file_path: Path to the JSON file to validate
        
    Returns:
        Validation result dict
    """
    logger.info(f"Validating workflow JSON: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Validate each workflow in the list
        workflows = [WorkflowConfig(**workflow) for workflow in data]
        
        logger.info(f"Successfully validated {len(workflows)} workflows in: {file_path}")
        return {
            "status": "valid",
            "workflow_count": len(workflows),
            "file_path": file_path
        }
        
    except Exception as e:
        logger.error(f"Validation failed for {file_path}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "invalid",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "file_path": file_path
        }


def validate_agent_json(file_path: str) -> Dict[str, Any]:
    """
    Validate an existing agent JSON file against schema
    
    Args:
        file_path: Path to the JSON file to validate
        
    Returns:
        Validation result dict
    """
    logger.info(f"Validating agent JSON: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Validate agent config
        agent = AgentConfig(**data)
        
        logger.info(f"Successfully validated agent config: {file_path}")
        return {
            "status": "valid",
            "agent_name": agent.agent_name,
            "file_path": file_path
        }
        
    except Exception as e:
        logger.error(f"Validation failed for {file_path}: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "invalid",
            "error": str(e),
            "traceback": traceback.format_exc(),
            "file_path": file_path
        }