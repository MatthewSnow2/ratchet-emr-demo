"""
Mock PointCare/HCHB API
Simulates the backend EMR system for development and testing
"""

import json
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pathlib import Path
import uuid


class PointCareMockAPI:
    """Mock API simulating AccentCare's HCHB/PointCare system"""

    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            # Default to mock_data directory relative to this file
            data_dir = Path(__file__).parent.parent.parent / "mock_data"
        self.data_dir = Path(data_dir)
        self._load_data()
        self._active_sessions: Dict[str, Dict[str, Any]] = {}

    def _load_data(self):
        """Load all mock data from JSON files"""
        with open(self.data_dir / "patients.json", "r") as f:
            data = json.load(f)
            self.patients = {p["patient_id"]: p for p in data["patients"]}

        with open(self.data_dir / "service_codes.json", "r") as f:
            data = json.load(f)
            self.service_codes = {sc["code"]: sc for sc in data["service_codes"]}
            self.visit_statuses = {vs["code"]: vs for vs in data["visit_statuses"]}
            self.disciplines = {d["code"]: d for d in data["disciplines"]}

        with open(self.data_dir / "icd10_codes.json", "r") as f:
            data = json.load(f)
            self.icd10_codes = {ic["code"]: ic for ic in data["icd10_codes"]}

        with open(self.data_dir / "medications.json", "r") as f:
            data = json.load(f)
            self.medications_db = {m["name"]: m for m in data["medications"]}
            self.routes = data["routes"]
            self.frequencies = data["frequencies"]

    def _save_patients(self):
        """Persist patient data back to JSON"""
        data = {
            "patients": list(self.patients.values()),
            "metadata": {
                "version": "1.0.0",
                "updated_at": datetime.now().isoformat(),
                "description": "Mock patient data for Ratchet EMR Demo"
            }
        }
        with open(self.data_dir / "patients.json", "w") as f:
            json.dump(data, f, indent=2)

    # ==================== Patient Search ====================

    def search_patients(
        self,
        query: str,
        search_type: str = "all",
        status: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for patients by name, ID, or phone"""
        results = []
        query_lower = query.lower()

        for patient in self.patients.values():
            match = False

            if search_type in ("all", "name"):
                full_name = f"{patient['demographics']['first_name']} {patient['demographics']['last_name']}"
                if query_lower in full_name.lower():
                    match = True

            if search_type in ("all", "id"):
                if query.upper() in patient["patient_id"].upper():
                    match = True

            if search_type in ("all", "phone"):
                phones = [
                    patient["demographics"].get("phone_home", ""),
                    patient["demographics"].get("phone_cell", "")
                ]
                if any(query in phone for phone in phones):
                    match = True

            if match:
                if status is None or patient["episode"]["status"] == status:
                    results.append(self._format_patient_summary(patient))

            if len(results) >= limit:
                break

        return results

    def _format_patient_summary(self, patient: Dict[str, Any]) -> Dict[str, Any]:
        """Format patient for search results"""
        demo = patient["demographics"]
        return {
            "patient_id": patient["patient_id"],
            "name": f"{demo['first_name']} {demo['last_name']}",
            "preferred_name": demo.get("preferred_name"),
            "dob": demo["dob"],
            "age": demo["age"],
            "gender": demo["gender"],
            "address": f"{demo['address']['city']}, {demo['address']['state']}",
            "phone": demo.get("phone_home") or demo.get("phone_cell"),
            "status": patient["episode"]["status"],
            "primary_diagnosis": patient["diagnoses"][0]["description"] if patient["diagnoses"] else None,
            "alerts_count": len([a for a in patient.get("alerts", []) if a["active"]])
        }

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get full patient record"""
        return self.patients.get(patient_id)

    # ==================== Visit Management ====================

    def start_visit(
        self,
        patient_id: str,
        service_code: str,
        visit_date: Optional[str] = None,
        clinician_id: str = "STH-001",
        clinician_name: str = "Stacey Thompson, RN"
    ) -> Dict[str, Any]:
        """Start a new visit session"""
        if patient_id not in self.patients:
            raise ValueError(f"Patient {patient_id} not found")

        if service_code not in self.service_codes:
            raise ValueError(f"Invalid service code: {service_code}")

        visit_date = visit_date or date.today().isoformat()
        session_id = f"VS-{uuid.uuid4().hex[:8].upper()}"
        visit_id = f"V-{visit_date.replace('-', '')}-{len(self.patients[patient_id]['visits']) + 1:03d}"

        session = {
            "session_id": session_id,
            "visit_id": visit_id,
            "patient_id": patient_id,
            "service_code": service_code,
            "service_code_description": self.service_codes[service_code]["description"],
            "date": visit_date,
            "clinician": {"id": clinician_id, "name": clinician_name},
            "time_in": datetime.now().strftime("%H:%M"),
            "time_out": None,
            "status": "in_progress",
            "vitals": {},
            "assessment_summary": {},
            "interventions_provided": [],
            "goals_addressed": [],
            "coordination_notes": [],
            "created_at": datetime.now().isoformat()
        }

        self._active_sessions[session_id] = session
        return {
            "session_id": session_id,
            "visit_id": visit_id,
            "patient_id": patient_id,
            "service_code": service_code,
            "time_in": session["time_in"],
            "message": f"Visit started for {self.patients[patient_id]['demographics']['first_name']} {self.patients[patient_id]['demographics']['last_name']}"
        }

    def complete_visit(
        self,
        session_id: str,
        disposition: str = "complete",
        next_visit_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Complete a visit session"""
        if session_id not in self._active_sessions:
            raise ValueError(f"Session {session_id} not found or already completed")

        session = self._active_sessions[session_id]
        session["time_out"] = datetime.now().strftime("%H:%M")
        session["status"] = "completed" if disposition == "complete" else disposition
        session["next_visit_scheduled"] = next_visit_date

        # Add visit to patient record
        patient = self.patients[session["patient_id"]]
        visit_record = {
            "visit_id": session["visit_id"],
            "service_code": session["service_code"],
            "service_code_description": session["service_code_description"],
            "date": session["date"],
            "clinician": session["clinician"],
            "time_in": session["time_in"],
            "time_out": session["time_out"],
            "status": session["status"],
            "vitals": session["vitals"],
            "assessment_summary": session["assessment_summary"],
            "interventions_provided": session["interventions_provided"],
            "goals_addressed": session["goals_addressed"],
            "coordination_notes": session["coordination_notes"],
            "next_visit_scheduled": next_visit_date
        }
        patient["visits"].append(visit_record)
        self._save_patients()

        del self._active_sessions[session_id]

        return {
            "visit_id": session["visit_id"],
            "status": session["status"],
            "time_in": session["time_in"],
            "time_out": session["time_out"],
            "duration_minutes": self._calculate_duration(session["time_in"], session["time_out"]),
            "sync_status": "pending",
            "message": "Visit completed and queued for sync"
        }

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get active visit session"""
        return self._active_sessions.get(session_id)

    def _calculate_duration(self, time_in: str, time_out: str) -> int:
        """Calculate visit duration in minutes"""
        t_in = datetime.strptime(time_in, "%H:%M")
        t_out = datetime.strptime(time_out, "%H:%M")
        return int((t_out - t_in).total_seconds() / 60)

    # ==================== Demographics ====================

    def get_demographics(self, patient_id: str) -> Dict[str, Any]:
        """Get patient demographics"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")
        return {
            "patient_id": patient_id,
            "demographics": patient["demographics"],
            "insurance": patient["insurance"],
            "episode": patient["episode"]
        }

    def update_demographics(
        self,
        patient_id: str,
        field: str,
        value: Any
    ) -> Dict[str, Any]:
        """Update a demographics field (creates change request)"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # In real system, this would create a change request for review
        return {
            "status": "change_request_created",
            "patient_id": patient_id,
            "field": field,
            "proposed_value": value,
            "current_value": self._get_nested_value(patient["demographics"], field),
            "message": "Demographics change request submitted for review"
        }

    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = path.split(".")
        for key in keys:
            if isinstance(obj, dict):
                obj = obj.get(key)
            else:
                return None
        return obj

    # ==================== Vitals ====================

    def record_vitals(
        self,
        session_id: str,
        vitals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Record vital signs for a visit"""
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        patient = self.patients[session["patient_id"]]

        # Validate against physician parameters
        validation_results = self._validate_vitals(patient, vitals)

        session["vitals"] = vitals

        return {
            "recorded": True,
            "vitals": vitals,
            "validation": validation_results,
            "alerts": [v for v in validation_results if v["status"] == "alert"]
        }

    def _validate_vitals(
        self,
        patient: Dict[str, Any],
        vitals: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Validate vitals against physician parameters"""
        results = []
        protocols = patient.get("physician_protocols", [])

        # Find vital sign parameter protocol
        vs_protocol = next(
            (p for p in protocols if "Vital Sign" in p.get("protocol", "")),
            None
        )

        if vs_protocol:
            instructions = vs_protocol.get("instructions", "")

            # Check BP
            if "blood_pressure_systolic" in vitals:
                bp_sys = vitals["blood_pressure_systolic"]
                bp_dia = vitals.get("blood_pressure_diastolic", 0)

                if bp_sys > 160 or bp_dia > 100:
                    results.append({
                        "vital": "blood_pressure",
                        "value": f"{bp_sys}/{bp_dia}",
                        "status": "alert",
                        "message": "BP above threshold - notify MD per protocol"
                    })
                elif bp_sys < 90 or bp_dia < 60:
                    results.append({
                        "vital": "blood_pressure",
                        "value": f"{bp_sys}/{bp_dia}",
                        "status": "alert",
                        "message": "BP below threshold - notify MD per protocol"
                    })
                else:
                    results.append({
                        "vital": "blood_pressure",
                        "value": f"{bp_sys}/{bp_dia}",
                        "status": "normal",
                        "message": "Within parameters"
                    })

            # Check HR
            if "heart_rate" in vitals:
                hr = vitals["heart_rate"]
                if hr > 100:
                    results.append({
                        "vital": "heart_rate",
                        "value": hr,
                        "status": "alert",
                        "message": "HR above 100 - notify MD per protocol"
                    })
                elif hr < 50:
                    results.append({
                        "vital": "heart_rate",
                        "value": hr,
                        "status": "alert",
                        "message": "HR below 50 - notify MD per protocol"
                    })
                else:
                    results.append({
                        "vital": "heart_rate",
                        "value": hr,
                        "status": "normal",
                        "message": "Within parameters"
                    })

            # Check O2 Sat
            if "oxygen_saturation" in vitals:
                o2 = vitals["oxygen_saturation"]
                if o2 < 92:
                    results.append({
                        "vital": "oxygen_saturation",
                        "value": o2,
                        "status": "alert",
                        "message": "O2 Sat below 92% - notify MD per protocol"
                    })
                else:
                    results.append({
                        "vital": "oxygen_saturation",
                        "value": o2,
                        "status": "normal",
                        "message": "Within parameters"
                    })

        # Check weight for CHF patients
        chf_protocol = next(
            (p for p in protocols if "Weight" in p.get("protocol", "")),
            None
        )

        if chf_protocol and "weight" in vitals:
            # Get previous weight
            prev_visits = patient.get("visits", [])
            if prev_visits:
                last_weight = prev_visits[-1].get("vitals", {}).get("weight")
                if last_weight:
                    weight_change = vitals["weight"] - last_weight
                    if weight_change > 2:
                        results.append({
                            "vital": "weight",
                            "value": vitals["weight"],
                            "status": "alert",
                            "message": f"Weight gain of {weight_change:.1f} lbs since last visit - notify MD per CHF protocol"
                        })
                    else:
                        results.append({
                            "vital": "weight",
                            "value": vitals["weight"],
                            "status": "normal",
                            "message": f"Weight change: {weight_change:+.1f} lbs from last visit"
                        })

        return results

    def get_vital_trends(
        self,
        patient_id: str,
        vital_type: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get vital sign trends for a patient"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        trends = []
        vital_key_map = {
            "bp": ["blood_pressure_systolic", "blood_pressure_diastolic"],
            "blood_pressure": ["blood_pressure_systolic", "blood_pressure_diastolic"],
            "hr": ["heart_rate"],
            "heart_rate": ["heart_rate"],
            "weight": ["weight"],
            "temp": ["temperature"],
            "temperature": ["temperature"],
            "o2": ["oxygen_saturation"],
            "oxygen_saturation": ["oxygen_saturation"],
            "pain": ["pain_level"]
        }

        keys = vital_key_map.get(vital_type.lower(), [vital_type])

        for visit in reversed(patient.get("visits", [])[-limit:]):
            vitals = visit.get("vitals", {})
            if any(k in vitals for k in keys):
                entry = {"date": visit["date"], "visit_id": visit["visit_id"]}
                for k in keys:
                    if k in vitals:
                        entry[k] = vitals[k]
                trends.append(entry)

        return {
            "patient_id": patient_id,
            "vital_type": vital_type,
            "data_points": len(trends),
            "trends": trends
        }

    # ==================== Medications ====================

    def get_medications(self, patient_id: str) -> Dict[str, Any]:
        """Get patient medication list"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        meds = patient.get("medications", [])
        active = [m for m in meds if m.get("status") == "active"]
        discontinued = [m for m in meds if m.get("status") == "discontinued"]

        return {
            "patient_id": patient_id,
            "active_count": len(active),
            "active_medications": active,
            "discontinued_medications": discontinued,
            "allergies": patient.get("allergies", [])
        }

    def validate_medications(
        self,
        session_id: str,
        medication_ids: List[str]
    ) -> Dict[str, Any]:
        """Validate/attest medications during visit"""
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        patient = self.patients[session["patient_id"]]
        meds = {m["med_id"]: m for m in patient.get("medications", [])}

        validated = []
        not_found = []

        for med_id in medication_ids:
            if med_id in meds:
                validated.append({
                    "med_id": med_id,
                    "name": meds[med_id]["name"],
                    "validated": True
                })
            else:
                not_found.append(med_id)

        return {
            "session_id": session_id,
            "validated_count": len(validated),
            "validated": validated,
            "not_found": not_found,
            "attestation_timestamp": datetime.now().isoformat()
        }

    def add_medication(
        self,
        patient_id: str,
        medication: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a new medication (checks for interactions)"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # Check for allergy interactions
        allergies = [a["allergen"].lower() for a in patient.get("allergies", [])]
        med_name = medication.get("name", "").lower()

        warnings = []
        if any(allergy in med_name for allergy in allergies):
            warnings.append({
                "type": "allergy",
                "severity": "high",
                "message": f"ALLERGY ALERT: Patient allergic to component in {medication['name']}"
            })

        # Generate med ID
        existing_ids = [m["med_id"] for m in patient.get("medications", [])]
        new_id = f"MED-{len(existing_ids) + 1:03d}"

        new_med = {
            "med_id": new_id,
            "name": medication["name"],
            "dose": medication.get("dose"),
            "unit": medication.get("unit"),
            "route": medication.get("route", "PO"),
            "frequency": medication.get("frequency"),
            "times": medication.get("times", []),
            "purpose": medication.get("purpose"),
            "prescriber": medication.get("prescriber"),
            "start_date": date.today().isoformat(),
            "status": "active"
        }

        if not warnings or medication.get("override_warnings"):
            patient["medications"].append(new_med)
            self._save_patients()
            return {
                "status": "added",
                "med_id": new_id,
                "medication": new_med,
                "warnings": warnings
            }
        else:
            return {
                "status": "blocked",
                "med_id": None,
                "warnings": warnings,
                "message": "Medication not added due to warnings. Set override_warnings=true to proceed."
            }

    def discontinue_medication(
        self,
        patient_id: str,
        med_id: str,
        reason: str,
        discontinue_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Discontinue a medication"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        for med in patient.get("medications", []):
            if med["med_id"] == med_id:
                med["status"] = "discontinued"
                med["end_date"] = discontinue_date or date.today().isoformat()
                med["discontinue_reason"] = reason
                self._save_patients()
                return {
                    "status": "discontinued",
                    "med_id": med_id,
                    "medication": med["name"],
                    "reason": reason,
                    "effective_date": med["end_date"]
                }

        raise ValueError(f"Medication {med_id} not found for patient {patient_id}")

    # ==================== Interventions & Goals ====================

    def get_active_interventions(self, patient_id: str) -> Dict[str, Any]:
        """Get active interventions with linked goals"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        care_plan = patient.get("care_plan", {})
        problem_statements = care_plan.get("problem_statements", [])

        interventions = []
        goals = []

        for ps in problem_statements:
            for intervention in ps.get("interventions", []):
                interventions.append({
                    **intervention,
                    "problem_statement_id": ps["ps_id"],
                    "pathway": ps["pathway"]
                })
            for goal in ps.get("goals", []):
                goals.append({
                    **goal,
                    "problem_statement_id": ps["ps_id"],
                    "pathway": ps["pathway"]
                })

        return {
            "patient_id": patient_id,
            "intervention_count": len(interventions),
            "interventions": interventions,
            "goal_count": len(goals),
            "goals": goals,
            "goals_met": len([g for g in goals if g.get("status") == "met"]),
            "goals_in_progress": len([g for g in goals if g.get("status") == "in_progress"])
        }

    def document_intervention(
        self,
        session_id: str,
        intervention_id: str,
        provided: bool = True,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Document that an intervention was provided"""
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session["interventions_provided"].append({
            "intervention_id": intervention_id,
            "provided": provided,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })

        return {
            "documented": True,
            "intervention_id": intervention_id,
            "provided": provided
        }

    def update_goal_status(
        self,
        session_id: str,
        goal_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update goal progress during visit"""
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        session["goals_addressed"].append({
            "goal_id": goal_id,
            "status": status,
            "notes": notes,
            "timestamp": datetime.now().isoformat()
        })

        # If goal is met, update the patient record
        if status == "met":
            patient = self.patients[session["patient_id"]]
            for ps in patient.get("care_plan", {}).get("problem_statements", []):
                for goal in ps.get("goals", []):
                    if goal["goal_id"] == goal_id:
                        goal["status"] = "met"
                        goal["met_date"] = date.today().isoformat()
                        self._save_patients()

        return {
            "updated": True,
            "goal_id": goal_id,
            "new_status": status
        }

    # ==================== Physical Assessment ====================

    def get_assessment_questions(
        self,
        patient_id: str,
        category: str
    ) -> Dict[str, Any]:
        """Get assessment questions with previous answers"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        # Get previous assessment for this category
        prev_assessment = None
        for visit in reversed(patient.get("visits", [])):
            if category in visit.get("assessment_summary", {}):
                prev_assessment = visit["assessment_summary"][category]
                break

        # Assessment categories and their questions
        categories = {
            "cardiovascular": {
                "questions": [
                    {"id": "cv1", "text": "Heart sounds", "type": "select", "options": ["S1S2 regular rate", "S1S2 irregular", "Murmur present", "S3 gallop", "S4 gallop"]},
                    {"id": "cv2", "text": "Pedal edema", "type": "select", "options": ["None", "Trace", "+1", "+2", "+3", "+4"]},
                    {"id": "cv3", "text": "JVD present", "type": "boolean"},
                    {"id": "cv4", "text": "Chest pain", "type": "boolean"},
                    {"id": "cv5", "text": "Additional findings", "type": "text"}
                ]
            },
            "respiratory": {
                "questions": [
                    {"id": "resp1", "text": "Lung sounds", "type": "select", "options": ["Clear throughout", "Diminished bases", "Crackles", "Wheezes", "Rhonchi"]},
                    {"id": "resp2", "text": "Dyspnea", "type": "select", "options": ["None", "With exertion", "At rest", "Orthopnea"]},
                    {"id": "resp3", "text": "Cough present", "type": "boolean"},
                    {"id": "resp4", "text": "Oxygen in use", "type": "boolean"},
                    {"id": "resp5", "text": "Additional findings", "type": "text"}
                ]
            },
            "neurological": {
                "questions": [
                    {"id": "neuro1", "text": "Level of consciousness", "type": "select", "options": ["Alert", "Lethargic", "Obtunded", "Unresponsive"]},
                    {"id": "neuro2", "text": "Orientation", "type": "multiselect", "options": ["Person", "Place", "Time", "Situation"]},
                    {"id": "neuro3", "text": "Speech", "type": "select", "options": ["Clear", "Slurred", "Aphasia"]},
                    {"id": "neuro4", "text": "Pupils", "type": "select", "options": ["PERRLA", "Unequal", "Non-reactive"]},
                    {"id": "neuro5", "text": "Additional findings", "type": "text"}
                ]
            },
            "integumentary": {
                "questions": [
                    {"id": "skin1", "text": "Skin integrity", "type": "select", "options": ["Intact", "Impaired"]},
                    {"id": "skin2", "text": "Color", "type": "select", "options": ["Normal", "Pale", "Cyanotic", "Jaundiced", "Flushed"]},
                    {"id": "skin3", "text": "Turgor", "type": "select", "options": ["Normal", "Decreased", "Tenting"]},
                    {"id": "skin4", "text": "Wounds present", "type": "boolean"},
                    {"id": "skin5", "text": "Additional findings", "type": "text"}
                ]
            },
            "gastrointestinal": {
                "questions": [
                    {"id": "gi1", "text": "Bowel sounds", "type": "select", "options": ["Normal", "Hyperactive", "Hypoactive", "Absent"]},
                    {"id": "gi2", "text": "Abdomen", "type": "select", "options": ["Soft, non-tender", "Distended", "Tender", "Rigid"]},
                    {"id": "gi3", "text": "Last bowel movement", "type": "text"},
                    {"id": "gi4", "text": "Nausea/vomiting", "type": "boolean"},
                    {"id": "gi5", "text": "Additional findings", "type": "text"}
                ]
            },
            "genitourinary": {
                "questions": [
                    {"id": "gu1", "text": "Voiding pattern", "type": "select", "options": ["Normal", "Frequency", "Urgency", "Incontinence", "Retention"]},
                    {"id": "gu2", "text": "Catheter present", "type": "boolean"},
                    {"id": "gu3", "text": "Urine characteristics", "type": "select", "options": ["Clear yellow", "Dark", "Cloudy", "Bloody"]},
                    {"id": "gu4", "text": "Additional findings", "type": "text"}
                ]
            },
            "musculoskeletal": {
                "questions": [
                    {"id": "msk1", "text": "ROM limitations", "type": "text"},
                    {"id": "msk2", "text": "Strength", "type": "select", "options": ["5/5 all extremities", "Weakness present", "Paralysis"]},
                    {"id": "msk3", "text": "Gait", "type": "select", "options": ["Steady", "Unsteady", "Uses assistive device", "Non-ambulatory"]},
                    {"id": "msk4", "text": "Fall risk", "type": "select", "options": ["Low", "Moderate", "High"]},
                    {"id": "msk5", "text": "Additional findings", "type": "text"}
                ]
            }
        }

        if category not in categories:
            raise ValueError(f"Invalid category: {category}. Valid: {list(categories.keys())}")

        return {
            "patient_id": patient_id,
            "category": category,
            "questions": categories[category]["questions"],
            "previous_assessment": prev_assessment
        }

    def submit_assessment(
        self,
        session_id: str,
        category: str,
        responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Submit assessment responses"""
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Format as narrative summary
        summary = responses.get("narrative") or responses.get("summary") or str(responses)

        session["assessment_summary"][category] = summary

        return {
            "recorded": True,
            "category": category,
            "session_id": session_id
        }

    # ==================== Wounds ====================

    def get_wound_record(self, patient_id: str) -> Dict[str, Any]:
        """Get active wounds for a patient"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        wounds = patient.get("wounds", [])
        active_wounds = [w for w in wounds if w.get("status") == "active"]

        return {
            "patient_id": patient_id,
            "active_wound_count": len(active_wounds),
            "wounds": active_wounds
        }

    def add_wound(
        self,
        patient_id: str,
        location: str,
        wound_type: str,
        onset_date: str
    ) -> Dict[str, Any]:
        """Add a new wound to track"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        if "wounds" not in patient:
            patient["wounds"] = []

        wound_id = f"W-{len(patient['wounds']) + 1:03d}"

        wound = {
            "wound_id": wound_id,
            "type": wound_type,
            "location": location,
            "onset_date": onset_date,
            "status": "active",
            "measurements": {},
            "characteristics": {},
            "assessments": []
        }

        patient["wounds"].append(wound)
        self._save_patients()

        return {
            "wound_id": wound_id,
            "status": "created",
            "wound": wound
        }

    def document_wound_assessment(
        self,
        session_id: str,
        wound_id: str,
        measurements: Dict[str, float],
        attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Document wound assessment during visit"""
        session = self._active_sessions.get(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        patient = self.patients[session["patient_id"]]

        for wound in patient.get("wounds", []):
            if wound["wound_id"] == wound_id:
                wound["measurements"] = measurements
                wound["characteristics"] = attributes
                wound["last_assessment_date"] = date.today().isoformat()

                # Calculate simple WAT score (0-5 scale, lower is better)
                wat_score = 0
                if measurements.get("length_cm", 0) > 5:
                    wat_score += 1
                if measurements.get("depth_cm", 0) > 0.5:
                    wat_score += 1
                if attributes.get("drainage") and attributes["drainage"] != "None":
                    wat_score += 1
                if attributes.get("infection_signs"):
                    wat_score += 2

                self._save_patients()

                return {
                    "documented": True,
                    "wound_id": wound_id,
                    "wat_score": wat_score,
                    "measurements": measurements
                }

        raise ValueError(f"Wound {wound_id} not found")

    # ==================== Orders ====================

    def create_order(
        self,
        patient_id: str,
        order_type: str,
        physician_id: str,
        instructions: str,
        effective_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new order"""
        valid_types = ["physician", "poc_update", "discharge", "hospital_hold", "roc"]
        if order_type not in valid_types:
            raise ValueError(f"Invalid order type. Valid: {valid_types}")

        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        order = {
            "order_id": order_id,
            "order_type": order_type,
            "patient_id": patient_id,
            "physician_id": physician_id,
            "instructions": instructions,
            "effective_date": effective_date or date.today().isoformat(),
            "created_at": datetime.now().isoformat(),
            "status": "pending_signature"
        }

        return {
            "order_id": order_id,
            "status": "created",
            "order": order,
            "message": "Order created and queued for physician signature"
        }

    # ==================== Coordination Notes ====================

    def add_coordination_note(
        self,
        patient_id: str,
        note_type: str,
        content: str,
        author: str = "Stacey Thompson, RN"
    ) -> Dict[str, Any]:
        """Add a coordination note"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        note_id = f"NOTE-{uuid.uuid4().hex[:8].upper()}"

        note = {
            "note_id": note_id,
            "type": note_type,
            "content": content,
            "author": author,
            "created_at": datetime.now().isoformat()
        }

        return {
            "note_id": note_id,
            "status": "created",
            "note": note
        }

    def get_coordination_notes(
        self,
        patient_id: str,
        note_type: Optional[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get coordination notes for a patient"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        all_notes = []

        # Collect notes from visits
        for visit in patient.get("visits", []):
            for note in visit.get("coordination_notes", []):
                all_notes.append({
                    **note,
                    "visit_id": visit["visit_id"],
                    "visit_date": visit["date"]
                })

        # Filter by type if specified
        if note_type:
            all_notes = [n for n in all_notes if n.get("type") == note_type]

        # Sort by date descending and limit
        all_notes.sort(key=lambda x: x.get("visit_date", ""), reverse=True)

        return {
            "patient_id": patient_id,
            "note_count": len(all_notes[:limit]),
            "notes": all_notes[:limit]
        }

    # ==================== Care Plan ====================

    def get_care_plan(self, patient_id: str) -> Dict[str, Any]:
        """Get full care plan including POC 485 data"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        return {
            "patient_id": patient_id,
            "care_plan": patient.get("care_plan", {}),
            "diagnoses": patient.get("diagnoses", []),
            "alerts": patient.get("alerts", []),
            "physician_protocols": patient.get("physician_protocols", [])
        }

    def get_visit_calendar(
        self,
        patient_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get scheduled visits for a patient"""
        patient = self.patients.get(patient_id)
        if not patient:
            raise ValueError(f"Patient {patient_id} not found")

        visits = patient.get("visits", [])

        # In a real system, this would include future scheduled visits
        # For mock, we'll just return completed visits and next scheduled

        last_visit = visits[-1] if visits else None
        next_scheduled = last_visit.get("next_visit_scheduled") if last_visit else None

        return {
            "patient_id": patient_id,
            "completed_visits": len(visits),
            "visit_history": [
                {
                    "visit_id": v["visit_id"],
                    "date": v["date"],
                    "service_code": v["service_code"],
                    "status": v["status"]
                }
                for v in visits
            ],
            "next_scheduled": next_scheduled
        }
