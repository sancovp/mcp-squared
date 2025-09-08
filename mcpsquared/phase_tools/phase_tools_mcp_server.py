"""
Phase Tools FastMCP Server

Implements the 7 phase tools for MCPSquared workflow generation:
- Phase 1: MCP Analysis (install, discover tools)
- Phase 2: Workflow Design (design workflows, create agent configs)
- Phase 3: Package Generation (render implementations, documentation, packaging)
"""

import os
import sys
from fastmcp import FastMCP
import logging

# CRITICAL: Immediately validate API key is available in environment
API_KEY_VARS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "AZURE_OPENAI_API_KEY"]
found_keys = [var for var in API_KEY_VARS if os.getenv(var)]

if not found_keys:
    print(f"FATAL ERROR: No API keys found in environment!", file=sys.stderr)
    print(f"Phase tools server requires at least one of: {API_KEY_VARS}", file=sys.stderr)
    print(f"Current environment keys: {[k for k in os.environ.keys() if 'KEY' in k]}", file=sys.stderr)
    sys.exit(1)

logger = logging.getLogger(__name__)
logger.info(f"Phase tools server starting with API keys: {found_keys}")

# Import modular components
from .models.requests import (
    MCPConfig, ToolsFileRequest, DesignsFileRequest
)
from .phases.phase1 import phase1_1_install_mcp_tool, phase1_2_list_mcp_tools_tool
from .phases.phase2 import phase2_1_call_workflow_designer_subagent_tool, phase2_2_call_agent_designer_subagent_tool, debug_environment_tool, debug_schema_import_test

# Setup logging
logger = logging.getLogger(__name__)

# Create FastMCP app
app = FastMCP("MCPSquared Phase Tools")

# Register phase tools
app.tool()(phase1_1_install_mcp_tool)
app.tool()(phase1_2_list_mcp_tools_tool)
app.tool()(phase2_1_call_workflow_designer_subagent_tool)
app.tool()(phase2_2_call_agent_designer_subagent_tool)
app.tool()(debug_environment_tool)
app.tool()(debug_schema_import_test)


# Legacy functions (to be removed - now handled by modular components)
# Keeping for compatibility during transition


def main():
    """Main entry point for console script"""
    logger.info("Starting MCPSquared Phase Tools MCP Server")
    app.run()

if __name__ == "__main__":
    main()