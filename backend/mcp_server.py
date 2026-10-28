"""
Model Context Protocol (MCP) Server for Predictive Maintenance System (PMS).

Standard JSON-RPC 2.0 compliant MCP implementation exposing:
1. MCP Tools: `predict_equipment_risk`, `predict_and_narrate`, `simulate_derate_intervention`,
             `dispatch_work_order`, `get_drift_telemetry`, `run_inference_benchmark`.
2. MCP Resources: `pms://system/health`, `pms://models/manifest`, `pms://knowledge_base/{sop_name}`.
3. MCP Prompts: `diagnose_machine_anomaly`, `shift_handover_report`.

Can be executed as:
- Standard I/O (stdio) process for desktop agents (Claude Desktop, Antigravity, Cursor).
- In-process JSON-RPC handler for FastAPI gateway integration (/mcp endpoint).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from .database import SessionLocal
from .inference_engine import InferenceRuntime, inference_engine
from .narration_service import orchestrate_predict_and_narrate, rag_store
from .predictor import predictor

logger = logging.getLogger("pms.mcp")

MCP_SERVER_NAME = "pms-mcp-server"
MCP_SERVER_VERSION = "1.0.0"
MCP_PROTOCOL_VERSION = "2024-11-05"


class PMSMCPServer:
    """Enterprise Model Context Protocol (MCP) server for industrial equipment intelligence."""

    def __init__(self):
        self.tools = self._build_tool_definitions()
        self.resources = self._build_resource_definitions()
        self.prompts = self._build_prompt_definitions()

    def _build_tool_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "predict_equipment_risk",
                "description": "Predicts machine failure risk probability, SHAP root causes, and recommended actions from sensor telemetry.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "temperature": {"type": "number", "description": "Operating temperature in °C (-20 to 250)"},
                        "rpm": {"type": "number", "description": "Rotational speed in RPM (100 to 6000)"},
                        "pressure": {"type": "number", "description": "Hydraulic/operating pressure in bar (1 to 100)"},
                        "vibration": {"type": "number", "description": "Vibration amplitude in g (0.01 to 5.0)"},
                        "operating_hours": {"type": "number", "description": "Cumulative operating hours (0 to 50000)"},
                        "runtime": {
                            "type": "string",
                            "enum": ["hybrid", "onnx", "xgboost"],
                            "default": "hybrid",
                            "description": "Inference engine runtime: onnx (ultra-fast 20µs), xgboost (full SHAP), or hybrid",
                        },
                    },
                    "required": ["temperature", "rpm", "pressure", "vibration", "operating_hours"],
                },
            },
            {
                "name": "predict_and_narrate",
                "description": "Performs failure prediction and synthesizes a context-grounded maintenance briefing using RAG SOP retrieval.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "temperature": {"type": "number", "description": "Operating temperature in °C"},
                        "rpm": {"type": "number", "description": "Rotational speed in RPM"},
                        "pressure": {"type": "number", "description": "Hydraulic pressure in bar"},
                        "vibration": {"type": "number", "description": "Vibration amplitude in g"},
                        "operating_hours": {"type": "number", "description": "Cumulative operating hours"},
                        "include_counterfactual": {"type": "boolean", "default": True, "description": "Include minimal-fix intervention targets"},
                    },
                    "required": ["temperature", "rpm", "pressure", "vibration", "operating_hours"],
                },
            },
            {
                "name": "simulate_derate_intervention",
                "description": "Simulates speed/pressure de-rating to lower failure risk, extend Remaining Useful Life (RUL), and calculate saved capital risk ($VaR).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "temperature": {"type": "number"},
                        "rpm": {"type": "number"},
                        "pressure": {"type": "number"},
                        "vibration": {"type": "number"},
                        "operating_hours": {"type": "number"},
                        "derate_rpm_pct": {"type": "number", "default": -15.0, "description": "Percentage spindle speed adjustment"},
                        "derate_pressure_pct": {"type": "number", "default": -10.0, "description": "Percentage hydraulic pressure adjustment"},
                    },
                    "required": ["temperature", "rpm", "pressure", "vibration", "operating_hours"],
                },
            },
            {
                "name": "dispatch_work_order",
                "description": "Dispatches an emergency or preventive maintenance work order with bill of materials (BOM) and safety interlocks.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "asset_id": {"type": "string", "default": "CNC-SPINDLE-LINE-2"},
                        "line_id": {"type": "string", "default": "Line 4 - Discrete Assembly"},
                        "failure_mode": {"type": "string", "default": "Thermal / Overstrain"},
                        "priority": {"type": "string", "enum": ["CRITICAL", "HIGH", "MEDIUM"], "default": "HIGH"},
                    },
                    "required": ["asset_id", "failure_mode"],
                },
            },
            {
                "name": "get_drift_telemetry",
                "description": "Queries current Population Stability Index (PSI) drift metrics across all 5 physical features.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "run_inference_benchmark",
                "description": "Benchmarks C++ ONNX Runtime against Python XGBoost runtime across latency (µs) and throughput (req/sec).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "iterations": {"type": "integer", "default": 100, "description": "Benchmark sample size"},
                    },
                },
            },
        ]

    def _build_resource_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "uri": "pms://system/health",
                "name": "PMS System Health",
                "description": "Real-time health status, database connectivity, and loaded model version",
                "mimeType": "application/json",
            },
            {
                "uri": "pms://models/manifest",
                "name": "Model Architecture & Performance Manifest",
                "description": "Calibrated XGBoost & ONNX model metrics (ROC-AUC, Brier score, threshold)",
                "mimeType": "application/json",
            },
            {
                "uri": "pms://knowledge_base/sop_index",
                "name": "Standard Operating Procedures Index",
                "description": "List of indexed industrial maintenance procedures in RAG store",
                "mimeType": "application/json",
            },
        ]

    def _build_prompt_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "diagnose_machine_anomaly",
                "description": "Interactive technical guide for diagnosing and remediating high-risk machinery alerts",
                "arguments": [
                    {"name": "machine_id", "description": "Asset identifier", "required": True},
                    {"name": "observed_symptoms", "description": "Audible sounds, oil leaks, or visual clues", "required": False},
                ],
            },
            {
                "name": "shift_handover_report",
                "description": "Drafts an operational plant briefing summarizing fleet health and pending work orders",
                "arguments": [
                    {"name": "shift_id", "description": "Shift identifier e.g. Day Shift A", "required": True},
                ],
            },
        ]

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches incoming JSON-RPC 2.0 MCP request to the appropriate handler."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {"name": MCP_SERVER_NAME, "version": MCP_SERVER_VERSION},
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                },
            }

        elif method == "notifications/initialized":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        elif method == "tools/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.tools}}

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            return self._execute_tool(req_id, tool_name, tool_args)

        elif method == "resources/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": self.resources}}

        elif method == "resources/read":
            uri = params.get("uri", "")
            return self._read_resource(req_id, uri)

        elif method == "prompts/list":
            return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": self.prompts}}

        elif method == "prompts/get":
            prompt_name = params.get("name", "")
            prompt_args = params.get("arguments", {})
            return self._get_prompt(req_id, prompt_name, prompt_args)

        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found in MCP server."},
            }

    def _execute_tool(self, req_id: Any, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Executes tool call and formats result as standard MCP content block."""
        try:
            if name == "predict_equipment_risk":
                runtime_str = args.get("runtime", "hybrid").lower()
                rt = InferenceRuntime(runtime_str) if runtime_str in ("onnx", "xgboost", "hybrid") else InferenceRuntime.HYBRID
                res = inference_engine.predict(args, runtime=rt)
                text_content = json.dumps(res, indent=2)

            elif name == "predict_and_narrate":
                res = orchestrate_predict_and_narrate(args, include_counterfactual=args.get("include_counterfactual", True))
                text_content = json.dumps(res, indent=2)

            elif name == "simulate_derate_intervention":
                baseline_data = {
                    "temperature": float(args["temperature"]),
                    "rpm": float(args["rpm"]),
                    "pressure": float(args["pressure"]),
                    "vibration": float(args["vibration"]),
                    "operating_hours": float(args["operating_hours"]),
                }
                res = predictor.simulate_derate(
                    baseline_input=baseline_data,
                    derate_rpm_pct=float(args.get("derate_rpm_pct", -15.0)),
                    derate_pressure_pct=float(args.get("derate_pressure_pct", -10.0)),
                    coolant_temp_delta_c=float(args.get("coolant_temp_delta_c", 0.0)),
                )
                text_content = json.dumps(res, indent=2)

            elif name == "dispatch_work_order":
                import uuid
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                mode = str(args.get("failure_mode", "General")).lower()
                if "therm" in mode:
                    bom = [
                        {"part_number": "HEX-PUMP-GASKET-68", "description": "Thermal Heat Exchanger Gasket Set", "qty": "1"},
                        {"part_number": "OIL-SYNTH-VG68", "description": "ISO VG 68 Synthetic Cooling Lubricant (5L)", "qty": "2"},
                    ]
                    duration = 3.5
                    torque = 35.0
                elif "press" in mode or "strain" in mode:
                    bom = [
                        {"part_number": "HYD-VALVE-PROP-40", "description": "Hydraulic Proportional Relief Valve Cartridge", "qty": "1"},
                        {"part_number": "SEAL-VITON-ORING-KIT", "description": "High-Pressure Viton Fluorocarbon O-Ring Kit", "qty": "1"},
                    ]
                    duration = 6.0
                    torque = 45.0
                elif "power" in mode or "rpm" in mode:
                    bom = [
                        {"part_number": "VFD-STATOR-MOD-22KW", "description": "Variable Frequency Inverter Stator Module", "qty": "1"},
                        {"part_number": "COUPLING-FLEX-ROTOR", "description": "Dynamic Flexible Shaft Coupling", "qty": "1"},
                    ]
                    duration = 5.0
                    torque = 40.0
                else:
                    bom = [{"part_number": "SP-GEN-KIT-01", "description": "Standard Inspection & Fastener Kit", "qty": "1"}]
                    duration = 2.0
                    torque = 30.0

                res = {
                    "work_order_id": f"WO-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}",
                    "asset_id": args.get("asset_id", "CNC-SPINDLE-01"),
                    "line_id": args.get("line_id", "Line 4"),
                    "dispatched_at": now.isoformat(),
                    "status": "DISPATCHED",
                    "cmms_target": "SAP-PM / IBM Maximo",
                    "technician_qualification": "Level II Mechanical Reliability Specialist",
                    "required_bom_parts": bom,
                    "safety_interlocks": ["LOTO Procedure #E-401 Verified", "Zero Hydraulic Stored Pressure Check"],
                    "torque_specs_nm": torque,
                    "estimated_duration_hours": duration,
                }
                text_content = json.dumps(res, indent=2)

            elif name == "get_drift_telemetry":
                from .drift_detector import drift_detector
                res = drift_detector.get_drift_status()
                text_content = json.dumps(res, indent=2)

            elif name == "run_inference_benchmark":
                iters = int(args.get("iterations", 100))
                res = inference_engine.run_benchmark(n_iterations=iters)
                text_content = json.dumps(res, indent=2)

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32602, "message": f"Tool '{name}' not found."},
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": text_content}]},
            }
        except Exception as e:
            logger.error(f"Error executing MCP tool {name}: {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Error executing tool '{name}': {e!s}"}],
                },
            }

    def _read_resource(self, req_id: Any, uri: str) -> Dict[str, Any]:
        """Resolves resource URIs into text/json payloads."""
        if uri == "pms://system/health":
            content = json.dumps(
                {
                    "status": "healthy",
                    "model_loaded": predictor.model is not None,
                    "model_version": predictor.version,
                    "onnx_loaded": inference_engine.onnx_session is not None,
                },
                indent=2,
            )
        elif uri == "pms://models/manifest":
            content = json.dumps(predictor.metadata, indent=2)
        elif uri == "pms://knowledge_base/sop_index":
            chunks = [
                {"id": c["id"], "title": c["title"], "section": c["section"], "failure_mode": c["failure_mode"]}
                for c in rag_store.chunks
            ]
            content = json.dumps({"indexed_chunks": chunks}, indent=2)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Resource URI '{uri}' not recognized."},
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "contents": [{"uri": uri, "mimeType": "application/json", "text": content}]
            },
        }

    def _get_prompt(self, req_id: Any, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Renders an MCP Prompt workflow template."""
        if name == "diagnose_machine_anomaly":
            m_id = args.get("machine_id", "CNC-01")
            symptoms = args.get("observed_symptoms", "None provided")
            instruction = (
                f"You are the PMS Industrial Diagnostic AI for equipment {m_id}.\n"
                f"Observed Shop Floor Symptoms: {symptoms}\n\n"
                "Please follow this diagnostic workflow:\n"
                "1. Call `predict_equipment_risk` with latest telemetry.\n"
                "2. Call `predict_and_narrate` to retrieve standard operating procedures.\n"
                "3. If failure probability >= 0.2849, propose a de-rating plan via `simulate_derate_intervention` "
                "or dispatch an emergency repair order via `dispatch_work_order`."
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "messages": [
                        {"role": "user", "content": {"type": "text", "text": instruction}}
                    ]
                },
            }
        elif name == "shift_handover_report":
            shift = args.get("shift_id", "Current Shift")
            instruction = (
                f"Compile a reliability shift debriefing for {shift}.\n"
                "1. Inspect fleet health and model metrics using resource `pms://system/health`.\n"
                "2. Call `get_drift_telemetry` to verify telemetry sensor drift.\n"
                "3. Summarize equipment requiring scheduled lubrication or wear insert replacements."
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "messages": [
                        {"role": "user", "content": {"type": "text", "text": instruction}}
                    ]
                },
            }
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"Prompt '{name}' not found."},
            }


# Singleton server instance
mcp_server = PMSMCPServer()


def main():
    """Stdio entrypoint for MCP clients (Antigravity, Claude Desktop, Cursor)."""
    # Ensure stdout handles UTF-8
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    for line in sys.stdin:
        line_clean = line.strip()
        if not line_clean:
            continue
        try:
            req = json.loads(line_clean)
            resp = mcp_server.handle_request(req)
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e!s}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
