"""
Medications MCP Tools
Medication management with allergy checking and interaction warnings
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_medications_tools(server: Server, api: PointCareMockAPI):
    """Register medications tools with the MCP server"""

    @server.list_tools()
    async def list_medications_tools() -> list[Tool]:
        return [
            Tool(
                name="get_medications",
                description="""Get patient medication list.

Returns active and discontinued medications with full details including:
- Medication name, dose, route, frequency
- Purpose and prescriber
- Patient allergies for reference""",
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
                name="validate_medications",
                description="""Validate/attest medication list during visit.

Documents that medications were reviewed with patient.
Pass medication IDs that were verified as currently being taken.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Active visit session ID"
                        },
                        "medication_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of medication IDs to validate"
                        }
                    },
                    "required": ["session_id", "medication_ids"]
                }
            ),
            Tool(
                name="add_medication",
                description="""Add a new medication to patient's list.

Automatically checks for allergy interactions before adding.
Set override_warnings=true to add despite warnings.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "name": {
                            "type": "string",
                            "description": "Medication name"
                        },
                        "dose": {
                            "type": "string",
                            "description": "Dose (e.g., '10', '500')"
                        },
                        "unit": {
                            "type": "string",
                            "description": "Unit (e.g., 'mg', 'mcg', 'mL')"
                        },
                        "route": {
                            "type": "string",
                            "description": "Route of administration",
                            "enum": ["PO", "IV", "IM", "SQ", "SL", "PR", "TOP", "INH", "OPH", "OT", "NAS", "TD"]
                        },
                        "frequency": {
                            "type": "string",
                            "description": "Frequency (e.g., 'daily', 'BID', 'TID', 'PRN')"
                        },
                        "times": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Scheduled times (e.g., ['08:00', '20:00'])"
                        },
                        "purpose": {
                            "type": "string",
                            "description": "Reason for medication"
                        },
                        "prescriber": {
                            "type": "string",
                            "description": "Prescribing physician name"
                        },
                        "override_warnings": {
                            "type": "boolean",
                            "description": "Override allergy warnings",
                            "default": False
                        }
                    },
                    "required": ["patient_id", "name"]
                }
            ),
            Tool(
                name="discontinue_medication",
                description="""Discontinue a medication.

Marks medication as discontinued with reason and effective date.
Creates documentation for the change.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "med_id": {
                            "type": "string",
                            "description": "Medication ID to discontinue"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Reason for discontinuation"
                        },
                        "discontinue_date": {
                            "type": "string",
                            "description": "Effective date (YYYY-MM-DD). Defaults to today."
                        }
                    },
                    "required": ["patient_id", "med_id", "reason"]
                }
            )
        ]

    @server.call_tool()
    async def call_medications_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "get_medications":
                result = api.get_medications(arguments["patient_id"])

                output = f"# Medications for {result['patient_id']}\n\n"

                # Allergies first (important!)
                allergies = result.get("allergies", [])
                if allergies:
                    output += "## ⚠️ ALLERGIES\n"
                    for a in allergies:
                        severity_icon = "🔴" if a["severity"] == "severe" else "🟡"
                        output += f"- {severity_icon} **{a['allergen']}**: {a['reaction']} ({a['severity']})\n"
                    output += "\n"

                # Active medications
                output += f"## Active Medications ({result['active_count']})\n\n"
                for med in result["active_medications"]:
                    output += f"### {med['name']} {med.get('dose', '')} {med.get('unit', '')}\n"
                    output += f"- **ID:** {med['med_id']}\n"
                    output += f"- **Route:** {med.get('route', 'PO')} | **Frequency:** {med.get('frequency', 'N/A')}\n"
                    if med.get("times"):
                        output += f"- **Times:** {', '.join(med['times'])}\n"
                    if med.get("purpose"):
                        output += f"- **Purpose:** {med['purpose']}\n"
                    if med.get("prescriber"):
                        output += f"- **Prescriber:** {med['prescriber']}\n"
                    output += "\n"

                # Discontinued medications
                if result.get("discontinued_medications"):
                    output += "## Discontinued Medications\n"
                    for med in result["discontinued_medications"]:
                        output += f"- ~~{med['name']} {med.get('dose', '')} {med.get('unit', '')}~~ "
                        if med.get("discontinue_reason"):
                            output += f"(Reason: {med['discontinue_reason']})"
                        output += "\n"

                return [TextContent(type="text", text=output)]

            elif name == "validate_medications":
                result = api.validate_medications(
                    session_id=arguments["session_id"],
                    medication_ids=arguments["medication_ids"]
                )

                output = "## Medication Validation\n\n"
                output += f"✅ Validated {result['validated_count']} medications at {result['attestation_timestamp']}\n\n"

                for med in result["validated"]:
                    output += f"- ✅ {med['name']} ({med['med_id']})\n"

                if result.get("not_found"):
                    output += "\n⚠️ **Not found:** " + ", ".join(result["not_found"]) + "\n"

                return [TextContent(type="text", text=output)]

            elif name == "add_medication":
                result = api.add_medication(
                    patient_id=arguments["patient_id"],
                    medication={
                        "name": arguments["name"],
                        "dose": arguments.get("dose"),
                        "unit": arguments.get("unit"),
                        "route": arguments.get("route", "PO"),
                        "frequency": arguments.get("frequency"),
                        "times": arguments.get("times", []),
                        "purpose": arguments.get("purpose"),
                        "prescriber": arguments.get("prescriber"),
                        "override_warnings": arguments.get("override_warnings", False)
                    }
                )

                if result["status"] == "added":
                    output = f"✅ **Medication Added**\n\n"
                    output += f"- ID: {result['med_id']}\n"
                    output += f"- Name: {result['medication']['name']}\n"
                else:
                    output = f"🚫 **Medication Not Added**\n\n"
                    output += f"{result.get('message', 'See warnings below')}\n\n"

                if result.get("warnings"):
                    output += "\n⚠️ **Warnings:**\n"
                    for w in result["warnings"]:
                        output += f"- {w['message']}\n"

                return [TextContent(type="text", text=output)]

            elif name == "discontinue_medication":
                result = api.discontinue_medication(
                    patient_id=arguments["patient_id"],
                    med_id=arguments["med_id"],
                    reason=arguments["reason"],
                    discontinue_date=arguments.get("discontinue_date")
                )

                output = f"✅ **Medication Discontinued**\n\n"
                output += f"- Medication: {result['medication']}\n"
                output += f"- Reason: {result['reason']}\n"
                output += f"- Effective Date: {result['effective_date']}\n"

                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
