"""
Coordination Notes MCP Tools
Communication notes and care coordination documentation
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_notes_tools(server: Server, api: PointCareMockAPI):
    """Register coordination notes tools with the MCP server"""

    @server.list_tools()
    async def list_notes_tools() -> list[Tool]:
        return [
            Tool(
                name="add_coordination_note",
                description="""Add a coordination note for a patient.

Documents communication, care coordination, and other notes.
Types: Clinical, Physician Communication, Case Conference, Insurance, Other.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "note_type": {
                            "type": "string",
                            "description": "Type of coordination note",
                            "enum": ["Clinical", "Physician Communication", "Case Conference", "Insurance", "Family Communication", "Other"]
                        },
                        "content": {
                            "type": "string",
                            "description": "Note content"
                        }
                    },
                    "required": ["patient_id", "note_type", "content"]
                }
            ),
            Tool(
                name="get_coordination_notes",
                description="""Get coordination notes for a patient.

Returns recent notes with optional type filter.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "note_type": {
                            "type": "string",
                            "description": "Filter by note type",
                            "enum": ["Clinical", "Physician Communication", "Case Conference", "Insurance", "Family Communication", "Other"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum notes to return",
                            "default": 20
                        }
                    },
                    "required": ["patient_id"]
                }
            )
        ]

    @server.call_tool()
    async def call_notes_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "add_coordination_note":
                result = api.add_coordination_note(
                    patient_id=arguments["patient_id"],
                    note_type=arguments["note_type"],
                    content=arguments["content"]
                )

                output = f"✅ **Coordination Note Added**\n\n"
                output += f"- Note ID: {result['note_id']}\n"
                output += f"- Type: {result['note']['type']}\n"
                output += f"- Author: {result['note']['author']}\n"
                output += f"- Created: {result['note']['created_at']}\n\n"
                output += f"**Content:**\n{result['note']['content']}"

                return [TextContent(type="text", text=output)]

            elif name == "get_coordination_notes":
                result = api.get_coordination_notes(
                    patient_id=arguments["patient_id"],
                    note_type=arguments.get("note_type"),
                    limit=arguments.get("limit", 20)
                )

                output = f"# Coordination Notes for {result['patient_id']}\n\n"
                output += f"Total Notes: {result['note_count']}\n\n"

                if not result["notes"]:
                    output += "_No coordination notes found._\n"
                else:
                    for note in result["notes"]:
                        output += f"## {note['type']} - {note.get('visit_date', 'N/A')}\n"
                        output += f"**{note.get('author', 'Unknown')}**\n\n"
                        output += f"{note['content']}\n\n"
                        output += "---\n\n"

                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
