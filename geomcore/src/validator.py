from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any, Iterable

ALLOWED_KINDS = {"rect", "line", "circle", "text", "polygon", "polyline", "path"}
DEFAULT_MAX_PRIMITIVES = 512

def issue(code: str, message: str, primitive_id: str | None = None) -> dict[str, Any]:
    out = {"code": code, "message": message}
    if primitive_id is not None:
        out["primitive_id"] = primitive_id
    return out

def _finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

def _check_point(v: Any) -> bool:
    return isinstance(v, (list, tuple)) and len(v) == 2 and _finite(v[0]) and _finite(v[1])

def _point_oob(pt: list[float] | tuple[float, float], w: float, h: float, tol: float = 2) -> bool:
    return pt[0] < -tol or pt[1] < -tol or pt[0] > w + tol or pt[1] > h + tol

def validate_ir(ir: dict[str, Any], manifest: dict[str, Any], *, required_features: Iterable[str] = (), per_feature_caps: dict[str, int] | None = None, max_primitives: int = DEFAULT_MAX_PRIMITIVES) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    if not isinstance(ir, dict):
        return [issue("E_IR_TYPE", "IR root must be an object")]
    typ = ir.get("type"); variant = ir.get("variant")
    if not isinstance(typ, str) or not typ.strip() or typ not in manifest:
        errors.append(issue("E_TYPE", f"unknown/empty diagram type: {typ!r}")); type_spec = None
    else:
        type_spec = manifest[typ]
        if not isinstance(variant, str) or variant not in type_spec.get("variants", []):
            errors.append(issue("E_VARIANT", f"unsupported variant {variant!r} for {typ}"))
    canvas = ir.get("canvas")
    if not isinstance(canvas, dict) or not _finite(canvas.get("w")) or not _finite(canvas.get("h")) or canvas.get("w", 0) <= 0 or canvas.get("h", 0) <= 0:
        errors.append(issue("E_CANVAS", "canvas w/h must be finite positive numbers")); w = h = 0.0
    else:
        w, h = float(canvas["w"]), float(canvas["h"])
    prims = ir.get("primitives")
    if not isinstance(prims, list):
        return errors + [issue("E_PRIMITIVES_TYPE", "primitives must be a list")]
    if not prims: errors.append(issue("E_EMPTY_PRIMITIVES", "diagram has no primitives"))
    if len(prims) > max_primitives: errors.append(issue("E_PRIMITIVE_BUDGET", f"{len(prims)} primitives exceeds safety cap {max_primitives}"))
    ids: set[str] = set(); feature_counts: Counter[str] = Counter()
    allowed_features = set(type_spec.get("features", [])) if type_spec else set()
    for idx, p in enumerate(prims):
        if not isinstance(p, dict):
            errors.append(issue("E_PRIMITIVE_TYPE", f"primitive[{idx}] is not an object")); continue
        pid = p.get("id")
        if not isinstance(pid, str) or not pid.strip():
            errors.append(issue("E_EMPTY_ID", "primitive id must be non-empty string")); pid = f"@{idx}"
        elif pid in ids: errors.append(issue("E_DUPLICATE_ID", f"duplicate primitive id {pid}", pid))
        ids.add(pid)
        feat = p.get("feature")
        if not isinstance(feat, str) or not feat.strip():
            errors.append(issue("E_EMPTY_FEATURE", "feature must be non-empty string", pid)); feat = ""
        else:
            feature_counts[feat] += 1
            if feat != "__title__" and type_spec and feat not in allowed_features:
                errors.append(issue("E_UNKNOWN_FEATURE", f"feature {feat!r} is not declared for {typ}", pid))
        kind = p.get("kind")
        if kind not in ALLOWED_KINDS:
            errors.append(issue("E_UNKNOWN_KIND", f"unsupported primitive kind {kind!r}", pid)); continue
        if kind == "rect":
            vals = [p.get(k) for k in ("x", "y", "w", "h")]
            if not all(_finite(v) for v in vals): errors.append(issue("E_NONFINITE", "rect geometry must be finite", pid)); continue
            x,y,rw,rh = map(float, vals)
            if rw <= 0 or rh <= 0: errors.append(issue("E_NONPOSITIVE_GEOMETRY", "rect w/h must be > 0", pid))
            if x < -2 or y < -2 or x + rw > w + 2 or y + rh > h + 2: errors.append(issue("E_OUT_OF_BOUNDS", "rect exceeds canvas", pid))
        elif kind == "circle":
            vals = [p.get(k) for k in ("cx", "cy", "r")]
            if not all(_finite(v) for v in vals): errors.append(issue("E_NONFINITE", "circle geometry must be finite", pid)); continue
            cx,cy,r = map(float, vals)
            if r <= 0: errors.append(issue("E_NONPOSITIVE_GEOMETRY", "circle radius must be > 0", pid))
            if cx-r < -2 or cy-r < -2 or cx+r > w+2 or cy+r > h+2: errors.append(issue("E_OUT_OF_BOUNDS", "circle exceeds canvas", pid))
        elif kind == "line":
            vals = [p.get(k) for k in ("x1", "y1", "x2", "y2")]
            if not all(_finite(v) for v in vals): errors.append(issue("E_NONFINITE", "line geometry must be finite", pid)); continue
            x1,y1,x2,y2 = map(float, vals)
            if x1 == x2 and y1 == y2: errors.append(issue("E_ZERO_LENGTH_LINE", "line endpoints are identical", pid))
            if min(x1,x2)<-2 or min(y1,y2)<-2 or max(x1,x2)>w+2 or max(y1,y2)>h+2: errors.append(issue("E_OUT_OF_BOUNDS", "line exceeds canvas", pid))
        elif kind == "text":
            vals = [p.get("x"), p.get("y")]
            if not all(_finite(v) for v in vals): errors.append(issue("E_NONFINITE", "text anchor must be finite", pid)); continue
            txt = p.get("text")
            if not isinstance(txt, str) or not txt.strip(): errors.append(issue("E_EMPTY_TEXT", "text primitive has empty/whitespace payload", pid))
            if float(p["x"]) < -5 or float(p["y"]) < -5 or float(p["x"]) > w+5 or float(p["y"]) > h+5: errors.append(issue("E_OUT_OF_BOUNDS", "text anchor exceeds canvas", pid))
        elif kind in {"polyline", "polygon"}:
            pts = p.get("points"); min_points = 2 if kind == "polyline" else 3
            if not isinstance(pts, list) or len(pts) < min_points: errors.append(issue("E_EMPTY_POINTS", f"{kind} needs at least {min_points} points", pid)); continue
            if [q for q in pts if not _check_point(q)]: errors.append(issue("E_NONFINITE", f"{kind} has invalid/nonfinite point", pid)); continue
            if any(_point_oob(q,w,h) for q in pts): errors.append(issue("E_OUT_OF_BOUNDS", f"{kind} exceeds canvas", pid))
        elif kind == "path":
            d = p.get("d")
            if not isinstance(d, str) or not d.strip(): errors.append(issue("E_EMPTY_PATH", "path d must be non-empty", pid))
            elif re.search(r"(?:nan|inf)", d, re.I): errors.append(issue("E_NONFINITE", "path contains non-finite token", pid))
    for feat in required_features:
        if feature_counts.get(feat, 0) <= 0: errors.append(issue("E_REQUIRED_FEATURE_MISSING", f"required feature {feat!r} is absent"))
    if per_feature_caps:
        for feat, cap in per_feature_caps.items():
            if feature_counts.get(feat, 0) > cap: errors.append(issue("E_FEATURE_BUDGET", f"feature {feat!r} count {feature_counts[feat]} exceeds cap {cap}"))
    return errors

def error_codes(errors: list[dict[str, Any]]) -> set[str]:
    return {e["code"] for e in errors}
