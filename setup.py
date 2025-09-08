#!/usr/bin/env python3
"""
MCPSquared - Ultra-Minimal Workflow Generation for MCPs
"""

from setuptools import setup, find_packages

setup(
    name="mcpsquared",
    version="0.1.0",
    description="Ultra-Minimal MCPSquared MVP - Workflow generation for MCP servers",
    author="Isaac & Claude",
    author_email="isaacwrubin@gmail.com",
    packages=[
        "mcpsquared",
        "mcpsquared.mcpsquared_main", 
        "mcpsquared.phase_tools",
        "mcpsquared.phase_tools.agents",
        "mcpsquared.phase_tools.models",
        "mcpsquared.phase_tools.utils",
        "mcpsquared.schema_tools",
        "mcpsquared.schema_tools.models"
    ],
    install_requires=[
        "fastmcp>=2.0.0",
        "pydantic>=2.0.0",
        "mcp-use>=0.1.0",
        "langchain-openai>=0.1.0",
        "python-dotenv>=1.0.0"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "mcpsquared-server=mcpsquared.server:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)