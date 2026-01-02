"""
Orders MCP Tools
Create physician orders, POC updates, and other order types
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_order_tools(server: Server, api: PointCareMockAPI):
    """Register order tools with the MCP server"""

    @server.list_tools()
    async def list_order_tools() -> list[Tool]:
        return [
            Tool(
                name="create_order",
                description="""Create a new order.

Creates orders for physician signature. Types include:
- physician: General physician order
- poc_update: Plan of Care update
- discharge: Discharge from agency
- hospital_hold: Hospital hold order
- roc: Resumption of Care order""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "order_type": {
                            "type": "string",
                            "description": "Type of order",
                            "enum": ["physician", "poc_update", "discharge", "hospital_hold", "roc"]
                        },
                        "physician_id": {
                            "type": "string",
                            "description": "Ordering physician ID or NPI"
                        },
                        "instructions": {
                            "type": "string",
                            "description": "Order instructions/details"
                        },
                        "effective_date": {
                            "type": "string",
                            "description": "Effective date (YYYY-MM-DD). Defaults to today."
                        }
                    },
                    "required": ["patient_id", "order_type", "physician_id", "instructions"]
                }
            )
        ]

    @server.call_tool()
    async def call_order_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "create_order":
                result = api.create_order(
                    patient_id=arguments["patient_id"],
                    order_type=arguments["order_type"],
                    physician_id=arguments["physician_id"],
                    instructions=arguments["instructions"],
                    effective_date=arguments.get("effective_date")
                )

                order = result["order"]

                type_labels = {
                    "physician": "Physician Order",
                    "poc_update": "Plan of Care Update",
                    "discharge": "Discharge Order",
                    "hospital_hold": "Hospital Hold",
                    "roc": "Resumption of Care"
                }

                output = f"## 📋 Order Created\n\n"
                output += f"- **Order ID:** {result['order_id']}\n"
                output += f"- **Type:** {type_labels.get(order['order_type'], order['order_type'])}\n"
                output += f"- **Patient:** {order['patient_id']}\n"
                output += f"- **Physician:** {order['physician_id']}\n"
                output += f"- **Effective Date:** {order['effective_date']}\n"
                output += f"- **Status:** {order['status']}\n\n"
                output += f"**Instructions:**\n{order['instructions']}\n\n"
                output += f"_{result['message']}_"

                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
