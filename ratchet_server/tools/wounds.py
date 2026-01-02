"""
Wound Documentation MCP Tools
Track wounds and surgical incisions with ICC (Integumentary Command Center)
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_wound_tools(server: Server, api: PointCareMockAPI):
    """Register wound documentation tools with the MCP server"""

    @server.list_tools()
    async def list_wound_tools() -> list[Tool]:
        return [
            Tool(
                name="get_wound_record",
                description="""Get active wounds for a patient.

Returns wound list with measurements, characteristics, and last assessment date.
Used for tracking pressure ulcers, surgical incisions, and other wounds.""",
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
                name="add_wound",
                description="""Add a new wound to track.

Creates a new wound record for the patient. Use for new pressure ulcers,
surgical incisions, or other wounds requiring tracking.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "location": {
                            "type": "string",
                            "description": "Wound location (e.g., 'Right knee - anterior', 'Sacrum')"
                        },
                        "wound_type": {
                            "type": "string",
                            "description": "Type of wound",
                            "enum": ["Surgical incision", "Pressure ulcer", "Venous ulcer", "Arterial ulcer", "Diabetic ulcer", "Skin tear", "Laceration", "Burn", "Other"]
                        },
                        "onset_date": {
                            "type": "string",
                            "description": "Date wound occurred/discovered (YYYY-MM-DD)"
                        }
                    },
                    "required": ["patient_id", "location", "wound_type", "onset_date"]
                }
            ),
            Tool(
                name="document_wound_assessment",
                description="""Document wound assessment during visit.

Records measurements and characteristics. Calculates WAT (Wound Assessment Tool) score.
Required for wound care visits and tracking healing progress.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Active visit session ID"
                        },
                        "wound_id": {
                            "type": "string",
                            "description": "Wound ID from wound record"
                        },
                        "length_cm": {
                            "type": "number",
                            "description": "Wound length in cm"
                        },
                        "width_cm": {
                            "type": "number",
                            "description": "Wound width in cm"
                        },
                        "depth_cm": {
                            "type": "number",
                            "description": "Wound depth in cm"
                        },
                        "edges": {
                            "type": "string",
                            "description": "Wound edge description",
                            "enum": ["Well-approximated", "Approximated with staples", "Approximated with sutures", "Rolled", "Undermined", "Macerated"]
                        },
                        "drainage": {
                            "type": "string",
                            "description": "Drainage type and amount",
                            "enum": ["None", "Minimal serous", "Moderate serous", "Sanguineous", "Serosanguineous", "Purulent"]
                        },
                        "periwound": {
                            "type": "string",
                            "description": "Periwound skin condition"
                        },
                        "infection_signs": {
                            "type": "boolean",
                            "description": "Signs of infection present",
                            "default": False
                        },
                        "wound_bed": {
                            "type": "string",
                            "description": "Wound bed tissue type",
                            "enum": ["Epithelializing", "Granulating", "Slough", "Eschar", "Mixed"]
                        }
                    },
                    "required": ["session_id", "wound_id", "length_cm", "width_cm"]
                }
            )
        ]

    @server.call_tool()
    async def call_wound_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "get_wound_record":
                result = api.get_wound_record(arguments["patient_id"])

                output = f"# Wound Record for {result['patient_id']}\n\n"
                output += f"Active Wounds: {result['active_wound_count']}\n\n"

                if not result["wounds"]:
                    output += "_No active wounds documented._\n"
                else:
                    for wound in result["wounds"]:
                        output += f"## {wound['wound_id']}: {wound['type']}\n"
                        output += f"- **Location:** {wound['location']}\n"
                        output += f"- **Onset Date:** {wound['onset_date']}\n"
                        output += f"- **Status:** {wound['status']}\n"

                        if wound.get("measurements"):
                            m = wound["measurements"]
                            output += f"- **Size:** {m.get('length_cm', 0)} x {m.get('width_cm', 0)} x {m.get('depth_cm', 0)} cm\n"

                        if wound.get("characteristics"):
                            c = wound["characteristics"]
                            output += f"- **Edges:** {c.get('edges', 'N/A')}\n"
                            output += f"- **Drainage:** {c.get('drainage', 'N/A')}\n"
                            output += f"- **Periwound:** {c.get('periwound', 'N/A')}\n"

                        if wound.get("wound_care_order"):
                            output += f"- **Order:** {wound['wound_care_order']}\n"

                        if wound.get("last_assessment_date"):
                            output += f"- **Last Assessed:** {wound['last_assessment_date']}\n"

                        output += "\n"

                return [TextContent(type="text", text=output)]

            elif name == "add_wound":
                result = api.add_wound(
                    patient_id=arguments["patient_id"],
                    location=arguments["location"],
                    wound_type=arguments["wound_type"],
                    onset_date=arguments["onset_date"]
                )

                output = f"✅ **Wound Added**\n\n"
                output += f"- Wound ID: {result['wound_id']}\n"
                output += f"- Type: {result['wound']['type']}\n"
                output += f"- Location: {result['wound']['location']}\n"
                output += f"- Onset: {result['wound']['onset_date']}\n"

                return [TextContent(type="text", text=output)]

            elif name == "document_wound_assessment":
                measurements = {
                    "length_cm": arguments["length_cm"],
                    "width_cm": arguments["width_cm"],
                    "depth_cm": arguments.get("depth_cm", 0)
                }

                attributes = {
                    "edges": arguments.get("edges"),
                    "drainage": arguments.get("drainage"),
                    "periwound": arguments.get("periwound"),
                    "infection_signs": arguments.get("infection_signs", False),
                    "wound_bed": arguments.get("wound_bed")
                }

                result = api.document_wound_assessment(
                    session_id=arguments["session_id"],
                    wound_id=arguments["wound_id"],
                    measurements=measurements,
                    attributes={k: v for k, v in attributes.items() if v is not None}
                )

                output = f"## Wound Assessment Documented\n\n"
                output += f"- Wound ID: {result['wound_id']}\n"
                output += f"- Size: {measurements['length_cm']} x {measurements['width_cm']} x {measurements['depth_cm']} cm\n"
                output += f"- WAT Score: {result['wat_score']}/5\n\n"

                if result["wat_score"] <= 1:
                    output += "✅ Wound healing well\n"
                elif result["wat_score"] <= 3:
                    output += "⚠️ Monitor wound closely\n"
                else:
                    output += "🔴 Wound requires attention - consider physician notification\n"

                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
