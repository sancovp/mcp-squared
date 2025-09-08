#!/usr/bin/env python3
"""
MCPSquared Main Server Entry Point
"""

from mcpsquared.mcpsquared_main.mcpsquared_main_server import app

def main():
    """Main entry point for MCPSquared server"""
    app.run()

if __name__ == "__main__":
    main()