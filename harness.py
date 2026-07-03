import json
import os
from datetime import datetime, timezone
from pathlib import Path

from extraction import extract_creative_fields
from rules import run_rules, _confidence_key

_RULES_PATH = Path(__file__).parent / "config" / "rules.json"
LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "pipeline_log.json")


def _load_rules() -> dict:
    with open(_RULES_PATH) as f:
        return json.load(f)


def log_step(step_name: str, input_data: dict, output_data: dict, status: str, rules_version: str, submitted_by: str = "") -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "submitted_by": submitted_by,
        "rules_version": rules_version,
        "step": step_name,
        "status": status,
        "input": input_data,
        "output": output_data,
    }

    existing = []
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, ValueError):
            existing = []

    existing.append(entry)
    with open(LOG_PATH, "w") as f:
        json.dump(existing, f, indent=2, default=str)


def _flatten_extraction(nested: dict) -> dict:
    """Convert {field: {value, confidence}} → {field: bool, field_confidence: float}."""
    flat = {}
    for field, entry in nested.items():
        if isinstance(entry, dict) and "value" in entry:
            flat[field] = entry["value"]
            flat[_confidence_key(field)] = entry.get("confidence", 1.0)
        else:
            flat[field] = entry  # already flat (fallback path)
    return flat


def _apply_confidence_filter(extraction: dict, rules_config: dict) -> dict:
    threshold = rules_config.get("confidence_threshold", 0.80)
    all_rule_defs = rules_config["hard_stops"] + rules_config["soft_rules"]
    ruled_fields = {r["field"] for r in all_rule_defs}

    filtered = dict(extraction)
    for field in ruled_fields:
        conf_key = _confidence_key(field)
        confidence = extraction.get(conf_key, 1.0)
        if confidence < threshold:
            filtered[field] = False  # treat as undetected

    return filtered


def run_approval_pipeline(file_bytes: bytes, metadata: dict) -> dict:
    rules_config = _load_rules()
    rules_version = rules_config.get("version", "unknown")
    submitted_by = metadata.get("Email", "")

    # Step 1: extraction
    filename = metadata.get("File", "creative.jpg")
    raw_extraction = extract_creative_fields(file_bytes, filename, metadata)
    log_step("extraction", {"metadata": metadata}, raw_extraction, "ok", rules_version, submitted_by)

    # Step 2: flatten nested {value, confidence} → {field: bool, field_confidence: float}
    flat_extraction = _flatten_extraction(raw_extraction)

    # Step 3: confidence filtering
    extraction = _apply_confidence_filter(flat_extraction, rules_config)
    log_step(
        "confidence_filter",
        {"threshold": rules_config["confidence_threshold"], "flat": flat_extraction},
        extraction,
        "ok",
        rules_version,
        submitted_by,
    )

    # Step 4: rule evaluation
    rule_results = run_rules(extraction, rules_config)
    log_step("rule_evaluation", extraction, rule_results, "ok", rules_version, submitted_by)

    # Step 5: verdict
    hard_stop_failures = [r for r in rule_results if r["rule_type"] == "hard_stop" and not r["passed"]]
    soft_failures = [r for r in rule_results if r["rule_type"] == "soft" and not r["passed"]]
    triggered_rules = [r["rule_name"] for r in rule_results if not r["passed"]]

    total = len(rule_results)
    passed_count = sum(1 for r in rule_results if r["passed"])
    pass_rate = round(passed_count / total, 4) if total else 1.0

    if hard_stop_failures:
        verdict = "Rejected"
    elif soft_failures:
        verdict = "Flagged"
    else:
        verdict = "Approved"

    reasoning_per_rule = {r["rule_name"]: r["reasoning"] for r in rule_results}

    result = {
        "verdict": verdict,
        "rules_version": rules_version,
        "pass_rate": pass_rate,
        "triggered_rules": triggered_rules,
        "reasoning_per_rule": reasoning_per_rule,
        "logs": rule_results,
    }

    log_step("verdict", {"pass_rate": pass_rate, "triggered_rules": triggered_rules}, {"verdict": verdict}, "ok", rules_version, submitted_by)

    return result
