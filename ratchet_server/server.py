#!/usr/bin/env python3
"""
Ratchet EMR MCP Server
Healthcare MCP tool for patient management with mock PointCare/HCHB APIs

Usage:
    python -m ratchet_server.server
    # or
    python ratchet_server/server.py
"""

import asyncio
import logging
from pathlib import Path

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .mock_api import PointCareMockAPI
from .tools import (
    register_visit_tools,
    register_demographics_tools,
    register_vitals_tools,
    register_medications_tools,
    register_assessment_tools,
    register_intervention_tools,
    register_wound_tools,
    register_order_tools,
    register_notes_tools,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger("ratchet")

# Initialize the MCP server
server = Server("ratchet-emr")

# Initialize the mock API (shared across all tools)
data_dir = Path(__file__).parent.parent / "mock_data"
api = PointCareMockAPI(data_dir=str(data_dir))


def register_all_tools():
    """Register all MCP tools with the server"""
    register_visit_tools(server, api)
    register_demographics_tools(server, api)
    register_vitals_tools(server, api)
    register_medications_tools(server, api)
    register_assessment_tools(server, api)
    register_intervention_tools(server, api)
    register_wound_tools(server, api)
    register_order_tools(server, api)
    register_notes_tools(server, api)
    logger.info("All Ratchet EMR tools registered")


async def main():
    """Main entry point for the MCP server"""
    logger.info("Starting Ratchet EMR MCP Server")
    logger.info(f"Data directory: {data_dir}")

    # Register all tools
    register_all_tools()

    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
