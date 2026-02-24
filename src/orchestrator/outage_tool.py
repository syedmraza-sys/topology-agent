from __future__ import annotations

import asyncio
import random
from typing import Any, Dict

import structlog

from .state_types import TopologyState

logger = structlog.get_logger("orchestrator.outage_tool")

async def run_outage_tool(state: TopologyState) -> Dict[str, Any]:
    """
    Dummy API call to determine the status of an inventory element.
    Takes input arguments (site, device, and circuit) from the planner's scheduled step.
    Returns simulated active outages for the requested elements.
    """
    logger.info("outage_tool_started")
    
    # Extract params from the scheduled plan step
    plan = state.get("plan", {})
    steps = plan.get("steps", [])
    
    params = {}
    for step in steps:
        if step.get("tool") == "outage_tool":
            params = step.get("params", {})
            break

    site_names = params.get("site_names", [])
    device_ids = params.get("device_ids", [])
    circuit_ids = params.get("circuit_ids", [])
    
    # Because planner may output "$ref:step_1.output.circuit_ids" 
    # we'll gently resolve it to actual circuits from state if we see a $ref.
    if isinstance(circuit_ids, str) and circuit_ids.startswith("$ref"):
        inventory_data = state.get("inventory_data") or {}
        circuit_ids = [c.get("circuit_id") for c in inventory_data.get("circuits", []) if c.get("circuit_id")]
    
    if isinstance(device_ids, str) and device_ids.startswith("$ref"):
        inventory_data = state.get("inventory_data") or {}
        # Inventory tool currently returns circuits and sites, we can extract derived device_names if we need, 
        # or just fallback to an empty list.
        device_ids = []

    # UI Context fallback if nothing was derived
    if not site_names and not device_ids and not circuit_ids:
        ui_context = state.get("ui_context", {}) or {}
        site_names = ui_context.get("selected_sites", [])

    if not site_names and not device_ids and not circuit_ids:
        logger.warning("outage_tool_missing_args", reason="At least one site, device, or circuit must be provided.")
        return {
            "active_alarms": [],
            "metadata": {
                "source": "outage_tool",
                "error": "Missing input arguments. At least one of site, device, or circuit must be provided."
            }
        }

    # Simulate an external API call
    await asyncio.sleep(0.2) 
    
    alarms = []
    severities = ["minor", "major", "critical"]
    messages = [
        "Signal pulse anomaly detected",
        "Loss of signal (LOS)",
        "High latency threshold exceeded",
        "Hardware fan failure",
        "BGP peering down"
    ]
    
    # Generate random alarms for circuits
    for cid in circuit_ids:
        if random.random() < 0.3: # 30% chance of an alarm
            alarms.append({
                "alarm_id": f"ALM-CIR-{random.randint(1000, 9999)}",
                "element_id": cid,
                "element_type": "circuit",
                "type": "outage",
                "severity": random.choice(severities),
                "message": random.choice(messages),
                "timestamp": "2026-02-24T14:00:00Z"
            })
            
    # Generate random alarms for devices
    for did in device_ids:
        if random.random() < 0.2:
            alarms.append({
                "alarm_id": f"ALM-DEV-{random.randint(1000, 9999)}",
                "element_id": did,
                "element_type": "device",
                "type": "hardware",
                "severity": random.choice(severities),
                "message": random.choice(messages),
                "timestamp": "2026-02-24T14:00:00Z"
            })
            
    # Generate random alarms for sites
    for site in site_names:
        if random.random() < 0.1:
            alarms.append({
                "alarm_id": f"ALM-SITE-{random.randint(1000, 9999)}",
                "element_id": site,
                "element_type": "site",
                "type": "facility",
                "severity": random.choice(severities),
                "message": "Power fluctuation detected at site",
                "timestamp": "2026-02-24T14:00:00Z"
            })
            
    # To ensure there is ALWAYS at least one alarm if they queried successfully, inject a guaranteed one occasionally
    if not alarms and site_names:
        alarms.append({
            "alarm_id": f"ALM-SITE-{random.randint(1000, 9999)}",
            "element_id": site_names[0],
            "element_type": "site",
            "type": "network",
            "severity": "minor",
            "message": "Transient interface flapping detected in aggregation layer",
            "timestamp": "2026-02-24T14:00:00Z"
        })
    
    return {
        "active_alarms": alarms,
        "metadata": {
            "source": "outage_tool_stub",
            "num_alarms": len(alarms),
            "elements_checked": {
                "sites": len(site_names),
                "devices": len(device_ids),
                "circuits": len(circuit_ids)
            }
        }
    }
