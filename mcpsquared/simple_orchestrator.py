"""
Simple Orchestrator for Ultra-Minimal MCPSquared
Just runs one agent with the merged MCP server
"""

import os
import json
import asyncio
import logging
from typing import Dict, Any
from mcp_use import MCPClient, MCPAgent
from langchain_openai import ChatOpenAI

# Do not call basicConfig in library code
logger = logging.getLogger(__name__)

class SimpleOrchestrator:
    """
    Minimal orchestrator that:
    1. Creates an MCPAgent with merged server
    2. Runs the 4 phase tools in sequence
    3. Returns the generated package
    """
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        # Path to our merged MCP server (now in package)
        import mcpsquared.merged_mcp_server
        self.server_path = mcpsquared.merged_mcp_server.__file__
        logger.info("SimpleOrchestrator initialized")
    
    async def generate_workflows(self, mcp_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point - generates workflows for the given MCP
        
        Args:
            mcp_config: Dict with name, command, args for target MCP
            
        Returns:
            Result dict with package location
        """
        logger.info(f"Generating workflows for MCP: {mcp_config.get('name')}")
        
        # Create MCP client with our merged server
        client_config = {
            "mcpServers": {
                "mcpsquared": {
                    "command": "python",
                    "args": [self.server_path],
                    "transport": "stdio",
                    "env": {
                        "OPENAI_API_KEY": self.api_key,
                        "WORK_DIR": os.getenv("WORK_DIR"),
                        "PHASE_SERVER_DEBUG_PATH": os.getenv("PHASE_SERVER_DEBUG_PATH"),
                        "PHASE_SERVER_DEBUG_NICKNAME": os.getenv("PHASE_SERVER_DEBUG_NICKNAME")
                    }
                }
            }
        }
        
        client = MCPClient.from_dict(client_config)
        
        # Create agent with simple prompt
        agent = MCPAgent(
            llm=ChatOpenAI(model="gpt-5-mini"),
            client=client,
            system_prompt=self._get_system_prompt(),
            max_steps=10
        )
        
        # Build the execution prompt
        prompt = self._build_execution_prompt(mcp_config)
        
        try:
            # Run the agent
            result = await agent.run(prompt)
            
            logger.info(f"Agent completed: {result}")
            
            # Parse result to get project directory
            return self._parse_result(result, mcp_config)
            
        except Exception as e:
            logger.error(f"Workflow generation failed: {e}")
            import traceback
            return {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        finally:
            await client.close_all_sessions()
    
    def _get_system_prompt(self) -> str:
        """Simple system prompt for the agent"""
        return """You are MCPSquared workflow generator. Execute the 4 phase tools in sequence:

1. Call phase1_1_install_mcp_tool to test connection
2. Call phase1_2_list_mcp_tools_tool to discover tools (save the tools_file_path)
3. Call phase2_1_create_workflow_configs with the tools_file_path (save the workflows_directory)
4. Call phase2_2_create_agent_configs with the workflows_directory

Return the final project directory path when complete."""
    
    def _build_execution_prompt(self, mcp_config: Dict[str, Any]) -> str:
        """Build the execution prompt with MCP details"""
        return f"""Generate workflows for this MCP:
        
Name: {mcp_config['name']}
Command: {mcp_config['command']}
Args: {json.dumps(mcp_config['args'])}

Execute all 4 phases and return the project directory."""
    
    def _parse_result(self, result: str, mcp_config: Dict[str, Any]) -> Dict[str, Any]:
        """Parse agent result"""
        # Look for success indicators
        if "project_complete" in result or "configs_directory" in result:
            return {
                "status": "success",
                "result": result,
                "mcp_name": mcp_config.get("name"),
                "message": "Workflow package generated successfully"
            }
        else:
            return {
                "status": "partial",
                "result": result,
                "mcp_name": mcp_config.get("name"),
                "message": "Generation may be incomplete"
            }
    
    # ============= API STUB METHODS =============
    # These match the original MCPSquaredOrchestrator API but are not implemented yet
    
    def get_flows(self, domain: str = None) -> str:
        """List available generated workflows, optionally filtered by domain"""
        return '{"error": "get_flows not implemented in alpha version"}'
    
    def get_flow_domains(self) -> str:
        """List all available workflow domains/categories"""
        return '{"error": "get_flow_domains not implemented in alpha version"}'
    
    def sub_chat(self, message: str, history_id: str) -> str:
        """Chat interface for workflow planning and assistance"""
        return '{"error": "sub_chat not implemented in alpha version"}'
    
    def package_workflow_mcp(self, workflows: list, base_mcp: str) -> str:
        """Package specific workflows into installable MCP"""
        return '{"error": "package_workflow_mcp not implemented in alpha version"}'
    
    def get_processed_mcps_list(self) -> str:
        """Get list of all MCPs that have been processed by MCPSquared"""
        return '{"error": "get_processed_mcps_list not implemented in alpha version"}'
    
    def search_my_workflows(self, mcp_name: str = None, domain: str = None, workflow_name_pattern: str = None) -> str:
        """Search workflows across all processed MCPs with filtering options"""
        return '{"error": "search_my_workflows not implemented in alpha version"}'
    
    async def execute_any_workflow(self, workflow_name: str, workflow_args: Dict[str, Any], package_name: str = None) -> str:
        """Execute any workflow from the registry by name"""
        logger.info(f"Executing workflow: {workflow_name} from project: {package_name}")
        
        try:
            # Import _base workflow_runner directly (no merged server needed for execution)
            import sys
            from pathlib import Path
            sys.path.insert(0, '/tmp/mcpsquared-base')
            from mcpsquared_base.utils.workflow_runner import run_workflow
            from mcpsquared_base.models.schemas import InputArgs, InputArg
            from mcpsquared_base.utils.debug import mcp_debug_log
            
            mcp_debug_log(f"execute_any_workflow: {workflow_name} from {package_name}")
            
            # Convert workflow_args to InputArgs format
            input_args = InputArgs(args=[
                InputArg(name=key, value=value) 
                for key, value in workflow_args.items()
            ])
            
            mcp_debug_log(f"Input args: {input_args.model_dump()}")
            
            # Use _base workflow_runner directly
            # For now, assume project directory from WORK_DIR - should be smarter in future
            project_directory = package_name or os.getenv("WORK_DIR", "/tmp/mcpsquared")
            
            mcp_debug_log(f"Calling run_workflow with config_dir={project_directory}")
            result = await run_workflow(
                workflow_name=workflow_name,
                input_args=input_args,
                config_dir=project_directory  # Points to dir containing workflows/ and agents/
            )
            
            return json.dumps({
                "status": "success",
                "workflow_name": workflow_name,
                "result": result
            })
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            import traceback
            return json.dumps({
                "status": "error", 
                "error": str(e), 
                "traceback": traceback.format_exc(),
                "workflow_name": workflow_name
            })
    
    async def domain_specific_agent(self, prompt: str) -> str:
        """Execute domain-specific agent for advanced workflow generation"""
        return '{"error": "domain_specific_agent not implemented in alpha version"}'

async def main():
    """Test the orchestrator"""
    orchestrator = SimpleOrchestrator()
    
    # Test with carton MCP
    test_config = {
        "name": "carton",
        "command": "python",
        "args": ["/home/GOD/carton_mcp/server_fastmcp.py"]
    }
    
    result = await orchestrator.generate_workflows(test_config)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())