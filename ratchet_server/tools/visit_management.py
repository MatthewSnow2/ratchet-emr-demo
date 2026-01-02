"""
Visit Management MCP Tools
Handles visit lifecycle: start, complete, search patients
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_visit_tools(server: Server, api: PointCareMockAPI):
    """Register visit management tools with the MCP server"""

    @server.list_tools()
    async def list_visit_tools() -> list[Tool]:
        return [
            Tool(
                name="search_patient",
                description="""Search for patients in PointCare EMR.

Search by name, patient ID (PT-#####), or phone number.
Returns patient summaries with demographics and status.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search term (name, ID, or phone)"
                        },
                        "search_type": {
                            "type": "string",
                            "enum": ["all", "name", "id", "phone"],
                            "description": "Type of search to perform",
                            "default": "all"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "inactive", "discharged", "pending"],
                            "description": "Filter by patient status"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 10
                        }
                    },
                    "required": ["query"]
                }
            ),
            Tool(
                name="start_visit",
                description="""Start a new patient visit.

Initiates a visit session, starts time tracking, and returns a session ID
for documenting the visit. Required before documenting vitals, assessments, etc.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID (e.g., PT-10001)"
                        },
                        "service_code": {
                            "type": "string",
                            "description": "Service code (e.g., SN11, SN00, PT01)",
                            "enum": ["SN00", "SN01", "SN04", "SN11", "ROC", "D/C", "PT00", "PT01", "PT11", "OT01", "OT11", "ST01", "ST11", "HHA", "MSW01", "MSW11"]
                        },
                        "visit_date": {
                            "type": "string",
                            "description": "Visit date (YYYY-MM-DD). Defaults to today."
                        }
                    },
                    "required": ["patient_id", "service_code"]
                }
            ),
            Tool(
                name="complete_visit",
                description="""Complete a visit session.

Ends the visit, records time out, and syncs documentation.
Use after all visit documentation is complete.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Visit session ID from start_visit"
                        },
                        "disposition": {
                            "type": "string",
                            "enum": ["complete", "incomplete", "missed", "rescheduled"],
                            "description": "Visit completion status",
                            "default": "complete"
                        },
                        "next_visit_date": {
                            "type": "string",
                            "description": "Next scheduled visit date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_visit_calendar",
                description="""Get visit history and upcoming visits for a patient.

Returns completed visits and next scheduled visit date.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Filter from date (YYYY-MM-DD)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Filter to date (YYYY-MM-DD)"
                        }
                    },
                    "required": ["patient_id"]
                }
            )
        ]

    @server.call_tool()
    async def call_visit_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "search_patient":
                result = api.search_patients(
                    query=arguments["query"],
                    search_type=arguments.get("search_type", "all"),
                    status=arguments.get("status"),
                    limit=arguments.get("limit", 10)
                )
                if not result:
                    return [TextContent(type="text", text="No patients found matching your search.")]

                output = f"Found {len(result)} patient(s):\n\n"
                for p in result:
                    alerts = f" ⚠️ {p['alerts_count']} alerts" if p.get('alerts_count', 0) > 0 else ""
                    output += f"**{p['name']}** ({p['patient_id']}){alerts}\n"
                    output += f"  DOB: {p['dob']} | Age: {p['age']} | {p['gender']}\n"
                    output += f"  Status: {p['status']} | {p['address']}\n"
                    output += f"  Primary Dx: {p.get('primary_diagnosis', 'N/A')}\n\n"
                return [TextContent(type="text", text=output)]

            elif name == "start_visit":
                result = api.start_visit(
                    patient_id=arguments["patient_id"],
                    service_code=arguments["service_code"],
                    visit_date=arguments.get("visit_date")
                )
                output = f"✅ **Visit Started**\n\n"
                output += f"- Session ID: `{result['session_id']}`\n"
                output += f"- Visit ID: {result['visit_id']}\n"
                output += f"- Patient: {result['patient_id']}\n"
                output += f"- Service Code: {result['service_code']}\n"
                output += f"- Time In: {result['time_in']}\n\n"
                output += f"_{result['message']}_\n\n"
                output += "**Use this session_id for all visit documentation.**"
                return [TextContent(type="text", text=output)]

            elif name == "complete_visit":
                result = api.complete_visit(
                    session_id=arguments["session_id"],
                    disposition=arguments.get("disposition", "complete"),
                    next_visit_date=arguments.get("next_visit_date")
                )
                output = f"✅ **Visit Completed**\n\n"
                output += f"- Visit ID: {result['visit_id']}\n"
                output += f"- Status: {result['status']}\n"
                output += f"- Time In: {result['time_in']}\n"
                output += f"- Time Out: {result['time_out']}\n"
                output += f"- Duration: {result['duration_minutes']} minutes\n"
                output += f"- Sync Status: {result['sync_status']}\n\n"
                output += f"_{result['message']}_"
                return [TextContent(type="text", text=output)]

            elif name == "get_visit_calendar":
                result = api.get_visit_calendar(
                    patient_id=arguments["patient_id"],
                    start_date=arguments.get("start_date"),
                    end_date=arguments.get("end_date")
                )
                output = f"**Visit Calendar for {result['patient_id']}**\n\n"
                output += f"Completed Visits: {result['completed_visits']}\n"
                if result.get("next_scheduled"):
                    output += f"Next Scheduled: {result['next_scheduled']}\n"
                output += "\n**Visit History:**\n"
                for v in result.get("visit_history", []):
                    output += f"- {v['date']} | {v['service_code']} | {v['status']}\n"
                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
