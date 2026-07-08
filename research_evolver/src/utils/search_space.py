"""
Parse search_space.yaml into a normalized form for mutator and repair.
Handles: list (discrete/ordinal), dict with min/max/type (float), and single-value locked.
"""

from typing import Any

# Genome fields that are locked in v1 (never mutated)
LOCKED_FIELDS = {"task_family", "base_model"}


def parse_search_space(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Return a dict: field_name -> spec.
    spec is one of:
      {"kind": "float", "min": float, "max": float}
      {"kind": "choices", "values": list}  # for discrete and ordinal
      {"kind": "locked", "value": x}
    """
    out: dict[str, dict[str, Any]] = {}
    for field, v in raw.items():
        if field in LOCKED_FIELDS:
            if isinstance(v, list) and len(v) == 1:
                out[field] = {"kind": "locked", "value": v[0]}
            else:
                out[field] = {"kind": "locked", "value": v}
            continue
        if isinstance(v, list):
            out[field] = {"kind": "choices", "values": v}
        elif isinstance(v, dict):
            if "min" in v and "max" in v:
                out[field] = {"kind": "float", "min": float(v["min"]), "max": float(v["max"])}
            else:
                out[field] = {"kind": "locked", "value": v.get("value", list(v.values())[0] if v else None)}
        else:
            out[field] = {"kind": "locked", "value": v}
    return out


def get_float_bounds(spec: dict) -> tuple[float, float] | None:
    if spec.get("kind") == "float":
        return spec["min"], spec["max"]
    return None


def get_choices(spec: dict) -> list[Any] | None:
    if spec.get("kind") == "choices":
        return spec["values"]
    return None


def clamp_float(value: float, spec: dict) -> float:
    bounds = get_float_bounds(spec)
    if bounds is None:
        return value
    return max(bounds[0], min(bounds[1], value))


def snap_to_choice(value: Any, spec: dict) -> Any:
    choices = get_choices(spec)
    if choices is None:
        return value
    if value in choices:
        return value
    # Snap to nearest for numbers; otherwise first
    if isinstance(value, (int, float)) and choices:
        try:
            numeric = [float(c) for c in choices]
            nearest = min(numeric, key=lambda c: abs(c - float(value)))
            return int(nearest) if all(isinstance(c, int) for c in choices) else nearest
        except (TypeError, ValueError):
            pass
    return choices[0] if choices else value
