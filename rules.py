import json
from pathlib import Path

_RULES_PATH = Path(__file__).parent / "config" / "rules.json"


def _confidence_key(field: str) -> str:
    # safe_zone_violation uses "safe_zone_confidence" rather than the default pattern
    if field == "safe_zone_violation":
        return "safe_zone_confidence"
    return f"{field}_confidence"


def _expected_value(rule_name: str) -> bool:
    # logo_detected must be True (logo must be present); every other rule
    # passes when the undesirable thing is absent (False).
    return rule_name == "logo_detected"


def run_rules(extraction: dict, rules_config: dict) -> list[dict]:
    results = []

    for rule_type, rule_list in (
        ("hard_stop", rules_config["hard_stops"]),
        ("soft", rules_config["soft_rules"]),
    ):
        for rule_def in rule_list:
            rule_name = rule_def["rule"]
            field = rule_def["field"]
            reasoning_fail = rule_def["reasoning_fail"]

            field_value = extraction.get(field)
            expected = _expected_value(field)
            passed = field_value == expected

            results.append({
                "rule_name": rule_name,
                "rule_type": rule_type,
                "passed": passed,
                "reasoning": "Passed" if passed else reasoning_fail,
            })

    return results
