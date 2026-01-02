# Ratchet EMR - Claude Desktop Setup

## Option 1: Run Locally on Windows

### 1. Clone the repo
```powershell
git clone https://github.com/MatthewSnow2/ratchet-emr-demo.git
cd ratchet-emr-demo
```

### 2. Create virtual environment and install dependencies
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install mcp
```

### 3. Add to Claude Desktop config

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ratchet-emr": {
      "command": "C:/Users/YourUsername/path/to/ratchet-emr-demo/venv/Scripts/python.exe",
      "args": ["-m", "ratchet_server.server"],
      "cwd": "C:/Users/YourUsername/path/to/ratchet-emr-demo"
    }
  }
}
```

**Important:** Use forward slashes `/` in paths, not backslashes.

### 4. Restart Claude Desktop

The "ratchet-emr" server should appear in your MCP servers list.

---

## Option 2: Run on EC2 (Advanced)

For remote execution, you'll need to set up an SSE transport or tunnel. This requires additional configuration beyond stdio.

### SSH Tunnel Method (Quick)
```powershell
# On Windows, create SSH tunnel
ssh -L 3000:localhost:3000 ubuntu@your-ec2-ip

# On EC2, run server with HTTP transport (requires additional setup)
```

---

## Available Tools (20 total)

| Category | Tools |
|----------|-------|
| Visit Management | `search_patient`, `start_visit`, `complete_visit`, `get_visit_calendar` |
| Demographics | `get_demographics`, `update_demographics` |
| Vitals | `record_vitals`, `get_vital_trends` |
| Medications | `get_medications`, `validate_medications`, `add_medication`, `discontinue_medication` |
| Assessments | `get_assessment_questions`, `submit_assessment`, `get_care_plan` |
| Interventions | `get_active_interventions`, `document_intervention`, `update_goal_status` |
| Wounds | `get_wound_record`, `add_wound`, `document_wound_assessment` |
| Orders | `create_order` |
| Notes | `add_coordination_note`, `get_coordination_notes` |

## Test Patients

- **PT-10001**: Beth Morrison, 80F, CHF patient with 6 medications, 4 care plan goals
- **PT-10002**: Harold Jenkins, 72M, post-TKR with surgical wound tracking

## Example Workflow

1. Search for patient: `search_patient("Morrison")`
2. Start visit: `start_visit("PT-10001", "SN00")`
3. Record vitals: `record_vitals(session_id, {...})`
4. Document interventions: `document_intervention(session_id, "INT-001")`
5. Complete visit: `complete_visit(session_id)`
