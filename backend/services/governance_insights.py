"""Deterministic governance insight generation for analyzed report payloads."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

MAX_SIGNALS = 5
HIGH_THRESHOLD = 0.20
MEDIUM_THRESHOLD = 0.10


def _normalize_ratio(value: Any) -> Optional[float]:
    """Normalize mixed percent/ratio inputs to 0.0-1.0."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        ratio = float(value)
    elif isinstance(value, str):
        raw = value.strip().lower()
        if not raw:
            return None
        has_percent = raw.endswith("%")
        cleaned = re.sub(r"[^0-9.\-]", "", raw)
        if not cleaned:
            return None
        try:
            ratio = float(cleaned)
        except ValueError:
            return None
        if has_percent:
            ratio = ratio / 100.0
    else:
        return None

    if ratio > 1.0:
        ratio = ratio / 100.0
    if ratio < 0.0:
        ratio = 0.0
    return min(ratio, 1.0)


def _severity_from_ratio(ratio: float) -> str:
    if ratio >= HIGH_THRESHOLD:
        return "high"
    if ratio >= MEDIUM_THRESHOLD:
        return "medium"
    return "low"


def _priority_from_severity(severity: str) -> str:
    if severity == "high":
        return "high"
    if severity == "medium":
        return "medium"
    return "low"


def _title_case_metric(metric_key: str) -> str:
    words = [part for part in metric_key.replace("-", "_").split("_") if part]
    if not words:
        return "Service Risk"
    return " ".join(word.capitalize() for word in words)


def _build_signal_from_complaint(complaint: Any) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    if not isinstance(complaint, dict):
        return None

    label = (
        complaint.get("title")
        or complaint.get("theme")
        or complaint.get("name")
        or complaint.get("complaint")
        or complaint.get("category")
    )
    metric_key = (
        complaint.get("source_metric")
        or complaint.get("metric")
        or complaint.get("metric_key")
        or complaint.get("slug")
        or ""
    )
    ratio = _normalize_ratio(
        complaint.get("frequency")
        or complaint.get("share")
        or complaint.get("ratio")
        or complaint.get("percent")
        or complaint.get("percentage")
    )

    if not label or ratio is None:
        return None

    severity = _severity_from_ratio(ratio)
    percent = int(round(ratio * 100))
    metric_name = str(metric_key or f"{str(label).strip().lower().replace(' ', '_')}_mentions")
    title_prefix = str(label).strip()
    signal = {
        "title": f"{title_prefix} Risk",
        "description": f"{percent}% of reviews mention {title_prefix.lower()}.",
        "severity": severity,
        "source_metric": metric_name,
    }
    action = {
        "title": f"Review {title_prefix.lower()} standards",
        "suggested_owner": "Operations Partner",
        "priority": _priority_from_severity(severity),
    }
    return signal, action


def _build_signal_from_sentiment(sentiment_summary: Any) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    if not isinstance(sentiment_summary, dict):
        return None
    ratio = _normalize_ratio(
        sentiment_summary.get("negative_share")
        or sentiment_summary.get("negative_ratio")
        or sentiment_summary.get("negative_percent")
        or sentiment_summary.get("negative")
    )
    if ratio is None:
        return None

    severity = _severity_from_ratio(ratio)
    percent = int(round(ratio * 100))
    signal = {
        "title": "Negative Sentiment Risk",
        "description": f"{percent}% of feedback is coded as negative sentiment.",
        "severity": severity,
        "source_metric": "negative_sentiment_share",
    }
    action = {
        "title": "Prioritize negative sentiment remediation",
        "suggested_owner": "Managing Partner",
        "priority": _priority_from_severity(severity),
    }
    return signal, action


def _build_signal_from_roadmap(implementation_roadmap: Any) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
    if not isinstance(implementation_roadmap, list):
        return None
    unresolved = [item for item in implementation_roadmap if isinstance(item, dict)]
    if not unresolved:
        return None

    count = len(unresolved)
    # Treat roadmap density as a coarse pressure indicator.
    ratio = min(count / 10.0, 1.0)
    severity = _severity_from_ratio(ratio)
    signal = {
        "title": "Execution Load Risk",
        "description": f"{count} implementation actions are queued for follow-through.",
        "severity": severity,
        "source_metric": "implementation_actions_queued",
    }
    action = {
        "title": "Confirm owners and due dates for implementation actions",
        "suggested_owner": "Operations Partner",
        "priority": _priority_from_severity(severity),
    }
    return signal, action


def generate_governance_insights(report: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convert analyzed report payload into governance exposure signals + suggested actions.

    Expected input keys:
      - top_complaints
      - sentiment_summary
      - implementation_roadmap
    """
    if not isinstance(report, dict):
        return {"exposure_signals": [], "recommended_actions": []}

    exposure_signals: List[Dict[str, Any]] = []
    recommended_actions: List[Dict[str, Any]] = []
    seen_metrics = set()

    complaints = report.get("top_complaints") or []
    if isinstance(complaints, list):
        for complaint in complaints:
            built = _build_signal_from_complaint(complaint)
            if not built:
                continue
            signal, action = built
            metric = signal.get("source_metric")
            if metric in seen_metrics:
                continue
            seen_metrics.add(metric)
            exposure_signals.append(signal)
            recommended_actions.append(action)
            if len(exposure_signals) >= MAX_SIGNALS:
                break

    if len(exposure_signals) < MAX_SIGNALS:
        sentiment_built = _build_signal_from_sentiment(report.get("sentiment_summary"))
        if sentiment_built:
            signal, action = sentiment_built
            if signal["source_metric"] not in seen_metrics:
                seen_metrics.add(signal["source_metric"])
                exposure_signals.append(signal)
                recommended_actions.append(action)

    if len(exposure_signals) < MAX_SIGNALS:
        roadmap_built = _build_signal_from_roadmap(report.get("implementation_roadmap"))
        if roadmap_built:
            signal, action = roadmap_built
            if signal["source_metric"] not in seen_metrics:
                exposure_signals.append(signal)
                recommended_actions.append(action)

    # Keep output deterministic and bounded.
    exposure_signals = exposure_signals[:MAX_SIGNALS]
    recommended_actions = recommended_actions[:MAX_SIGNALS]
    return {
        "exposure_signals": exposure_signals,
        "recommended_actions": recommended_actions,
    }


def compute_theme_trends(
    current_report: Dict[str, Any],
    previous_report: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, int]]:
    """Compare current vs previous theme counts and return deterministic trend deltas."""
    if not isinstance(current_report, dict) or not isinstance(previous_report, dict):
        return {}

    current_themes = current_report.get("themes") or {}
    previous_themes = previous_report.get("themes") or {}
    if not isinstance(current_themes, dict) or not isinstance(previous_themes, dict):
        return {}

    trend_map: Dict[str, Dict[str, int]] = {}
    all_theme_keys = set(current_themes.keys()) | set(previous_themes.keys())
    for key in sorted(all_theme_keys):
        try:
            current_count = int(current_themes.get(key) or 0)
            previous_count = int(previous_themes.get(key) or 0)
        except Exception:
            continue
        change = current_count - previous_count
        if previous_count > 0:
            percent = int(round((change / previous_count) * 100))
        elif current_count > 0:
            percent = 100
        else:
            percent = 0
        trend_map[str(key)] = {
            "current": current_count,
            "previous": previous_count,
            "change": change,
            "percent": percent,
        }
    return trend_map
