"""
Demographics MCP Tools
Patient demographics, insurance, and episode information
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_demographics_tools(server: Server, api: PointCareMockAPI):
    """Register demographics tools with the MCP server"""

    @server.list_tools()
    async def list_demographics_tools() -> list[Tool]:
        return [
            Tool(
                name="get_demographics",
                description="""Get patient demographics, insurance, and episode information.

Returns full patient profile including:
- Personal information (name, DOB, address, contacts)
- Emergency contacts and caregivers
- Insurance coverage
- Current episode details (SOC date, referring physician, admission reason)""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID (e.g., PT-10001)"
                        }
                    },
                    "required": ["patient_id"]
                }
            ),
            Tool(
                name="update_demographics",
                description="""Request a demographics update.

Creates a change request for review. Demographics changes require verification.
Specify the field path (e.g., 'address.phone_home') and new value.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "field": {
                            "type": "string",
                            "description": "Field to update (e.g., 'phone_home', 'address.street')"
                        },
                        "value": {
                            "type": "string",
                            "description": "New value for the field"
                        }
                    },
                    "required": ["patient_id", "field", "value"]
                }
            )
        ]

    @server.call_tool()
    async def call_demographics_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "get_demographics":
                result = api.get_demographics(arguments["patient_id"])
                demo = result["demographics"]
                ins = result["insurance"]
                ep = result["episode"]

                output = f"# Patient Demographics: {demo['first_name']} {demo['last_name']}\n\n"
                output += f"**Patient ID:** {result['patient_id']}\n\n"

                output += "## Personal Information\n"
                output += f"- **Name:** {demo['first_name']} {demo['last_name']}"
                if demo.get("preferred_name"):
                    output += f" (goes by {demo['preferred_name']})"
                output += "\n"
                output += f"- **DOB:** {demo['dob']} (Age {demo['age']})\n"
                output += f"- **Gender:** {demo['gender']}\n"
                output += f"- **Language:** {demo.get('language', 'English')}\n"
                output += f"- **Marital Status:** {demo.get('marital_status', 'Unknown')}\n\n"

                output += "## Contact Information\n"
                addr = demo["address"]
                output += f"- **Address:** {addr['street']}"
                if addr.get("unit"):
                    output += f" {addr['unit']}"
                output += f"\n  {addr['city']}, {addr['state']} {addr['zip']}\n"
                if addr.get("directions"):
                    output += f"- **Directions:** {addr['directions']}\n"
                if demo.get("phone_home"):
                    output += f"- **Home Phone:** {demo['phone_home']}\n"
                if demo.get("phone_cell"):
                    output += f"- **Cell Phone:** {demo['phone_cell']}\n"
                output += "\n"

                if demo.get("emergency_contact"):
                    ec = demo["emergency_contact"]
                    output += "## Emergency Contact\n"
                    output += f"- **Name:** {ec['name']} ({ec['relationship']})\n"
                    output += f"- **Phone:** {ec['phone']}\n"
                    if ec.get("is_poa"):
                        output += "- **POA:** Yes\n"
                    output += "\n"

                if demo.get("caregiver"):
                    cg = demo["caregiver"]
                    output += "## Caregiver\n"
                    output += f"- **Name:** {cg['name']} ({cg['relationship']})\n"
                    output += f"- **Phone:** {cg['phone']}\n"
                    if cg.get("availability"):
                        output += f"- **Availability:** {cg['availability']}\n"
                    output += "\n"

                output += "## Insurance\n"
                if ins.get("primary"):
                    output += f"- **Primary:** {ins['primary']['payer']} - {ins['primary']['plan']}\n"
                    output += f"  Member ID: {ins['primary']['member_id']}\n"
                if ins.get("secondary"):
                    output += f"- **Secondary:** {ins['secondary']['payer']} - {ins['secondary']['plan']}\n"
                    output += f"  Member ID: {ins['secondary']['member_id']}\n"
                output += "\n"

                output += "## Current Episode\n"
                output += f"- **Episode ID:** {ep['episode_id']}\n"
                output += f"- **SOC Date:** {ep['soc_date']}\n"
                output += f"- **Cert Period:** {ep['certification_period']['start']} to {ep['certification_period']['end']}\n"
                output += f"- **Referral:** {ep['referral_source']}\n"
                output += f"- **Referring MD:** {ep['referring_physician']['name']} ({ep['referring_physician']['specialty']})\n"
                output += f"- **Admission Reason:** {ep['admission_reason']}\n"
                output += f"- **Status:** {ep['status']}\n"

                return [TextContent(type="text", text=output)]

            elif name == "update_demographics":
                result = api.update_demographics(
                    patient_id=arguments["patient_id"],
                    field=arguments["field"],
                    value=arguments["value"]
                )
                output = f"📝 **Demographics Change Request**\n\n"
                output += f"- Status: {result['status']}\n"
                output += f"- Patient: {result['patient_id']}\n"
                output += f"- Field: {result['field']}\n"
                output += f"- Current Value: {result['current_value']}\n"
                output += f"- Proposed Value: {result['proposed_value']}\n\n"
                output += f"_{result['message']}_"
                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
