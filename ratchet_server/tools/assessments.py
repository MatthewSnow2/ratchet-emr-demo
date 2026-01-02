"""
Physical Assessment MCP Tools
Body system assessments with OASIS integration
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_assessment_tools(server: Server, api: PointCareMockAPI):
    """Register assessment tools with the MCP server"""

    @server.list_tools()
    async def list_assessment_tools() -> list[Tool]:
        return [
            Tool(
                name="get_assessment_questions",
                description="""Get assessment questions for a body system category.

Returns structured questions with previous assessment data for comparison.
Categories: respiratory, cardiovascular, neurological, gastrointestinal,
genitourinary, musculoskeletal, integumentary.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "category": {
                            "type": "string",
                            "description": "Assessment category",
                            "enum": ["respiratory", "cardiovascular", "neurological", "gastrointestinal", "genitourinary", "musculoskeletal", "integumentary"]
                        }
                    },
                    "required": ["patient_id", "category"]
                }
            ),
            Tool(
                name="submit_assessment",
                description="""Submit physical assessment findings.

Records assessment responses for a body system. Can provide structured
responses or a narrative summary.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Active visit session ID"
                        },
                        "category": {
                            "type": "string",
                            "description": "Assessment category",
                            "enum": ["respiratory", "cardiovascular", "neurological", "gastrointestinal", "genitourinary", "musculoskeletal", "integumentary"]
                        },
                        "narrative": {
                            "type": "string",
                            "description": "Narrative assessment summary"
                        },
                        "responses": {
                            "type": "object",
                            "description": "Structured question responses (question_id: answer)"
                        }
                    },
                    "required": ["session_id", "category"]
                }
            ),
            Tool(
                name="get_care_plan",
                description="""Get the patient's full care plan.

Returns POC 485 data, diagnoses, problem statements, goals,
interventions, alerts, and physician protocols.""",
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
            )
        ]

    @server.call_tool()
    async def call_assessment_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "get_assessment_questions":
                result = api.get_assessment_questions(
                    patient_id=arguments["patient_id"],
                    category=arguments["category"]
                )

                output = f"## {arguments['category'].title()} Assessment\n\n"

                if result.get("previous_assessment"):
                    output += f"**Previous Assessment:** {result['previous_assessment']}\n\n"

                output += "### Questions\n\n"
                for q in result["questions"]:
                    output += f"**{q['id']}. {q['text']}**\n"
                    if q["type"] == "select":
                        output += f"  Options: {', '.join(q['options'])}\n"
                    elif q["type"] == "multiselect":
                        output += f"  Select all that apply: {', '.join(q['options'])}\n"
                    elif q["type"] == "boolean":
                        output += f"  Yes/No\n"
                    elif q["type"] == "text":
                        output += f"  Free text response\n"
                    output += "\n"

                return [TextContent(type="text", text=output)]

            elif name == "submit_assessment":
                result = api.submit_assessment(
                    session_id=arguments["session_id"],
                    category=arguments["category"],
                    responses={
                        "narrative": arguments.get("narrative"),
                        **arguments.get("responses", {})
                    }
                )

                output = f"✅ **{arguments['category'].title()} Assessment Recorded**\n\n"
                output += f"Session: {result['session_id']}\n"

                return [TextContent(type="text", text=output)]

            elif name == "get_care_plan":
                result = api.get_care_plan(arguments["patient_id"])

                output = f"# Care Plan for {result['patient_id']}\n\n"

                # Alerts
                alerts = result.get("alerts", [])
                if alerts:
                    output += "## ⚠️ Active Alerts\n"
                    for alert in alerts:
                        if alert.get("active"):
                            icon = "🔴" if alert["priority"] == "high" else "🟡"
                            output += f"- {icon} **{alert['type'].upper()}:** {alert['message']}\n"
                    output += "\n"

                # Diagnoses
                output += "## Diagnoses\n"
                for dx in result.get("diagnoses", []):
                    primary = "⭐ " if dx.get("is_primary") else ""
                    output += f"- {primary}**{dx['icd10']}**: {dx['description']}\n"
                output += "\n"

                # POC 485
                poc = result.get("care_plan", {}).get("poc_485", {})
                if poc:
                    output += "## Plan of Care (485)\n"
                    output += f"- **Visit Frequency:**\n"
                    for discipline, freq in poc.get("visit_frequency", {}).items():
                        output += f"  - {discipline}: {freq}\n"
                    output += f"- **Nutritional Requirements:** {poc.get('nutritional_requirements', 'N/A')}\n"
                    output += f"- **Functional Limitations:** {', '.join(poc.get('functional_limitations', []))}\n"
                    output += f"- **Activities Permitted:** {', '.join(poc.get('activities_permitted', []))}\n"
                    output += f"- **Prognosis:** {poc.get('prognosis', 'N/A')}\n"
                    output += f"- **Safety Measures:** {', '.join(poc.get('safety_measures', []))}\n"
                    output += f"- **Discharge Plans:** {poc.get('discharge_plans', 'N/A')}\n\n"

                # Problem Statements with Goals and Interventions
                output += "## Problem Statements\n\n"
                for ps in result.get("care_plan", {}).get("problem_statements", []):
                    output += f"### {ps['pathway']}\n"
                    output += f"**Problem:** {ps['problem']}\n\n"

                    output += "**Goals:**\n"
                    for goal in ps.get("goals", []):
                        status_icon = "✅" if goal["status"] == "met" else "🔄"
                        output += f"- {status_icon} {goal['text']} (Target: {goal['target_date']})\n"

                    output += "\n**Interventions:**\n"
                    for int in ps.get("interventions", []):
                        output += f"- {int['text']} ({int['frequency']})\n"
                    output += "\n"

                # Physician Protocols
                protocols = result.get("physician_protocols", [])
                if protocols:
                    output += "## Physician Protocols\n"
                    for p in protocols:
                        output += f"- **{p['protocol']}**: {p['instructions']}\n"

                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
