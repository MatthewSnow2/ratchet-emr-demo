"""
Vitals MCP Tools
Record and track vital signs with physician parameter validation
"""

from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent

from ..mock_api import PointCareMockAPI


def register_vitals_tools(server: Server, api: PointCareMockAPI):
    """Register vitals tools with the MCP server"""

    @server.list_tools()
    async def list_vitals_tools() -> list[Tool]:
        return [
            Tool(
                name="record_vitals",
                description="""Record vital signs during a visit.

Automatically validates against physician-ordered parameters and alerts if out of range.
Supports: blood pressure, heart rate, respiratory rate, temperature, O2 saturation, weight, pain level.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Active visit session ID"
                        },
                        "blood_pressure_systolic": {
                            "type": "integer",
                            "description": "Systolic BP (mmHg)"
                        },
                        "blood_pressure_diastolic": {
                            "type": "integer",
                            "description": "Diastolic BP (mmHg)"
                        },
                        "heart_rate": {
                            "type": "integer",
                            "description": "Heart rate (bpm)"
                        },
                        "respiratory_rate": {
                            "type": "integer",
                            "description": "Respiratory rate (breaths/min)"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Temperature"
                        },
                        "temperature_unit": {
                            "type": "string",
                            "enum": ["F", "C"],
                            "description": "Temperature unit",
                            "default": "F"
                        },
                        "oxygen_saturation": {
                            "type": "integer",
                            "description": "O2 saturation (%)"
                        },
                        "weight": {
                            "type": "number",
                            "description": "Weight"
                        },
                        "weight_unit": {
                            "type": "string",
                            "enum": ["lbs", "kg"],
                            "description": "Weight unit",
                            "default": "lbs"
                        },
                        "pain_level": {
                            "type": "integer",
                            "description": "Pain level (0-10 scale)",
                            "minimum": 0,
                            "maximum": 10
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_vital_trends",
                description="""Get vital sign trends for a patient.

Returns historical vital sign data across visits for trend analysis.
Useful for monitoring CHF weight trends, BP control, etc.""",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID"
                        },
                        "vital_type": {
                            "type": "string",
                            "description": "Type of vital to trend",
                            "enum": ["bp", "blood_pressure", "hr", "heart_rate", "weight", "temp", "temperature", "o2", "oxygen_saturation", "pain"]
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of data points",
                            "default": 10
                        }
                    },
                    "required": ["patient_id", "vital_type"]
                }
            )
        ]

    @server.call_tool()
    async def call_vitals_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "record_vitals":
                session_id = arguments.pop("session_id")
                vitals = {k: v for k, v in arguments.items() if v is not None}

                result = api.record_vitals(session_id, vitals)

                output = "## Vital Signs Recorded\n\n"

                # Display recorded vitals
                v = result["vitals"]
                if "blood_pressure_systolic" in v:
                    output += f"- **Blood Pressure:** {v['blood_pressure_systolic']}/{v.get('blood_pressure_diastolic', '?')} mmHg\n"
                if "heart_rate" in v:
                    output += f"- **Heart Rate:** {v['heart_rate']} bpm\n"
                if "respiratory_rate" in v:
                    output += f"- **Respiratory Rate:** {v['respiratory_rate']} breaths/min\n"
                if "temperature" in v:
                    unit = v.get("temperature_unit", "F")
                    output += f"- **Temperature:** {v['temperature']}°{unit}\n"
                if "oxygen_saturation" in v:
                    output += f"- **O2 Saturation:** {v['oxygen_saturation']}%\n"
                if "weight" in v:
                    unit = v.get("weight_unit", "lbs")
                    output += f"- **Weight:** {v['weight']} {unit}\n"
                if "pain_level" in v:
                    output += f"- **Pain Level:** {v['pain_level']}/10\n"

                output += "\n### Validation Results\n\n"

                alerts = result.get("alerts", [])
                validations = result.get("validation", [])

                if alerts:
                    output += "⚠️ **ALERTS - ACTION REQUIRED:**\n"
                    for alert in alerts:
                        output += f"- **{alert['vital']}:** {alert['message']}\n"
                    output += "\n"

                for val in validations:
                    if val["status"] == "normal":
                        output += f"✅ {val['vital']}: {val['message']}\n"

                return [TextContent(type="text", text=output)]

            elif name == "get_vital_trends":
                result = api.get_vital_trends(
                    patient_id=arguments["patient_id"],
                    vital_type=arguments["vital_type"],
                    limit=arguments.get("limit", 10)
                )

                output = f"## {arguments['vital_type'].upper()} Trends for {result['patient_id']}\n\n"
                output += f"Data points: {result['data_points']}\n\n"

                if result["trends"]:
                    output += "| Date | Visit | Value |\n"
                    output += "|------|-------|-------|\n"
                    for t in result["trends"]:
                        # Format value based on vital type
                        if "blood_pressure_systolic" in t:
                            val = f"{t['blood_pressure_systolic']}/{t.get('blood_pressure_diastolic', '?')}"
                        else:
                            val = str(list(t.values())[2]) if len(t) > 2 else "N/A"
                        output += f"| {t['date']} | {t['visit_id']} | {val} |\n"
                else:
                    output += "No data available for this vital type.\n"

                return [TextContent(type="text", text=output)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            return [TextContent(type="text", text=f"Error: {str(e)}")]
