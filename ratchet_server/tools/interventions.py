"""
Interventions & Goals MCP Tools
Document care provided and track goal progress
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_intervention_tools(server: Server, api: PointCareMockAPI):
    """Register intervention and goal tools with the MCP server"""

    @server.list_tools()
    async def list_intervention_tools() -> list[Tool]:
        return [
            Tool(
                name="get_active_interventions",
                description="""Get active interventions and goals for a patient.

Returns all interventions from care plan with linked goals.
Shows goal status (met/in progress) and intervention frequencies.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        }
                    },
                    "required": ["patient_id"]
                }
            ),
            Tool(
                name="document_intervention",
                description="""Document that an intervention was provided during visit.

Links to care plan interventions. Can mark as provided or not provided
with optional details.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Active visit session ID"
                        },
                        "intervention_id": {
                            "type": "string",
                            "description": "Intervention ID from care plan"
                        },
                        "provided": {
                            "type": "boolean",
                            "description": "Whether intervention was provided",
                            "default": True
                        },
                        "details": {
                            "type": "string",
                            "description": "Additional notes about the intervention"
                        }
                    },
                    "required": ["session_id", "intervention_id"]
                }
            ),
            Tool(
                name="update_goal_status",
                description="""Update goal progress during visit.

Track goal progress: in_progress, met, not_met.
When goal is met, updates patient record permanently.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Active visit session ID"
                        },
                        "goal_id": {
                            "type": "string",
                            "description": "Goal ID from care plan"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["in_progress", "met", "not_met", "revised"],
                            "description": "New goal status"
                        },
                        "notes": {
                            "type": "string",
                            "description": "Progress notes for this goal"
                        }
                    },
                    "required": ["session_id", "goal_id", "status"]
                }
            )
        ]

    @server.call_tool()
    async def call_intervention_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "get_active_interventions":
                result = api.get_active_interventions(arguments["patient_id"])

                output = f"# Interventions & Goals for {result['patient_id']}\n\n"

                # Goals summary
                output += "## Goals Summary\n"
                output += f"- Total Goals: {result['goal_count']}\n"
                output += f"- Met: {result['goals_met']}\n"
                output += f"- In Progress: {result['goals_in_progress']}\n\n"

                # Goals detail
                output += "## Goals\n\n"
                for goal in result["goals"]:
                    status_icon = "✅" if goal["status"] == "met" else "🔄"
                    output += f"### {status_icon} {goal['goal_id']}\n"
                    output += f"**{goal['text']}**\n"
                    output += f"- Pathway: {goal['pathway']}\n"
                    output += f"- Target Date: {goal['target_date']}\n"
                    output += f"- Status: {goal['status']}\n"
                    if goal.get("met_date"):
                        output += f"- Met Date: {goal['met_date']}\n"
                    output += "\n"

                # Interventions
                output += "## Interventions\n\n"
                for int in result["interventions"]:
                    output += f"### {int['int_id']}\n"
                    output += f"**{int['text']}**\n"
                    output += f"- Pathway: {int['pathway']}\n"
                    output += f"- Frequency: {int['frequency']}\n\n"

                return [TextContent(type="text", text=output)]

            elif name == "document_intervention":
                result = api.document_intervention(
                    session_id=arguments["session_id"],
                    intervention_id=arguments["intervention_id"],
                    provided=arguments.get("provided", True),
                    details=arguments.get("details")
                )

                status = "✅ Provided" if result["provided"] else "❌ Not Provided"
                output = f"## Intervention Documented\n\n"
                output += f"- Intervention: {result['intervention_id']}\n"
                output += f"- Status: {status}\n"

                return [TextContent(type="text", text=output)]

            elif name == "update_goal_status":
                result = api.update_goal_status(
                    session_id=arguments["session_id"],
                    goal_id=arguments["goal_id"],
                    status=arguments["status"],
                    notes=arguments.get("notes")
                )

                status_icons = {
                    "met": "✅",
                    "in_progress": "🔄",
                    "not_met": "❌",
                    "revised": "📝"
                }
                icon = status_icons.get(arguments["status"], "")

                output = f"## Goal Status Updated\n\n"
                output += f"- Goal: {result['goal_id']}\n"
                output += f"- New Status: {icon} {result['new_status']}\n"

                if arguments["status"] == "met":
                    output += "\n🎉 **Goal marked as MET!** Patient record updated."

                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
