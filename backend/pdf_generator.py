"""
Meeting-ready PDF report generator for Clarion.
Presentation-layer redesign only: no billing or data-model changes.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from io import BytesIO
import logging
import os
import re
from typing import Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

try:
    from svglib.svglib import svg2rlg
except Exception:  # noqa: BLE001
    svg2rlg = None


PDF_COPY = {
    "prepared_by": "Prepared by Clarion",
    "site_url": "app.clarionhq.co",
    "free_upgrade_note": "Upgrade for full report depth, complete action plans, and full comment coverage.",
    "action_preface": "If you only do three things in the next 90 days, start here.",
    "appendix_title": "Appendix - Detailed Metrics",
    "preview_watermark": "Preview - Not for client distribution",
    "default_role": "Operations lead",
}

PDF_TEMPLATE_VERSION = "GovBrief Template v2026-03-03-1"
LOGGER = logging.getLogger(__name__)

ACCENT_THEMES = {
    "default": {
        "accent": colors.HexColor("#d97706"),
        "primary": colors.HexColor("#1e3a8a"),
        "surface": colors.HexColor("#f8fafc"),
    },
    "blue": {
        "accent": colors.HexColor("#2563eb"),
        "primary": colors.HexColor("#1d4ed8"),
        "surface": colors.HexColor("#eff6ff"),
    },
    "green": {
        "accent": colors.HexColor("#0f766e"),
        "primary": colors.HexColor("#065f46"),
        "surface": colors.HexColor("#ecfdf5"),
    },
}

BASE_COLORS = {
    "ink": colors.HexColor("#0f172a"),
    "body": colors.HexColor("#1e293b"),
    "muted": colors.HexColor("#64748b"),
    "border": colors.HexColor("#dce3ee"),
    "card": colors.HexColor("#ffffff"),
    "danger": colors.HexColor("#dc2626"),
    "success": colors.HexColor("#15803d"),
    "warning": colors.HexColor("#b45309"),
}


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _theme_palette(theme_id: Optional[str]) -> Dict[str, colors.Color]:
    selected = ACCENT_THEMES.get((theme_id or "default").lower(), ACCENT_THEMES["default"])
    return {
        "accent": selected["accent"],
        "primary": selected["primary"],
        "surface": selected["surface"],
    }


def _normalize_themes(themes: object) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    if isinstance(themes, dict):
        total_mentions = sum(_safe_int(v) for v in themes.values()) or 1
        for name, mentions in themes.items():
            count = _safe_int(mentions)
            rows.append(
                {
                    "name": str(name),
                    "mentions": count,
                    "percentage": round((count / total_mentions) * 100.0, 1),
                }
            )
    elif isinstance(themes, list):
        mentions_total = 0
        for row in themes:
            if isinstance(row, dict):
                count = _safe_int(row.get("mentions"))
                mentions_total += count
                rows.append(
                    {
                        "name": str(row.get("name") or "Theme"),
                        "mentions": count,
                        "percentage": _safe_float(row.get("percentage"), 0.0),
                    }
                )
            else:
                mentions_total += 1
                rows.append({"name": str(row), "mentions": 1, "percentage": 0.0})

        if mentions_total > 0:
            for row in rows:
                if row.get("percentage", 0.0) <= 0:
                    row["percentage"] = round((_safe_int(row.get("mentions")) / mentions_total) * 100.0, 1)

    rows.sort(key=lambda item: _safe_int(item.get("mentions")), reverse=True)
    return rows


def _extract_quote_entry(item: object, default_sentiment: str) -> Optional[Dict[str, str]]:
    if isinstance(item, str):
        text = item.strip()
        if not text:
            return None
        return {
            "text": text,
            "sentiment": default_sentiment,
            "practice": "General matter",
        }

    if isinstance(item, dict):
        text = str(item.get("review_text") or item.get("text") or "").strip()
        if not text:
            return None

        sentiment_raw = str(item.get("sentiment") or default_sentiment).strip().lower()
        sentiment = sentiment_raw if sentiment_raw in {"positive", "neutral", "negative"} else default_sentiment

        practice = str(
            item.get("practice_area")
            or item.get("matter_type")
            or item.get("theme")
            or item.get("category")
            or "General matter"
        ).strip()

        return {
            "text": text,
            "sentiment": sentiment,
            "practice": practice,
        }

    return None


def _normalize_quote_entries(quotes: object, default_sentiment: str) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    if not isinstance(quotes, list):
        return normalized

    for item in quotes:
        entry = _extract_quote_entry(item, default_sentiment)
        if not entry:
            continue
        entry["text"] = entry["text"].replace("\n", " ").strip()
        if entry["text"]:
            normalized.append(entry)
    return normalized


def _quote_texts(entries: Sequence[Dict[str, str]]) -> List[str]:
    return [entry.get("text", "") for entry in entries if entry.get("text")]


def _sentiment_mix(total_reviews: int, avg_rating: float) -> Dict[str, int]:
    bounded_reviews = max(1, int(total_reviews or 1))
    positive_pct = max(12, min(90, int(round((avg_rating / 5.0) * 100.0))))
    negative_pct = max(5, min(50, int(round((100 - positive_pct) * 0.45))))
    neutral_pct = max(0, 100 - positive_pct - negative_pct)

    positive_count = int(round((positive_pct / 100.0) * bounded_reviews))
    negative_count = int(round((negative_pct / 100.0) * bounded_reviews))
    neutral_count = max(0, bounded_reviews - positive_count - negative_count)

    return {
        "positive_pct": positive_pct,
        "neutral_pct": neutral_pct,
        "negative_pct": negative_pct,
        "positive_count": positive_count,
        "neutral_count": neutral_count,
        "negative_count": negative_count,
    }


def _assessment(avg_rating: float, trend_stability: str) -> Dict[str, str]:
    trend = (trend_stability or "").strip().lower()
    if avg_rating >= 4.3 and trend.startswith("stable"):
        return {
            "label": "Strong",
            "tone": "success",
            "summary": "Client sentiment is consistent and positive across recent reporting periods.",
        }
    if avg_rating >= 3.8:
        return {
            "label": "Balanced",
            "tone": "warning",
            "summary": "Client sentiment is mixed. Prioritized operational follow-through should improve outcomes.",
        }
    return {
        "label": "Needs attention",
        "tone": "danger",
        "summary": "Client satisfaction risk is elevated. Immediate corrective actions are recommended.",
    }


def _trend_stability_from_points(points: Sequence[Dict[str, object]]) -> str:
    if len(points) < 3:
        return "Insufficient data"

    scores = [_safe_float(point.get("avg_rating")) for point in points if point.get("avg_rating") is not None]
    if len(scores) < 3:
        return "Insufficient data"

    spread = max(scores) - min(scores)
    if spread <= 0.25:
        return "Stable"
    if spread <= 0.7:
        return "Moderately stable"
    return "Volatile"


def _at_risk_count(trend_points: Sequence[Dict[str, object]]) -> int:
    if not trend_points:
        return 0

    risk = 0
    prev: Optional[float] = None
    for point in trend_points:
        score = _safe_float(point.get("avg_rating"), 0.0)
        if score and score < 4.0:
            risk += 1
        if prev is not None and score and score < prev:
            risk += 1
        if score:
            prev = score
    return max(0, risk)


def _parse_iso(value: object) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _trend_points_chronological(trend_points: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    indexed = list(enumerate(trend_points))
    indexed.sort(
        key=lambda row: (
            (
                _parse_iso(row[1].get("review_date_end")).timestamp()
                if _parse_iso(row[1].get("review_date_end"))
                else (
                    _parse_iso(row[1].get("created_at")).timestamp()
                    if _parse_iso(row[1].get("created_at"))
                    else float("-inf")
                )
            ),
            (
                _parse_iso(row[1].get("created_at")).timestamp()
                if _parse_iso(row[1].get("created_at"))
                else float("-inf")
            ),
            row[0],
        )
    )
    return [row[1] for row in indexed]


def _windowed_risk_counts(trend_points: Sequence[Dict[str, object]], window_size: int = 4) -> Tuple[int, Optional[int]]:
    points = _trend_points_chronological(trend_points)
    if not points:
        return 0, None

    flags: List[int] = []
    prev_score: Optional[float] = None
    for point in points:
        score = _safe_float(point.get("avg_rating"), 0.0)
        if score <= 0:
            flags.append(0)
            continue
        risk = 1 if score < 4.0 else 0
        if prev_score is not None and score < prev_score:
            risk += 1
        flags.append(1 if risk > 0 else 0)
        prev_score = score

    current_window = flags[-window_size:]
    previous_window = flags[-(window_size * 2):-window_size]
    current_count = sum(current_window)
    previous_count = sum(previous_window) if previous_window else None
    return current_count, previous_count


def _clip(text: str, max_len: int = 140) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_len:
        return normalized
    return normalized[: max_len - 1].rstrip() + "..."


def _clip_at_word(text: str, max_len: int = 200) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_len:
        return normalized
    truncated = normalized[:max_len].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0].rstrip()
    if not truncated:
        truncated = normalized[: max_len - 3].rstrip()
    return truncated + "..."


def _fit_text_to_width(pdf_canvas: canvas.Canvas, text: str, font_name: str, font_size: float, max_width: float) -> str:
    value = str(text or "")
    if max_width <= 0:
        return ""
    if pdf_canvas.stringWidth(value, font_name, font_size) <= max_width:
        return value
    ellipsis = "..."
    clipped = value
    while clipped and pdf_canvas.stringWidth(clipped + ellipsis, font_name, font_size) > max_width:
        clipped = clipped[:-1]
    return (clipped + ellipsis) if clipped else ellipsis


def _fmt_date(value: Optional[str]) -> str:
    if not value:
        return "N/A"
    raw = str(value).strip()
    if not raw:
        return "N/A"
    # Already-human dates should not be truncated (fixes "Mar 01, 20" bug).
    if re.match(r"^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$", raw):
        return raw
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.strftime("%b %d, %Y")
    except ValueError:
        # Last-resort parse attempts before returning raw, never sliced.
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
            try:
                parsed = datetime.strptime(raw, fmt)
                return parsed.strftime("%b %d, %Y")
            except ValueError:
                continue
        return raw


def _firm_display_name(name: Optional[str]) -> str:
    return str(name or "").strip() or "Your Firm"


def _format_brief_date(value: Optional[str]) -> str:
    return _fmt_date(value)


def _format_export_timestamp(value: Optional[str]) -> str:
    if not value:
        return "TBD"
    raw = str(value).strip()
    if not raw:
        return "TBD"
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed.strftime("%b %d, %Y %I:%M %p")
    except ValueError:
        return _fmt_date(raw)


def _fmt_report_date(value: Optional[str]) -> str:
    if not value:
        return datetime.utcnow().strftime("%b %d, %Y")
    return _fmt_date(value)


def _compute_date_range(trend_points: Sequence[Dict[str, object]], fallback: Optional[str], report_date: Optional[str]) -> str:
    if fallback:
        return str(fallback)

    chronological_points = _trend_points_chronological(trend_points)
    review_starts = [str(point.get("review_date_start")) for point in chronological_points if point.get("review_date_start")]
    review_ends = [str(point.get("review_date_end")) for point in chronological_points if point.get("review_date_end")]
    if review_starts and review_ends:
        return f"{_fmt_date(min(review_starts))} to {_fmt_date(max(review_ends))}"

    usable = [point for point in chronological_points if point.get("created_at")]
    if len(usable) >= 2:
        return f"{_fmt_date(str(usable[0].get('created_at')))} to {_fmt_date(str(usable[-1].get('created_at')))}"

    if report_date:
        return _fmt_date(report_date)
    return datetime.utcnow().strftime("%b %Y")

def _logo_flowable(logo_path: Optional[str], max_width: float, max_height: float):
    if not logo_path or not os.path.isfile(logo_path):
        return None

    extension = os.path.splitext(logo_path)[1].lower()
    if extension == ".svg":
        if not svg2rlg:
            return None
        try:
            drawing = svg2rlg(logo_path)
            if not drawing or not drawing.width or not drawing.height:
                return None
            scale = min(max_width / float(drawing.width), max_height / float(drawing.height))
            drawing.scale(scale, scale)
            drawing.width = drawing.width * scale
            drawing.height = drawing.height * scale
            return drawing
        except Exception:  # noqa: BLE001
            return None

    try:
        img_reader = ImageReader(logo_path)
        width, height = img_reader.getSize()
        if not width or not height:
            return None
        ratio = min(max_width / float(width), max_height / float(height))
        return Image(logo_path, width=width * ratio, height=height * ratio)
    except Exception:  # noqa: BLE001
        return None


def _logo_canvas_supported(logo_path: Optional[str]) -> bool:
    if not logo_path or not os.path.isfile(logo_path):
        return False
    ext = os.path.splitext(logo_path)[1].lower()
    return ext in {".png", ".jpg", ".jpeg"}


def _build_styles(palette: Dict[str, colors.Color]) -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontSize=20,
            leading=24,
            textColor=BASE_COLORS["ink"],
            alignment=TA_LEFT,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["BodyText"],
            fontSize=11,
            leading=15,
            textColor=BASE_COLORS["muted"],
            spaceAfter=8,
        ),
        "h1": ParagraphStyle(
            "ReportHeading",
            parent=base["Heading1"],
            fontSize=19,
            leading=23,
            textColor=palette["primary"],
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "ReportHeadingTwo",
            parent=base["Heading2"],
            fontSize=13,
            leading=17,
            textColor=BASE_COLORS["ink"],
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "ReportBody",
            parent=base["BodyText"],
            fontSize=11,
            leading=15,
            textColor=BASE_COLORS["body"],
            spaceAfter=6,
            wordWrap="CJK",
        ),
        "bullet": ParagraphStyle(
            "ReportBullet",
            parent=base["BodyText"],
            fontSize=11,
            leading=15,
            textColor=BASE_COLORS["body"],
            leftIndent=14,
            bulletIndent=2,
            spaceAfter=4,
            wordWrap="CJK",
        ),
        "small": ParagraphStyle(
            "ReportSmall",
            parent=base["BodyText"],
            fontSize=9.7,
            leading=12.5,
            textColor=BASE_COLORS["muted"],
            spaceAfter=4,
            wordWrap="CJK",
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["BodyText"],
            fontSize=8,
            leading=10,
            textColor=BASE_COLORS["muted"],
            spaceAfter=1,
        ),
        "metric_value": ParagraphStyle(
            "MetricValue",
            parent=base["BodyText"],
            fontSize=16,
            leading=18,
            textColor=BASE_COLORS["ink"],
            spaceAfter=2,
        ),
        "cover_meta": ParagraphStyle(
            "CoverMeta",
            parent=base["BodyText"],
            fontSize=10,
            leading=14,
            textColor=BASE_COLORS["muted"],
            spaceAfter=4,
        ),
        "quote": ParagraphStyle(
            "QuoteBody",
            parent=base["BodyText"],
            fontSize=9,
            leading=13,
            textColor=BASE_COLORS["body"],
            leftIndent=6,
            rightIndent=6,
            spaceAfter=2,
            wordWrap="CJK",
        ),
        "client_signal_quote": ParagraphStyle(
            "ClientSignalQuote",
            parent=base["BodyText"],
            fontSize=12,
            leading=17,
            textColor=BASE_COLORS["body"],
            leftIndent=14,
            bulletIndent=2,
            rightIndent=2,
            spaceAfter=6,
            wordWrap="CJK",
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=13.5,
            textColor=BASE_COLORS["ink"],
            wordWrap="CJK",
        ),
        "table_cell": ParagraphStyle(
            "TableCell",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=13.5,
            textColor=BASE_COLORS["body"],
            wordWrap="CJK",
        ),
        "appendix_table_header": ParagraphStyle(
            "AppendixTableHeader",
            parent=base["BodyText"],
            fontSize=11,
            leading=14,
            textColor=BASE_COLORS["ink"],
            wordWrap="CJK",
        ),
        "appendix_table_cell": ParagraphStyle(
            "AppendixTableCell",
            parent=base["BodyText"],
            fontSize=11,
            leading=14,
            textColor=BASE_COLORS["body"],
            wordWrap="CJK",
        ),
        "callout_title": ParagraphStyle(
            "CalloutTitle",
            parent=base["Heading3"],
            fontSize=11,
            leading=14,
            textColor=BASE_COLORS["ink"],
            spaceAfter=3,
        ),
        "callout_body": ParagraphStyle(
            "CalloutBody",
            parent=base["BodyText"],
            fontSize=10.5,
            leading=13.5,
            textColor=BASE_COLORS["body"],
            spaceAfter=2,
            wordWrap="CJK",
        ),
    }


def _metric_card(title: str, value: str, detail: str, styles: Dict[str, ParagraphStyle], width: float = 2.95 * inch):
    content = [
        Paragraph(title, styles["metric_label"]),
        Paragraph(value, styles["metric_value"]),
        Paragraph(detail, styles["small"]),
    ]
    table = Table([[item] for item in content], colWidths=[width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BASE_COLORS["card"]),
                ("BOX", (0, 0), (-1, -1), 0.75, BASE_COLORS["border"]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _info_panel(
    title: str,
    lines: Sequence[str],
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    width: float = 6.3 * inch,
):
    rows: List[List[object]] = [[Paragraph(title, styles["callout_title"])]]
    for line in lines:
        if line:
            rows.append([Paragraph(f"- {_clip(line, 170)}", styles["callout_body"])])

    panel = Table(rows, colWidths=[width])
    panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette["surface"]),
                ("BOX", (0, 0), (-1, -1), 0.8, BASE_COLORS["border"]),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, palette["accent"]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return panel


def _line_chart(
    labels: Sequence[str],
    points: Sequence[float],
    palette: Dict[str, colors.Color],
    width: int = 420,
    height: int = 195,
) -> Drawing:
    drawing = Drawing(width, height)
    chart = HorizontalLineChart()
    chart.x = 28
    chart.y = 24
    chart.height = max(68, height - 56)
    chart.width = max(108, width - 46)
    chart.data = [tuple(points)]
    chart.categoryAxis.categoryNames = list(labels)
    chart.categoryAxis.labels.boxAnchor = "n"
    if len(labels) > 4:
        chart.categoryAxis.labels.angle = 18
        chart.categoryAxis.labels.dy = -2
        chart.categoryAxis.labels.fontSize = 6.5
    else:
        chart.categoryAxis.labels.angle = 0
        chart.categoryAxis.labels.fontSize = 7

    min_point = min(points) if points else 0.0
    max_point = max(points) if points else 5.0
    spread = max(0.4, max_point - min_point)
    padding = max(0.15, spread * 0.2)
    chart.valueAxis.valueMin = max(0.0, min_point - padding)
    chart.valueAxis.valueMax = min(5.0, max_point + padding)
    if chart.valueAxis.valueMax <= chart.valueAxis.valueMin:
        chart.valueAxis.valueMax = min(5.0, chart.valueAxis.valueMin + 0.5)
    chart.valueAxis.valueStep = 0.5
    chart.valueAxis.labels.fontSize = 7
    chart.lines[0].strokeColor = palette["accent"]
    chart.lines[0].strokeWidth = 2
    chart.joinedLines = 1
    drawing.add(chart)
    return drawing


def _bar_chart(
    labels: Sequence[str],
    points: Sequence[int],
    palette: Dict[str, colors.Color],
    width: int = 420,
    height: int = 195,
) -> Drawing:
    drawing = Drawing(width, height)
    chart = VerticalBarChart()
    chart.x = 28
    chart.y = 24
    chart.height = max(68, height - 56)
    chart.width = max(108, width - 46)
    chart.data = [tuple(points)]
    chart.categoryAxis.categoryNames = list(labels)
    chart.categoryAxis.labels.fontSize = 6.5 if len(labels) > 4 else 7
    chart.categoryAxis.labels.boxAnchor = "n"
    if len(labels) > 4:
        chart.categoryAxis.labels.angle = 15
        chart.categoryAxis.labels.dy = -2
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.valueMin = 0
    max_value = max(points) if points else 1
    chart.valueAxis.valueMax = max_value + max(3, int(max_value * 0.2))
    chart.valueAxis.valueStep = max(1, int(chart.valueAxis.valueMax / 5))
    chart.bars[0].fillColor = palette["accent"]
    chart.bars[0].strokeColor = palette["primary"]
    drawing.add(chart)
    return drawing


def _theme_insight_sentence(name: str) -> str:
    lower = (name or "").lower()
    if "commun" in lower:
        return "Communication delays and unclear next steps are appearing repeatedly in client feedback."
    if "respons" in lower or "wait" in lower:
        return "Response speed is inconsistent, creating avoidable frustration between key matter updates."
    if "bill" in lower or "cost" in lower or "fee" in lower or "value" in lower or "invoice" in lower:
        return "Cost clarity is a pressure point; clients want clearer estimates and invoice context."
    if "outcome" in lower or "result" in lower:
        return "Case outcomes remain a strength and are a primary reason for positive client sentiment."
    if "expert" in lower or "legal" in lower:
        return "Clients acknowledge legal expertise, but service consistency still shapes their overall experience."
    if "professional" in lower:
        return "Professional conduct is recognized, and consistency across teams can further strengthen trust."
    if "staff" in lower or "support" in lower:
        return "Staff handoffs influence how clients judge reliability across the full matter lifecycle."
    return "This theme is material enough to include in partner-level operating priorities for the next cycle."


def _derive_summary_bullets(
    avg_rating: float,
    trend_stability: str,
    themes: Sequence[Dict[str, float]],
    sentiment_mix: Dict[str, int],
    top_praise: Sequence[str],
    top_complaints: Sequence[str],
) -> Tuple[List[str], List[str]]:
    positives: List[str] = []
    needs_attention: List[str] = []

    friction_tokens = ("commun", "respons", "bill", "cost", "fee", "wait", "support")
    strength_tokens = ("outcome", "result", "expert", "legal", "professional")

    if avg_rating >= 4.2:
        positives.append(f"Overall satisfaction is {avg_rating:.2f}/5, indicating clients generally value recent matter outcomes.")
    elif avg_rating >= 3.8:
        positives.append(f"Overall satisfaction is {avg_rating:.2f}/5; core delivery is solid with clear room to improve execution consistency.")

    if trend_stability.lower().startswith("stable"):
        positives.append("Sentiment direction is stable across recent snapshots, supporting predictable service performance.")

    if sentiment_mix.get("positive_pct", 0) >= 70:
        positives.append(
            f"Positive feedback remains high at {sentiment_mix.get('positive_pct', 0)}% of analyzed comments."
        )

    for theme in themes[:5]:
        name = str(theme.get("name") or "")
        lowered = name.lower()
        if any(token in lowered for token in strength_tokens):
            positives.append(f"{name} appears as a recurring strength and can be used as a standard for other teams.")
            break

    if top_praise:
        positives.append(f"Client praise often cites outcomes or professionalism, including comments like '{_clip(top_praise[0], 95)}'.")

    if avg_rating < 4.0:
        needs_attention.append("Satisfaction is below target and warrants immediate owner-level follow-through.")

    if trend_stability.lower().startswith("volatile"):
        needs_attention.append("Sentiment shifts between snapshots are volatile, suggesting inconsistent experience across matters.")

    if sentiment_mix.get("negative_pct", 0) >= 20:
        needs_attention.append(
            f"Negative feedback remains material at {sentiment_mix.get('negative_pct', 0)}% and should be addressed in the next 90-day cycle."
        )

    for theme in themes[:5]:
        name = str(theme.get("name") or "")
        lowered = name.lower()
        if any(token in lowered for token in friction_tokens):
            needs_attention.append(f"{name} appears repeatedly as a friction theme and should have a named owner and measurable KPI.")
            break

    if top_complaints:
        needs_attention.append(f"Representative friction comments reference issues such as '{_clip(top_complaints[0], 95)}'.")

    if not positives:
        positives.append("Clients continue to report positive experiences worth preserving through existing delivery standards.")

    if not needs_attention:
        needs_attention.append("No immediate critical issue detected; maintain monthly review cadence and watch for trend shifts.")

    return positives[:3], needs_attention[:3]


def _derive_action_items(
    implementation_items: Optional[Sequence[object]],
    themes: Optional[Sequence[object]],
) -> List[Dict[str, str]]:
    actions: List[Dict[str, str]] = []

    def _safe_generated(theme_name: str, idx: int) -> Dict[str, str]:
        generated = None  # stub removed: build_theme_action always returned None
        if not isinstance(generated, dict):
            return {
                "title": "Define and execute service-priority mitigation",
                "owner": PDF_COPY["default_role"],
                "timeframe": "0-30 days",
                "kpi": "Track measurable outcome improvement",
            }
        return {
            "title": str(generated.get("title") or "Define and execute service-priority mitigation").strip(),
            "owner": str(generated.get("owner") or PDF_COPY["default_role"]).strip(),
            "timeframe": str(generated.get("timeframe") or "0-30 days").strip() or "0-30 days",
            "kpi": str(generated.get("kpi") or "Track measurable outcome improvement").strip(),
        }

    safe_items = list(implementation_items or [])
    safe_themes = list(themes or [])

    for idx, raw_item in enumerate(safe_items):
        if not isinstance(raw_item, dict):
            continue
        item = raw_item
        title = str(item.get("title") or item.get("action") or "").strip()
        theme_name = str(item.get("theme") or "").strip()
        if not title and theme_name:
            generated = _safe_generated(theme_name, idx)
            title = generated["title"]
        if not title:
            continue
        owner = str(item.get("owner") or PDF_COPY["default_role"]).strip()
        kpi = str(item.get("kpi") or "Track response times and feedback lift").strip()
        if theme_name and (not owner or owner == PDF_COPY["default_role"] or not kpi):
            generated = _safe_generated(theme_name, idx)
            owner = owner or generated["owner"]
            kpi = kpi or generated["kpi"]
        due_date = str(item.get("due_date") or "").strip()
        timeframe = str(item.get("timeline") or "").strip() or "0-30 days"
        if due_date:
            timeframe = f"By {_fmt_date(due_date)}"
        actions.append(
            {
                "title": title,
                "owner": owner,
                "timeframe": timeframe,
                "kpi": kpi,
                "status": str(item.get("status") or "").strip().lower() or "open",
            }
        )

    if actions:
        return actions

    phase_labels = ["0-30 days", "31-60 days", "61-90 days"]
    for index, raw_theme in enumerate(safe_themes[:5]):
        if not isinstance(raw_theme, dict):
            continue
        theme = raw_theme
        phase = phase_labels[min(index, 2)]
        theme_name = str(theme.get("name") or "service priority")
        generated = _safe_generated(theme_name, index)
        actions.append(
            {
                "title": generated["title"],
                "owner": generated["owner"],
                "timeframe": generated["timeframe"] or phase,
                "kpi": generated["kpi"],
                "status": "open",
            }
        )

    if not actions:
        actions.append(
            {
                "title": "Run next feedback cycle and document top recurring concerns",
                "owner": "Operations lead",
                "timeframe": "0-30 days",
                "kpi": "Complete next report cycle",
                "status": "open",
            }
        )

    return actions

def _normalize_action_rows(implementation_items: Optional[Sequence[object]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for raw in list(implementation_items or []):
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or raw.get("action") or "").strip()
        if not title:
            continue
        rows.append(
            {
                "title": title,
                "owner": str(raw.get("owner") or "Unassigned").strip() or "Unassigned",
                "theme": str(raw.get("theme") or "").strip() or None,
                "due_date": str(raw.get("due_date") or "").strip() or None,
                "status": str(raw.get("status") or "open").strip().lower() or "open",
                "created_at": str(raw.get("created_at") or "").strip() or None,
                "updated_at": str(raw.get("updated_at") or "").strip() or None,
            }
        )
    return rows


def _status_bucket(status: str) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"done", "completed"}:
        return "completed"
    if "progress" in normalized:
        return "in_progress"
    if "overdue" in normalized:
        return "overdue"
    return "planned"


def _build_governance_snapshot_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    firm_name: str,
    export_date: str,
    participants_line: str,
    exported_by: str,
    exported_role: str,
    exported_at: str,
    version_hash: str,
    exposure_status: str,
    escalation_required: str,
    primary_risk_driver: str,
    responsible_owner: str,
    at_risk_matters: str,
    open_actions: str,
    overdue_actions: str,
    satisfaction_line: str,
    last_brief_date: str,
    delta_at_risk: str,
    delta_opened: str,
    delta_completed: str,
    delta_satisfaction: str,
    governance_signals: Sequence[Dict[str, object]],
    governance_recommendations: Sequence[Dict[str, object]],
    integrity_messages: Sequence[str],
) -> List[object]:
    participants_value = str(participants_line or "").strip()
    show_participants_blank_line = (not participants_value) or participants_value in {"â€”", "Ã¢â‚¬â€", "-", "N/A"}
    participants_text = "Participants: ____________________" if show_participants_blank_line else f"Participants: {participants_value}"

    export_meta_rows = [
        Paragraph(f"Exported by: {exported_by} ({exported_role})", styles["small"]),
        Paragraph(f"Exported: {exported_at}", styles["small"]),
        Paragraph(f"Version: {version_hash}", styles["small"]),
    ]

    flow: List[object] = [
        Paragraph("Clarion", styles["title"]),
        Paragraph("Client Experience Governance Brief", styles["subtitle"]),
        Paragraph(f"Firm: {firm_name}", styles["body"]),
        Paragraph(f"Date: {export_date}", styles["small"]),
        Spacer(1, 0.06 * inch),
        *export_meta_rows,
        Spacer(1, 0.02 * inch),
        Paragraph(participants_text, styles["body"]),
        Spacer(1, 0.04 * inch),
        Paragraph("Agenda", styles["h2"]),
        Paragraph("- Leadership Briefing", styles["body"]),
        Paragraph("- Signals That Matter Most", styles["body"]),
        Paragraph("- Assigned Follow-Through", styles["body"]),
        Paragraph("- Decisions & Next Steps", styles["body"]),
        Paragraph("- Supporting Client Evidence", styles["body"]),
        Paragraph("- Client Signals", styles["body"]),
        Spacer(1, 0.04 * inch),
        Paragraph("Leadership Briefing", styles["h2"]),
        Spacer(1, 0.03 * inch),
        Paragraph("Exposure & Escalation", styles["h2"]),
        Spacer(1, 0.03 * inch),
    ]

    snapshot_rows = [
        [Paragraph("Exposure Status:", styles["table_cell"]), Paragraph(str(exposure_status), styles["table_cell"])],
        [Paragraph("Partner Escalation Required:", styles["table_cell"]), Paragraph(str(escalation_required), styles["table_cell"])],
        [Paragraph("Primary Risk Driver:", styles["table_cell"]), Paragraph(str(primary_risk_driver), styles["table_cell"])],
        [Paragraph("Responsible Owner:", styles["table_cell"]), Paragraph(str(responsible_owner), styles["table_cell"])],
        [Paragraph("At-Risk Matters:", styles["table_cell"]), Paragraph(str(at_risk_matters), styles["table_cell"])],
        [Paragraph("Open Governance Actions:", styles["table_cell"]), Paragraph(str(open_actions), styles["table_cell"])],
        [Paragraph("Overdue Actions:", styles["table_cell"]), Paragraph(str(overdue_actions), styles["table_cell"])],
        [Paragraph("Satisfaction (All-Time):", styles["table_cell"]), Paragraph(str(satisfaction_line), styles["table_cell"])],
    ]
    snapshot_table = Table(snapshot_rows, colWidths=[2.75 * inch, 3.55 * inch])
    snapshot_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, BASE_COLORS["border"]),
                ("BACKGROUND", (0, 0), (-1, 1), palette["surface"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
            ]
        )
    )
    flow.append(snapshot_table)
    flow.append(Spacer(1, 0.08 * inch))
    flow.append(Paragraph("Signals That Matter Most", styles["h2"]))
    top_signals = list(governance_signals[:3])
    top_recommendations = list(governance_recommendations[:3])
    summary_rows: List[List[object]] = [
        [
            Paragraph("<b>Top 3 exposure signals</b>", styles["table_header"]),
            Paragraph("<b>Recommended actions</b>", styles["table_header"]),
        ]
    ]
    max_len = max(len(top_signals), len(top_recommendations), 1)
    for idx in range(max_len):
        signal = top_signals[idx] if idx < len(top_signals) else {}
        recommendation = top_recommendations[idx] if idx < len(top_recommendations) else {}

        signal_title = str(signal.get("title") or "No persisted signal")
        signal_desc = str(signal.get("description") or "").strip()
        signal_severity = str(signal.get("severity") or "low").strip().title()
        signal_line = _clip(signal_title, 90)
        if signal_desc:
            signal_line = f"{signal_line} ({_clip(signal_desc, 100)})"
        signal_line = f"{signal_line} [{signal_severity}]"

        action_title = str(recommendation.get("title") or "No persisted recommendation")
        action_priority = str(recommendation.get("priority") or "low").strip().title()
        action_owner = str(recommendation.get("suggested_owner") or "Unassigned").strip() or "Unassigned"
        action_line = f"{_clip(action_title, 90)} [{action_priority}] - Owner: {_clip(action_owner, 36)}"

        summary_rows.append(
            [
                Paragraph(signal_line, styles["table_cell"]),
                Paragraph(action_line, styles["table_cell"]),
            ]
        )
    summary_table = Table(summary_rows, colWidths=[3.15 * inch, 3.15 * inch], repeatRows=1, splitByRow=1)
    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, BASE_COLORS["border"]),
                ("BACKGROUND", (0, 0), (-1, 0), palette["surface"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow.append(summary_table)
    flow.append(Spacer(1, 0.08 * inch))
    flow.append(Paragraph(f"Since Last Brief ({last_brief_date})", styles["h2"]))

    delta_table = Table(
        [
            [Paragraph("New At-Risk Matters:", styles["table_cell"]), Paragraph(str(delta_at_risk), styles["table_cell"])],
            [Paragraph("Actions Opened:", styles["table_cell"]), Paragraph(str(delta_opened), styles["table_cell"])],
            [Paragraph("Actions Completed:", styles["table_cell"]), Paragraph(str(delta_completed), styles["table_cell"])],
            [Paragraph("Satisfaction Movement:", styles["table_cell"]), Paragraph(str(delta_satisfaction), styles["table_cell"])],
        ],
        colWidths=[2.75 * inch, 3.55 * inch],
    )
    delta_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.6, BASE_COLORS["border"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
            ]
        )
    )
    flow.append(delta_table)
    flow.append(Spacer(1, 0.03 * inch))
    flow.append(
        Paragraph(
            "Scope note: All-Time Satisfaction reflects the latest overall score. Satisfaction Movement reflects change since the last Governance Brief.",
            styles["small"],
        )
    )
    flow.append(Spacer(1, 0.08 * inch))
    flow.append(Paragraph("Governance Integrity", styles["h2"]))
    for line in integrity_messages:
        flow.append(Paragraph(line, styles["body"]))
    flow.append(Spacer(1, 0.08 * inch))
    flow.append(Paragraph("Decisions & Next Steps", styles["h2"]))
    try:
        open_actions_int = int(str(open_actions))
    except ValueError:
        open_actions_int = 0
    if str(exposure_status).strip().lower() == "high" and open_actions_int == 0:
        flow.append(Paragraph("Decision Required: Approve mitigation actions before next meeting (Yes / No)", styles["body"]))
        flow.append(Paragraph("If No, record rationale and next review date.", styles["body"]))
    elif open_actions_int > 0:
        flow.append(Paragraph("Confirm assignments and due dates (Yes / No)", styles["body"]))
    flow.append(Paragraph("Decision 1: __________________", styles["body"]))
    flow.append(Spacer(1, 0.02 * inch))
    flow.append(Paragraph("Decision 2: __________________", styles["body"]))
    flow.append(Spacer(1, 0.02 * inch))
    flow.append(Paragraph("Decision 3: __________________", styles["body"]))
    return flow


def _build_execution_accountability_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    action_rows: Sequence[Dict[str, object]],
    exposure_status: str,
    negative_themes: Sequence[Dict[str, float]],
) -> List[object]:
    flow: List[object] = [Paragraph("Assigned Follow-Through", styles["h1"]), Spacer(1, 0.06 * inch)]

    now = datetime.utcnow()
    summary = {"overdue": 0, "in_progress": 0, "planned": 0, "completed": 0}
    for row in action_rows:
        bucket = _status_bucket(str(row.get("status") or "open"))
        due_dt = _parse_iso(row.get("due_date"))
        if bucket != "completed" and due_dt and due_dt < now:
            bucket = "overdue"
        summary[bucket] += 1

    if not action_rows:
        if exposure_status != "Baseline":
            gap = Table(
                [[Paragraph("High exposure with no actions - assign during meeting.", styles["body"])]],
                colWidths=[6.3 * inch],
            )
            gap.setStyle(
                TableStyle(
                    [
                        ("BOX", (0, 0), (-1, -1), 1, BASE_COLORS["danger"]),
                        ("BACKGROUND", (0, 0), (-1, -1), palette["surface"]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            flow.append(gap)
            flow.append(Spacer(1, 0.06 * inch))
            flow.append(Paragraph("Assignment Mandate", styles["h2"]))
            mandate_rows: List[List[object]] = [
                [
                    Paragraph("<b>Action</b>", styles["table_header"]),
                    Paragraph("<b>Owner</b>", styles["table_header"]),
                    Paragraph("<b>Due</b>", styles["table_header"]),
                    Paragraph("<b>Status</b>", styles["table_header"]),
                    Paragraph("<b>Escalation</b>", styles["table_header"]),
                ]
            ]
            top_themes = list(negative_themes[:3])
            if not top_themes:
                top_themes = [{"name": "Uncategorized"}] * 3
            while len(top_themes) < 3:
                top_themes.append({"name": "Uncategorized"})
            for row in top_themes[:3]:
                theme_name = str(row.get("name") or "Uncategorized")
                mandate_rows.append(
                    [
                        Paragraph(_clip(f"Assign mitigation for {theme_name}", 90), styles["table_cell"]),
                        Paragraph("Unassigned", styles["table_cell"]),
                        Paragraph("TBD", styles["table_cell"]),
                        Paragraph("Planned", styles["table_cell"]),
                        Paragraph("High", styles["table_cell"]),
                    ]
                )
            mandate_table = Table(
                mandate_rows,
                colWidths=[2.35 * inch, 1.2 * inch, 1.1 * inch, 0.9 * inch, 1.0 * inch],
                repeatRows=1,
                splitByRow=1,
            )
            mandate_table.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.5, BASE_COLORS["border"]),
                        ("BACKGROUND", (0, 0), (-1, 0), palette["surface"]),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 5),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            flow.append(mandate_table)
        else:
            flow.append(Paragraph("No active governance actions at this time.", styles["body"]))
    else:
        flow.append(Paragraph("Assignments confirmed during meeting: Yes / No", styles["small"]))
        flow.append(Spacer(1, 0.03 * inch))
        table_rows: List[List[object]] = [
            [
                Paragraph("<b>Action</b>", styles["table_header"]),
                Paragraph("<b>Owner</b>", styles["table_header"]),
                Paragraph("<b>Due Date</b>", styles["table_header"]),
                Paragraph("<b>Status</b>", styles["table_header"]),
                Paragraph("<b>Escalation</b>", styles["table_header"]),
            ]
        ]
        for row in action_rows[:20]:
            status = str(row.get("status") or "open").strip().lower() or "open"
            due_dt = _parse_iso(row.get("due_date"))
            overdue = status not in {"done", "completed"} and bool(due_dt and due_dt < now)
            owner = str(row.get("owner") or "Unassigned").strip() or "Unassigned"
            escalation = "High" if overdue else ("Medium" if owner.lower() == "unassigned" else "Low")
            table_rows.append(
                [
                    Paragraph(_clip(str(row.get("title") or "TBD"), 90), styles["table_cell"]),
                    Paragraph(_clip(owner, 36), styles["table_cell"]),
                    Paragraph(_fmt_date(row.get("due_date") if row.get("due_date") else None), styles["table_cell"]),
                    Paragraph(_clip(status.replace("_", " ").title(), 24), styles["table_cell"]),
                    Paragraph(escalation, styles["table_cell"]),
                ]
            )
        table = Table(table_rows, colWidths=[2.35 * inch, 1.2 * inch, 1.1 * inch, 0.9 * inch, 1.0 * inch], repeatRows=1, splitByRow=1)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, BASE_COLORS["border"]),
                    ("BACKGROUND", (0, 0), (-1, 0), palette["surface"]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        flow.append(table)

    flow.append(Spacer(1, 0.08 * inch))
    flow.append(Paragraph("Execution Summary", styles["h2"]))
    summary_table = Table(
        [
            [Paragraph("Overdue:", styles["table_cell"]), Paragraph(str(summary["overdue"]), styles["table_cell"])],
            [Paragraph("In Progress:", styles["table_cell"]), Paragraph(str(summary["in_progress"]), styles["table_cell"])],
            [Paragraph("Planned:", styles["table_cell"]), Paragraph(str(summary["planned"]), styles["table_cell"])],
            [Paragraph("Completed:", styles["table_cell"]), Paragraph(str(summary["completed"]), styles["table_cell"])],
        ],
        colWidths=[2.2 * inch, 0.9 * inch],
    )
    summary_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BASE_COLORS["border"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    flow.append(summary_table)
    flow.append(Spacer(1, 0.16 * inch))
    flow.append(Paragraph("Reviewed by: ___________________________", styles["body"]))
    flow.append(Spacer(1, 0.04 * inch))
    flow.append(Paragraph("Date: ___________________________", styles["body"]))
    return flow


def _build_risk_drivers_page(
    styles: Dict[str, ParagraphStyle],
    themes: Sequence[Dict[str, float]],
    direction_symbol: str,
) -> List[object]:
    flow: List[object] = [CondPageBreak(1.9 * inch)]
    top_themes = _top_negative_themes(themes, limit=3)
    if not top_themes:
        flow.extend([Paragraph("Top Negative Drivers", styles["h1"]), Spacer(1, 0.06 * inch)])
        flow.append(Paragraph("No negative drivers identified in current signals.", styles["body"]))
        return flow

    first = top_themes[0]
    first_name = str(first.get("name") or "Uncategorized")
    first_share = f"{_safe_float(first.get('percentage')):.1f}%"
    flow.append(
        KeepTogether(
            [
                Paragraph("Top Negative Drivers", styles["h1"]),
                Spacer(1, 0.06 * inch),
                Paragraph(f"{first_name} - {first_share} - {direction_symbol}", styles["h2"]),
                Paragraph(_theme_insight_sentence(first_name), styles["body"]),
                Spacer(1, 0.05 * inch),
            ]
        )
    )

    for row in top_themes[1:]:
        name = str(row.get("name") or "Uncategorized")
        share = f"{_safe_float(row.get('percentage')):.1f}%"
        flow.append(Paragraph(f"{name} - {share} - {direction_symbol}", styles["h2"]))
        flow.append(Paragraph(_theme_insight_sentence(name), styles["body"]))
        flow.append(Spacer(1, 0.05 * inch))
    return flow


def _top_negative_themes(themes: Sequence[Dict[str, float]], limit: int = 3) -> List[Dict[str, float]]:
    friction_tokens = ("commun", "respons", "wait", "bill", "cost", "fee", "support", "delay", "friction", "complaint")
    strength_tokens = ("outcome", "result", "expert", "legal", "professional", "strength")
    negative_themes: List[Dict[str, float]] = []
    for row in themes:
        name = str(row.get("name") or "").lower()
        if not name:
            continue
        if any(token in name for token in strength_tokens):
            continue
        if any(token in name for token in friction_tokens):
            negative_themes.append(row)
    return negative_themes[:limit]


def _build_client_signals_page(
    styles: Dict[str, ParagraphStyle],
    praise_entries: Sequence[Dict[str, str]],
    complaint_entries: Sequence[Dict[str, str]],
) -> List[object]:
    flow: List[object] = [CondPageBreak(1.6 * inch), Paragraph("Client Signals", styles["h1"]), Spacer(1, 0.06 * inch)]
    merged = list(complaint_entries[:4]) + list(praise_entries[:4])
    if not merged:
        flow.append(Paragraph("No representative client signals available.", styles["body"]))
        return flow

    def _quote_bullet(row: Dict[str, str]) -> Paragraph:
        quote = _clip_at_word(str(row.get("text") or "â€”"), 200)
        return Paragraph(f'"{escape(quote)}"', styles["client_signal_quote"], bulletText="â€¢")

    for row in merged[:6]:
        flow.append(_quote_bullet(row))
        flow.append(Spacer(1, 0.08 * inch))
    return flow


def _build_positive_reinforcements_page(
    styles: Dict[str, ParagraphStyle],
    themes: Sequence[Dict[str, float]],
) -> List[object]:
    flow: List[object] = [Paragraph("Positive Reinforcements (Optional)", styles["h2"]), Spacer(1, 0.04 * inch)]
    strength_tokens = ("outcome", "result", "expert", "legal", "professional", "strength")
    positive_rows: List[Dict[str, float]] = []
    for row in themes:
        name = str(row.get("name") or "").lower()
        if any(token in name for token in strength_tokens):
            positive_rows.append(row)
    if not positive_rows:
        flow.append(Paragraph("â€”", styles["body"]))
        return flow

    for row in positive_rows[:3]:
        name = str(row.get("name") or "Theme")
        share = f"{_safe_float(row.get('percentage')):.1f}%"
        flow.append(Paragraph(f"{name} - {share}", styles["body"]))
    return flow

def _build_cover_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    firm_name: str,
    report_title: str,
    date_range: str,
    report_date: str,
    plan_label: str,
    logo_path: Optional[str],
) -> List[object]:
    flow: List[object] = []
    flow.append(Spacer(1, 0.25 * inch))

    firm_logo = _logo_flowable(logo_path, max_width=2.2 * inch, max_height=0.8 * inch)
    if firm_logo:
        logo_table = Table([[firm_logo, Paragraph("Clarion", styles["h2"])]], colWidths=[2.5 * inch, 3.3 * inch])
    else:
        logo_table = Table(
            [[Paragraph(f"<b>{firm_name}</b>", styles["h2"]), Paragraph("Clarion", styles["h2"])]],
            colWidths=[3.1 * inch, 2.7 * inch],
        )

    logo_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    flow.append(logo_table)
    flow.append(Spacer(1, 0.35 * inch))

    flow.append(Paragraph(report_title, styles["title"]))
    flow.append(Paragraph(f"<b>Prepared for:</b> {firm_name}", styles["cover_meta"]))
    flow.append(Paragraph(f"<b>Date range:</b> {date_range}", styles["cover_meta"]))
    flow.append(Paragraph(f"<b>Report date:</b> {report_date}", styles["cover_meta"]))
    flow.append(Paragraph(f"<b>Plan context:</b> {plan_label}", styles["cover_meta"]))

    cover_band = Table(
        [[Paragraph("Executive client feedback brief for partner and operations review.", styles["body"])]],
        colWidths=[6.3 * inch],
    )
    cover_band.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette["surface"]),
                ("BOX", (0, 0), (-1, -1), 1, palette["accent"]),
                ("TOPPADDING", (0, 0), (-1, -1), 16),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
            ]
        )
    )
    flow.append(Spacer(1, 0.25 * inch))
    flow.append(cover_band)
    flow.append(Spacer(1, 0.45 * inch))
    flow.append(Paragraph(PDF_COPY["prepared_by"], styles["subtitle"]))
    flow.append(Paragraph(PDF_COPY["site_url"], styles["small"]))
    return flow


def _build_executive_summary_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    positives: Sequence[str],
    needs_attention: Sequence[str],
    assessment: Dict[str, str],
) -> List[object]:
    flow: List[object] = [Paragraph("Executive Summary", styles["h1"])]

    tone_color = {
        "success": BASE_COLORS["success"],
        "warning": BASE_COLORS["warning"],
        "danger": BASE_COLORS["danger"],
    }.get(assessment.get("tone", "warning"), BASE_COLORS["warning"])

    badge = Table([[Paragraph(f"<b>Overall assessment:</b> {assessment['label']} - {assessment['summary']}", styles["body"])]], colWidths=[6.3 * inch])
    badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), palette["surface"]),
                ("BOX", (0, 0), (-1, -1), 1, tone_color),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    flow.append(badge)
    flow.append(Spacer(1, 0.2 * inch))

    working_rows: List[List[object]] = [[Paragraph("What is working", styles["h2"])]]
    for bullet in positives[:3]:
        working_rows.append([Paragraph(f"- {_clip(bullet, 145)}", styles["bullet"])])

    attention_rows: List[List[object]] = [[Paragraph("What needs attention", styles["h2"])]]
    for bullet in needs_attention[:3]:
        attention_rows.append([Paragraph(f"- {_clip(bullet, 145)}", styles["bullet"])])

    working_table = Table(working_rows, colWidths=[3.05 * inch])
    working_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BASE_COLORS["card"]),
                ("BOX", (0, 0), (-1, -1), 0.8, BASE_COLORS["border"]),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, BASE_COLORS["success"]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    attention_table = Table(attention_rows, colWidths=[3.05 * inch])
    attention_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BASE_COLORS["card"]),
                ("BOX", (0, 0), (-1, -1), 0.8, BASE_COLORS["border"]),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, BASE_COLORS["warning"]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    bullet_grid = Table([[working_table, attention_table]], colWidths=[3.1 * inch, 3.1 * inch])
    bullet_grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(bullet_grid)

    return flow


def _build_metrics_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    trend_points: Sequence[Dict[str, object]],
    total_reviews: int,
    avg_rating: float,
    sentiment_mix: Dict[str, int],
    at_risk: int,
    preview_mode: bool,
    theme_count: int,
) -> List[object]:
    flow: List[object] = [Paragraph("Key Metrics & Trends", styles["h1"])]

    chronological_points = _trend_points_chronological(trend_points)
    visible_points = chronological_points[-6:] if chronological_points else []
    labels = [
        str(
            point.get("label")
            or point.get("review_date_label")
            or _fmt_date(point.get("review_date_end") if point.get("review_date_end") else point.get("created_at"))
        )
        for point in visible_points
    ]
    scores = [_safe_float(point.get("avg_rating"), 0.0) for point in visible_points if point.get("avg_rating") is not None]
    volumes = [_safe_int(point.get("total_reviews"), 0) for point in visible_points]

    chart: Drawing
    chart_caption = "Trend history appears after multiple report snapshots are available."
    chart_width = 206
    chart_height = 150
    if len(scores) >= 2 and len(scores) == len(labels):
        chart = _line_chart(labels, scores, palette, width=chart_width, height=chart_height)
        data_through = _fmt_date(
            str(visible_points[-1].get("review_date_end") or visible_points[-1].get("created_at"))
            if visible_points
            else None
        )
        chart_caption = (
            f"Satisfaction moved from {scores[0]:.2f} to {scores[-1]:.2f} across the last {len(scores)} review-date periods "
            f"(data through {data_through})."
        )
    else:
        if not labels:
            labels = ["Current"]
        if not volumes:
            volumes = [total_reviews]
        chart = _bar_chart(labels, volumes, palette, width=chart_width, height=chart_height)
        chart_caption = "Review volume by period is shown until enough history exists for a stable satisfaction trend line."

    current_point = visible_points[-1] if visible_points else None
    previous_point = visible_points[-2] if len(visible_points) >= 2 else None
    current_risk_count, previous_risk_count = _windowed_risk_counts(trend_points)
    satisfaction_delta_label = "First report"
    satisfaction_delta_value = f"{avg_rating:.2f}/5"
    comparison_context_line = "No previous report is available for comparison."
    positive_delta_line = f"Positive share: {sentiment_mix['positive_pct']}% (comparison appears after next report)."
    risk_delta_line = f"At-risk signals: {current_risk_count} (comparison appears after next report)."
    if current_point and previous_point:
        current_avg = _safe_float(current_point.get("avg_rating"), avg_rating)
        previous_avg = _safe_float(previous_point.get("avg_rating"), current_avg)
        current_reviews = max(1, _safe_int(current_point.get("total_reviews"), total_reviews))
        previous_reviews = max(1, _safe_int(previous_point.get("total_reviews"), current_reviews))
        current_positive = _sentiment_mix(current_reviews, current_avg)["positive_pct"]
        previous_positive = _sentiment_mix(previous_reviews, previous_avg)["positive_pct"]
        avg_delta = current_avg - previous_avg
        pos_delta = current_positive - previous_positive
        risk_delta = current_risk_count - (previous_risk_count or 0)
        satisfaction_delta_label = f"{avg_delta:+.2f} vs last report"
        satisfaction_delta_value = f"{current_avg:.2f}/5"
        previous_generated = _fmt_date(previous_point.get("created_at") if previous_point.get("created_at") else None)
        previous_range = str(previous_point.get("review_date_label") or "").strip()
        comparison_context_line = (
            f"Baseline: previous report generated on {previous_generated}"
            + (f", covering {previous_range}." if previous_range else ".")
        )
        positive_delta_line = (
            f"Positive share: {current_positive}% vs {previous_positive}% ({pos_delta:+d} pts)"
        )
        risk_delta_line = (
            f"At-risk signals: {current_risk_count} vs {previous_risk_count if previous_risk_count is not None else 0} ({risk_delta:+d})"
        )

    metric_cards = [
        _metric_card("Total reviews analyzed", f"{total_reviews:,}", "Current report volume", styles, width=1.48 * inch),
        _metric_card("Overall satisfaction", f"{avg_rating:.2f}/5", "Current average rating", styles, width=1.48 * inch),
        _metric_card(
            "Sentiment split",
            f"{sentiment_mix['positive_pct']}/{sentiment_mix['neutral_pct']}/{sentiment_mix['negative_pct']}",
            "Positive/neutral/negative %",
            styles,
            width=1.48 * inch,
        ),
        _metric_card("At-risk reports", str(at_risk), "Current risk count", styles, width=1.48 * inch),
        _metric_card("Satisfaction delta", satisfaction_delta_label, "Compared with previous report", styles, width=1.48 * inch),
        _metric_card("Key themes detected", str(theme_count), "Recurring themes in this cycle", styles, width=1.48 * inch),
    ]
    if preview_mode:
        metric_cards = metric_cards[:4]

    grid_rows: List[List[object]] = []
    for i in range(0, len(metric_cards), 2):
        right = metric_cards[i + 1] if i + 1 < len(metric_cards) else Spacer(1, 0.02 * inch)
        grid_rows.append([metric_cards[i], right])
    metric_grid = Table(grid_rows, colWidths=[1.53 * inch, 1.53 * inch])
    metric_grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))

    left_col = Table(
        [
            [Paragraph("Satisfaction trend", styles["h2"])],
            [chart],
            [Paragraph(chart_caption, styles["small"])],
        ],
        colWidths=[3.17 * inch],
    )
    left_col.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BASE_COLORS["card"]),
                ("BOX", (0, 0), (-1, -1), 0.8, BASE_COLORS["border"]),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    right_col = Table([[Paragraph("Scorecard", styles["h2"])], [metric_grid]], colWidths=[3.05 * inch])
    right_col.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 0)]))

    layout = Table([[left_col, right_col]], colWidths=[3.22 * inch, 3.08 * inch])
    layout.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(layout)

    flow.append(Spacer(1, 0.14 * inch))
    comparison_lines = [
        f"Overall satisfaction now: {satisfaction_delta_value} ({satisfaction_delta_label}).",
        comparison_context_line,
        positive_delta_line,
        risk_delta_line,
    ]
    flow.append(_info_panel("Current vs previous report", comparison_lines, styles, palette))
    return flow

def _build_themes_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    themes: Sequence[Dict[str, float]],
    preview_mode: bool,
    avg_rating: float,
) -> List[object]:
    flow: List[object] = [Paragraph("Top Themes & Drivers", styles["h1"])]

    if not themes:
        flow.append(Paragraph("No recurring themes are available yet. Upload more review data to populate this section.", styles["body"]))
        return flow

    visible_limit = 2 if preview_mode else min(5, len(themes))
    visible_themes = themes[:visible_limit]
    theme_cards: List[object] = []
    for idx, theme in enumerate(visible_themes):
        theme_name = str(theme.get("name") or "Theme")
        mentions = _safe_int(theme.get("mentions"))
        share = _safe_float(theme.get("percentage"))
        sentiment_context = "positive reinforcement" if avg_rating >= 4.0 else "operational correction"
        insight = _theme_insight_sentence(theme_name)
        if idx == 0:
            insight = f"{insight} This is currently the highest-volume theme and a top {sentiment_context} priority."

        card = Table(
            [
                [Paragraph(f"<b>{theme_name}</b>", styles["h2"])],
                [Paragraph(f"{mentions} mentions | {share:.1f}% of comments", styles["small"])],
                [Paragraph(_clip(insight, 165), styles["body"])],
            ],
            colWidths=[3.05 * inch],
        )
        card.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), BASE_COLORS["card"]),
                    ("BOX", (0, 0), (-1, -1), 0.8, BASE_COLORS["border"]),
                    ("LINEBEFORE", (0, 0), (0, -1), 2.2, palette["accent"]),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        theme_cards.append(card)

    card_rows: List[List[object]] = []
    for idx in range(0, len(theme_cards), 2):
        right_card = theme_cards[idx + 1] if idx + 1 < len(theme_cards) else Spacer(1, 0.1 * inch)
        card_rows.append([theme_cards[idx], right_card])
    card_grid = Table(card_rows, colWidths=[3.1 * inch, 3.1 * inch])
    card_grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(card_grid)
    flow.append(Spacer(1, 0.12 * inch))

    chart_labels = [str(row.get("name") or f"T{idx + 1}")[:12] for idx, row in enumerate(themes[:8])]
    chart_points = [max(1, int(round(_safe_float(row.get("percentage"))))) for row in themes[:8]]
    flow.append(Paragraph("Theme share summary", styles["h2"]))
    flow.append(_bar_chart(chart_labels, chart_points, palette, width=392, height=150))

    flow.append(Spacer(1, 0.08 * inch))
    flow.append(CondPageBreak(2.0 * inch))
    summary_rows: List[List[object]] = [
        [
            Paragraph("<b>Theme</b>", styles["table_header"]),
            Paragraph("<b>Mentions</b>", styles["table_header"]),
            Paragraph("<b>Share</b>", styles["table_header"]),
            Paragraph("<b>Action owner</b>", styles["table_header"]),
        ]
    ]

    summary_limit = 5 if preview_mode else min(8, len(themes))
    for row in themes[:summary_limit]:
        theme_name = str(row.get("name") or "Theme")
        generated = None  # stub removed: build_theme_action always returned None)
        action_owner = PDF_COPY["default_role"]
        if isinstance(generated, dict):
            action_owner = str(generated.get("owner") or PDF_COPY["default_role"]).strip() or PDF_COPY["default_role"]
        summary_rows.append(
            [
                Paragraph(_clip(theme_name, 38), styles["table_cell"]),
                Paragraph(str(_safe_int(row.get("mentions"))), styles["table_cell"]),
                Paragraph(f"{_safe_float(row.get('percentage')):.1f}%", styles["table_cell"]),
                Paragraph(_clip(action_owner, 40), styles["table_cell"]),
            ]
        )

    table = Table(summary_rows, colWidths=[2.65 * inch, 1.0 * inch, 0.95 * inch, 1.7 * inch], repeatRows=1, splitByRow=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette["surface"]),
                ("GRID", (0, 0), (-1, -1), 0.5, BASE_COLORS["border"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, palette["surface"]]),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    flow.append(
        KeepTogether(
            [
                Paragraph("Theme detail table", styles["h2"]),
                Spacer(1, 0.03 * inch),
                table,
            ]
        )
    )

    return flow


def _build_action_plan_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    actions: Sequence[Dict[str, str]],
    preview_mode: bool,
    plan_type: str,
) -> List[object]:
    del plan_type
    flow: List[object] = [Paragraph("90-Day Action Plan", styles["h1"])]
    flow.append(Paragraph(PDF_COPY["action_preface"], styles["body"]))

    if preview_mode:
        visible_actions = list(actions[:2])
    else:
        visible_actions = list(actions[:5])
        if len(visible_actions) < 3:
            visible_actions = list(actions[:3])

    tracked_actions = [row for row in actions if str(row.get("title") or "").strip()]
    completed_actions = [
        row
        for row in tracked_actions
        if str(row.get("status") or "").strip().lower() in {"done", "completed"}
    ]

    timeframe_rank = {"0-30 days": 0, "31-60 days": 1, "61-90 days": 2}
    visible_actions.sort(key=lambda row: timeframe_rank.get(str(row.get("timeframe", "")).strip().lower(), 9))

    rows: List[List[object]] = [
        [
            Paragraph("<b>Action</b>", styles["table_header"]),
            Paragraph("<b>Owner</b>", styles["table_header"]),
            Paragraph("<b>Timeframe</b>", styles["table_header"]),
            Paragraph("<b>Success metric</b>", styles["table_header"]),
        ]
    ]
    for action in visible_actions:
        rows.append(
            [
                Paragraph(_clip(action.get("title", ""), 118), styles["table_cell"]),
                Paragraph(_clip(action.get("owner", PDF_COPY["default_role"]), 42), styles["table_cell"]),
                Paragraph(_clip(action.get("timeframe", "0-30 days"), 36), styles["table_cell"]),
                Paragraph(_clip(action.get("kpi", "Track outcome improvement"), 100), styles["table_cell"]),
            ]
        )

    action_table = Table(rows, colWidths=[2.15 * inch, 1.25 * inch, 0.9 * inch, 2.0 * inch], repeatRows=1, splitByRow=1)
    action_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette["surface"]),
                ("GRID", (0, 0), (-1, -1), 0.5, BASE_COLORS["border"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    flow.append(action_table)
    flow.append(Spacer(1, 0.14 * inch))

    owner_counts = Counter(_clip(str(action.get("owner") or PDF_COPY["default_role"]), 40) for action in visible_actions)
    primary_owner = owner_counts.most_common(1)[0][0] if owner_counts else PDF_COPY["default_role"]
    cadence = "Monthly partner review + 30-day owner checkpoints"
    execution_table = Table(
        [
            [
                _info_panel(
                    "Execution coverage",
                    [
                        f"{len(visible_actions)} actions scheduled across this 90-day cycle.",
                        f"Actions completed: {len(completed_actions)} of {len(tracked_actions)} tracked items.",
                    ],
                    styles,
                    palette,
                    2.03 * inch,
                ),
                _info_panel("Primary owner lane", [primary_owner], styles, palette, 2.03 * inch),
                _info_panel("Review cadence", [cadence], styles, palette, 2.03 * inch),
            ]
        ],
        colWidths=[2.1 * inch, 2.1 * inch, 2.1 * inch],
    )
    execution_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(execution_table)

    if preview_mode:
        upsell = Table(
            [[Paragraph("Preview shows top actions only. Paid plans include the full 90-day implementation plan.", styles["body"])]],
            colWidths=[6.3 * inch],
        )
        upsell.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), palette["surface"]),
                    ("BOX", (0, 0), (-1, -1), 1, palette["accent"]),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        flow.append(Spacer(1, 0.15 * inch))
        flow.append(upsell)

    return flow


def _quote_block(title: str, quotes: Sequence[Dict[str, str]], styles: Dict[str, ParagraphStyle], tone: str):
    accent = BASE_COLORS["success"] if tone == "positive" else BASE_COLORS["warning"]

    rows: List[List[object]] = [[Paragraph(f"<b>{title}</b>", styles["h2"])]]
    if quotes:
        for entry in quotes:
            quote_text = str(entry.get("text") or "")
            practice = _clip(str(entry.get("practice") or "General matter"), 36)
            sentiment = str(entry.get("sentiment") or tone).title()
            rows.append([Paragraph(f"\"{_clip(quote_text, 150)}\"", styles["quote"])])
            rows.append([Paragraph(f"{practice} | {sentiment}", styles["small"])])
            rows.append([Spacer(1, 0.03 * inch)])
    else:
        rows.append([Paragraph("No representative comments available in this section.", styles["small"])])

    table = Table(rows, colWidths=[3.05 * inch])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BASE_COLORS["card"]),
                ("BOX", (0, 0), (-1, -1), 0.8, BASE_COLORS["border"]),
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _build_comments_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    praise_quotes: Sequence[Dict[str, str]],
    complaint_quotes: Sequence[Dict[str, str]],
    preview_mode: bool,
) -> List[object]:
    flow: List[object] = [Paragraph("Representative Client Comments", styles["h1"])]

    positive_limit = 2 if preview_mode else 5
    critical_limit = 2 if preview_mode else 5

    quote_table = Table(
        [
            [
                _quote_block("What clients appreciate", praise_quotes[:positive_limit], styles, "positive"),
                _quote_block("Where clients struggle", complaint_quotes[:critical_limit], styles, "critical"),
            ]
        ],
        colWidths=[3.1 * inch, 3.1 * inch],
    )
    quote_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    flow.append(quote_table)
    flow.append(Spacer(1, 0.14 * inch))

    comment_takeaways = [
        "Use one positive and one critical quote to anchor the partner discussion with direct client language.",
        "Map each critical quote to an owner in the 90-day plan and review progress in the next cycle.",
        "Keep this section factual: what clients said, what changed, and what will be measured next.",
    ]
    flow.append(_info_panel("How to use these comments in leadership meetings", comment_takeaways, styles, palette))

    if preview_mode:
        flow.append(Spacer(1, 0.15 * inch))
        flow.append(Paragraph("Upgrade to access the full comment library and complete historical context.", styles["small"]))

    return flow


def _build_appendix_page(
    styles: Dict[str, ParagraphStyle],
    palette: Dict[str, colors.Color],
    themes: Sequence[Dict[str, float]],
    trend_points: Sequence[Dict[str, object]],
    preview_mode: bool,
) -> List[object]:
    flow: List[object] = [Paragraph(PDF_COPY["appendix_title"], styles["h1"])]
    flow.append(Paragraph("Reference detail for leadership and operations follow-up.", styles["small"]))

    theme_rows: List[List[object]] = [[
        Paragraph("<b>Theme</b>", styles["appendix_table_header"]),
        Paragraph("<b>Mentions</b>", styles["appendix_table_header"]),
        Paragraph("<b>Share</b>", styles["appendix_table_header"]),
    ]]
    theme_limit = 4 if preview_mode else min(15, len(themes))
    for row in themes[:theme_limit]:
        theme_rows.append(
            [
                Paragraph(str(row.get("name") or "Theme"), styles["appendix_table_cell"]),
                Paragraph(str(_safe_int(row.get("mentions"))), styles["appendix_table_cell"]),
                Paragraph(f"{_safe_float(row.get('percentage')):.1f}%", styles["appendix_table_cell"]),
            ]
        )

    theme_table = Table(theme_rows, colWidths=[3.8 * inch, 1.2 * inch, 1.3 * inch], repeatRows=1, splitByRow=1)
    theme_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette["surface"]),
                ("GRID", (0, 0), (-1, -1), 0.5, BASE_COLORS["border"]),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )
    flow.append(
        KeepTogether(
            [
                Paragraph("Theme breakdown", styles["h2"]),
                Spacer(1, 0.03 * inch),
                theme_table,
            ]
        )
    )
    flow.append(Spacer(1, 0.10 * inch))

    if trend_points:
        trend_rows: List[List[object]] = [[
            Paragraph("<b>Snapshot period</b>", styles["appendix_table_header"]),
            Paragraph("<b>Data through</b>", styles["appendix_table_header"]),
            Paragraph("<b>Generated</b>", styles["appendix_table_header"]),
            Paragraph("<b>Reviews</b>", styles["appendix_table_header"]),
            Paragraph("<b>Satisfaction</b>", styles["appendix_table_header"]),
        ]]
        timeline_by_date: Dict[str, Dict[str, object]] = {}
        timeline_order: List[str] = []
        for point in _trend_points_chronological(trend_points):
            point_end = point.get("review_date_end") if isinstance(point, dict) else None
            point_created = point.get("created_at") if isinstance(point, dict) else None
            snapshot_key = _fmt_date(str(point_end or point_created or ""))
            if snapshot_key not in timeline_by_date:
                timeline_by_date[snapshot_key] = {
                    "period_label": str(point.get("review_date_label") or point.get("label") or snapshot_key),
                    "data_through": snapshot_key,
                    "generated": _fmt_date(str(point_created or "")),
                    "reviews": 0,
                    "rating_total": 0.0,
                    "rating_count": 0,
                }
                timeline_order.append(snapshot_key)

            bucket = timeline_by_date[snapshot_key]
            bucket["reviews"] = _safe_int(bucket.get("reviews")) + _safe_int(point.get("total_reviews"))
            rating_val = _safe_float(point.get("avg_rating"))
            if rating_val > 0:
                bucket["rating_total"] = _safe_float(bucket.get("rating_total")) + rating_val
                bucket["rating_count"] = _safe_int(bucket.get("rating_count")) + 1
                bucket["generated"] = _fmt_date(str(point_created or ""))

        trend_limit = 6 if preview_mode else min(18, len(timeline_order))
        for snapshot_key in timeline_order[-trend_limit:]:
            bucket = timeline_by_date[snapshot_key]
            rating_count = _safe_int(bucket.get("rating_count"))
            satisfaction = "â€”"
            if rating_count > 0:
                satisfaction = f"{(_safe_float(bucket.get('rating_total')) / rating_count):.2f}"
            trend_rows.append(
                [
                    Paragraph(str(bucket.get("period_label") or snapshot_key), styles["appendix_table_cell"]),
                    Paragraph(str(bucket.get("data_through") or snapshot_key), styles["appendix_table_cell"]),
                    Paragraph(str(bucket.get("generated") or "N/A"), styles["appendix_table_cell"]),
                    Paragraph(str(_safe_int(bucket.get("reviews"))), styles["appendix_table_cell"]),
                    Paragraph(satisfaction, styles["appendix_table_cell"]),
                ]
            )

        trend_table = Table(
            trend_rows,
            colWidths=[1.7 * inch, 1.15 * inch, 1.5 * inch, 0.8 * inch, 1.15 * inch],
            repeatRows=1,
            splitByRow=1,
        )
        trend_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), palette["surface"]),
                    ("GRID", (0, 0), (-1, -1), 0.5, BASE_COLORS["border"]),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                ]
            )
        )
        flow.append(
            KeepTogether(
                [
                    Paragraph("Snapshot timeline (review-date based)", styles["h2"]),
                    Paragraph("Review counts reflect snapshot window totals.", styles["small"]),
                    Spacer(1, 0.03 * inch),
                    trend_table,
                ]
            )
        )

    if preview_mode:
        flow.append(Spacer(1, 0.08 * inch))
        flow.append(Paragraph("Preview appendix shown. Upgrade to unlock complete data tables and full historical comparisons.", styles["small"]))

    return flow

class DeckCanvas(canvas.Canvas):
    def __init__(self, *args, context: Optional[Dict[str, object]] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_states: List[dict] = []
        self.context = context or {}

    def showPage(self):
        self._saved_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_states)
        for state in self._saved_states:
            self.__dict__.update(state)
            self._draw_chrome(page_count)
            super().showPage()
        super().save()

    def _draw_chrome(self, total_pages: int):
        width, height = letter
        page_number = self._pageNumber

        palette = self.context.get("palette", _theme_palette("default"))
        assert isinstance(palette, dict)
        firm_name = _firm_display_name(self.context.get("firm_name"))

        self.setStrokeColor(BASE_COLORS["border"])
        self.setLineWidth(0.6)
        self.line(0.7 * inch, height - 0.55 * inch, width - 0.7 * inch, height - 0.55 * inch)

        # Keep the top rule without repeating section text in page chrome.

        self.line(0.7 * inch, 0.55 * inch, width - 0.7 * inch, 0.55 * inch)
        self.setFont("Helvetica", 9.5)
        self.setFillColor(BASE_COLORS["muted"])
        footer_date = _format_brief_date(str(self.context.get("exported_at") or self.context.get("report_date") or ""))
        page_text = f"Page {page_number} of {max(1, total_pages)}"
        left_x = 0.72 * inch
        right_x = width - 0.72 * inch
        footer_text = f"Clarion \u2014 Confidential Governance Document | {footer_date} | {page_text}"
        footer_max_width = right_x - left_x
        footer_text_fit = _fit_text_to_width(self, footer_text, "Helvetica", 9.5, footer_max_width)
        self.drawString(left_x, 0.37 * inch, footer_text_fit)
        version_text = f"{PDF_TEMPLATE_VERSION}"
        self.setFont("Helvetica", 8.2)
        self.drawString(left_x, 0.21 * inch, version_text)
        self.setFont("Helvetica", 9.5)

        logo_path = self.context.get("logo_path")
        if isinstance(logo_path, str) and _logo_canvas_supported(logo_path):
            try:
                self.drawImage(logo_path, width - 2.2 * inch, 0.18 * inch, width=0.45 * inch, height=0.26 * inch, mask="auto")
            except Exception:  # noqa: BLE001
                pass

        if bool(self.context.get("preview_mode")):
            self.saveState()
            self.setFillColor(colors.Color(0.86, 0.88, 0.92, alpha=0.22))
            self.setFont("Helvetica-Bold", 42)
            self.translate(width / 2.0, height / 2.0)
            self.rotate(34)
            self.drawCentredString(0, 0, PDF_COPY["preview_watermark"])
            self.restoreState()


def generate_pdf_report(
    firm_name,
    total_reviews,
    avg_rating,
    themes,
    top_praise,
    top_complaints,
    is_paid_user=False,
    subscription_type="monthly",
    analysis_period=None,
    access_level="trial",
    plan_type="free",
    report_title="Governance Brief",
    report_created_at=None,
    trend_points=None,
    implementation_items=None,
    branding=None,
    governance_brief_at=None,
    governance_delta_baseline_at=None,
    participants=None,
    exported_by=None,
    exported_role=None,
    exported_at=None,
    version_hash=None,
    exposure_snapshot=None,
    governance_signals=None,
    governance_recommendations=None,
):
    """
    Generate a standardized executive-brief PDF using existing report data only.
    """
    del subscription_type  # backward compatibility

    environment = str(os.environ.get("FLASK_ENV") or "").strip().lower()
    is_dev = environment == "development"
    snapshot_obj = exposure_snapshot if isinstance(exposure_snapshot, dict) else None
    if snapshot_obj is None:
        if is_dev:
            LOGGER.warning(
                "Exposure canonical snapshot missing in generate_pdf_report(); using DEV-only fallback exposure logic."
            )
        else:
            raise RuntimeError("Exposure snapshot is required for Governance Brief generation in production.")

    total_reviews_int = max(0, _safe_int(total_reviews))
    avg_rating_float = max(0.0, min(5.0, _safe_float(avg_rating, 0.0)))
    normalized_themes = _normalize_themes(themes)
    if normalized_themes is None:  # defensive guard for unexpected monkeypatching/overrides
        normalized_themes = []
    praise_quote_entries = _normalize_quote_entries(top_praise, "positive")
    complaint_quote_entries = _normalize_quote_entries(top_complaints, "negative")
    praise_quotes = _quote_texts(praise_quote_entries)
    complaint_quotes = _quote_texts(complaint_quote_entries)
    trend_points_list = list(trend_points or [])
    action_rows = list(implementation_items or [])
    if action_rows is None:  # defensive guard if list() behavior is altered
        action_rows = []
    governance_signal_rows = list(governance_signals or [])
    if governance_signal_rows is None:
        governance_signal_rows = []
    governance_recommendation_rows = list(governance_recommendations or [])
    if governance_recommendation_rows is None:
        governance_recommendation_rows = []

    branding = branding or {}
    accent_theme = str(branding.get("accent_theme") or "default")
    palette = _theme_palette(accent_theme)
    logo_path = branding.get("logo_path") if isinstance(branding.get("logo_path"), str) else None

    normalized_plan = str(plan_type or "free")
    preview_mode = normalized_plan == "free" or str(access_level or "trial") == "trial" or not bool(is_paid_user)
    plan_label_map = {
        "free": "Free",
        "one_time": "Free",
        "pro_monthly": "Team",
        "pro_annual": "Firm",
    }
    plan_label = plan_label_map.get(normalized_plan, "Free Preview" if preview_mode else "Paid")

    sentiment_mix = _sentiment_mix(total_reviews_int, avg_rating_float)
    trend_stability = _trend_stability_from_points(trend_points_list)
    assessment = _assessment(avg_rating_float, trend_stability)
    at_risk_reports = _at_risk_count(trend_points_list)
    positives, needs_attention = _derive_summary_bullets(
        avg_rating_float,
        trend_stability,
        normalized_themes,
        sentiment_mix,
        praise_quotes,
        complaint_quotes,
    )
    action_items = _derive_action_items(action_rows, normalized_themes or [])
    normalized_action_rows = _normalize_action_rows(action_rows)

    report_date = _fmt_report_date(report_created_at)
    exported_at_label = _format_export_timestamp(exported_at or report_created_at)
    date_range = _compute_date_range(trend_points_list, analysis_period, report_created_at)

    display_title = "Clarion"

    styles = _build_styles(palette)
    participant_names: List[str] = []
    if isinstance(participants, (list, tuple)):
        participant_names = [str(name).strip() for name in participants if str(name).strip()]
    participants_line = ", ".join(participant_names) if participant_names else "â€”"

    points = _trend_points_chronological(trend_points_list)
    current_point = points[-1] if points else {}
    previous_point = points[-2] if len(points) > 1 else {}
    current_score = _safe_float(current_point.get("avg_rating"), avg_rating_float) if isinstance(current_point, dict) else avg_rating_float
    previous_score = _safe_float(previous_point.get("avg_rating"), current_score) if isinstance(previous_point, dict) else current_score
    score_delta: Optional[float] = None
    if isinstance(previous_point, dict) and previous_point:
        score_delta = current_score - previous_score

    now = datetime.utcnow()
    completed_actions = 0
    open_actions = 0
    overdue_actions = 0
    for row in normalized_action_rows:
        status = str(row.get("status") or "open").lower()
        bucket = _status_bucket(status)
        due_dt = _parse_iso(row.get("due_date"))
        is_overdue = bucket != "completed" and bool(due_dt and due_dt < now)
        if is_overdue:
            overdue_actions += 1
        if bucket == "completed":
            completed_actions += 1
        else:
            open_actions += 1

    if snapshot_obj is not None:
        exposure_status = str(snapshot_obj.get("exposure_label") or "Baseline").strip() or "Baseline"
        escalation_required = "Yes" if bool(snapshot_obj.get("partner_escalation_required")) else "No"
    else:
        exposure_status = "Baseline"
        if overdue_actions > 0 or at_risk_reports > 0:
            exposure_status = "High"
        elif trend_stability in {"Moderately stable", "Volatile"} or (score_delta is not None and score_delta < 0):
            exposure_status = "Watchlist"
        escalation_required = "Yes" if exposure_status == "High" else "No"

    top_theme = {"name": "Uncategorized", "percentage": 0.0}
    if normalized_themes:
        friction_tokens = ("commun", "respons", "wait", "bill", "cost", "fee", "support", "delay", "friction", "complaint")
        strength_tokens = ("outcome", "result", "expert", "legal", "professional")
        scored = []
        for row in normalized_themes:
            name = str(row.get("name") or "").lower()
            share = _safe_float(row.get("percentage"))
            score = share
            if any(token in name for token in friction_tokens):
                score += 25.0
            if any(token in name for token in strength_tokens):
                score -= 10.0
            scored.append((score, row))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        top_theme = scored[0][1]
    top_theme_name = str(top_theme.get("name") or "Uncategorized")
    top_theme_share = f"{_safe_float(top_theme.get('percentage')):.1f}%"
    primary_risk_driver = f"{top_theme_name} ({top_theme_share})"
    responsible_owner = "Unassigned (requires assignment)"
    for row in normalized_action_rows:
        owner = str(row.get("owner") or "").strip()
        theme_name = str(row.get("theme") or "").strip().lower()
        if owner and owner.lower() != "unassigned" and theme_name and theme_name == top_theme_name.lower():
            responsible_owner = owner
            break
    if responsible_owner == "Unassigned (requires assignment)":
        for row in normalized_action_rows:
            owner = str(row.get("owner") or "").strip()
            if owner and owner.lower() != "unassigned":
                responsible_owner = owner
                break

    snapshot_driver = str((snapshot_obj or {}).get("primary_risk_driver") or "").strip()
    if snapshot_driver:
        primary_risk_driver = snapshot_driver
    snapshot_owner = str((snapshot_obj or {}).get("responsible_owner") or "").strip()
    if snapshot_owner:
        responsible_owner = snapshot_owner

    baseline_override = str(governance_delta_baseline_at or "").strip() or None
    last_brief_override = str(governance_brief_at or "").strip() or baseline_override
    last_brief_date_value: Optional[str] = baseline_override
    if not last_brief_date_value and isinstance(previous_point, dict):
        last_brief_date_value = str(previous_point.get("review_date_end") or previous_point.get("created_at") or "").strip() or None
    last_brief_date = _fmt_date(last_brief_date_value) if last_brief_date_value else "TBD"
    baseline_dt = _parse_iso(last_brief_date_value) if last_brief_date_value else None
    if last_brief_override:
        last_brief_date = _fmt_date(last_brief_override)

    current_risk_window, previous_risk_window = _windowed_risk_counts(trend_points_list)
    if previous_risk_window is None:
        delta_at_risk = "TBD"
    else:
        delta_at_risk = str(current_risk_window - previous_risk_window)

    if baseline_dt:
        delta_completed_int = sum(
            1
            for row in normalized_action_rows
            if _status_bucket(str(row.get("status") or "")) == "completed"
            and _parse_iso(row.get("updated_at"))
            and _parse_iso(row.get("updated_at")) >= baseline_dt
        )
        delta_opened_int = sum(
            1
            for row in normalized_action_rows
            if _parse_iso(row.get("created_at")) and _parse_iso(row.get("created_at")) >= baseline_dt
        )
        delta_completed = str(delta_completed_int)
        delta_opened = str(delta_opened_int)
    else:
        delta_completed = "TBD"
        delta_opened = "TBD"

    score_symbol = "\u2014"
    score_value = "\u2014"
    if score_delta is not None:
        score_symbol = "+" if score_delta >= 0 else "-"
        score_value = f"{abs(score_delta):.2f}"
    satisfaction_line = f"{current_score:.2f} ({score_symbol}{score_value})"
    delta_satisfaction = f"{score_symbol}{score_value}" if score_delta is not None else "â€”"
    direction_symbol = "â†”"
    if score_delta is not None:
        direction_symbol = "â†‘" if score_delta > 0 else ("â†“" if score_delta < 0 else "â†’")

    integrity_messages: List[str] = []
    if responsible_owner == "Unassigned (requires assignment)":
        integrity_messages.append("\u26A0 Owner Unassigned - assign during session.")
    if exposure_status == "High" and open_actions == 0:
        integrity_messages.append("\u26A0 Governance Gap Detected - High exposure exists without assigned mitigation actions.")
    if overdue_actions > 0:
        integrity_messages.append("\u26A0 Overdue Governance Actions Present - Immediate review recommended.")
    if exposure_status == "Baseline" and overdue_actions == 0:
        integrity_messages.append("\u2713 Governance exposure controlled and current.")
    if not integrity_messages:
        integrity_messages.append("â€”")

    pages: List[Tuple[str, List[object]]] = []
    negative_themes = _top_negative_themes(normalized_themes, limit=3)
    pages.append(
        (
            "Governance Snapshot",
            _build_governance_snapshot_page(
                styles,
                palette,
                firm_name=_firm_display_name(str(firm_name or "")),
                export_date=report_date,
                participants_line=participants_line,
                exported_by=str(exported_by or "Unknown"),
                exported_role=str(exported_role or "member"),
                exported_at=exported_at_label,
                version_hash=str(version_hash or "n/a"),
                exposure_status=exposure_status,
                escalation_required=escalation_required,
                primary_risk_driver=primary_risk_driver,
                responsible_owner=responsible_owner,
                at_risk_matters=str(at_risk_reports),
                open_actions=str(open_actions),
                overdue_actions=str(overdue_actions),
                satisfaction_line=satisfaction_line,
                last_brief_date=last_brief_date,
                delta_at_risk=delta_at_risk,
                delta_opened=delta_opened,
                delta_completed=delta_completed,
                delta_satisfaction=delta_satisfaction,
                governance_signals=governance_signal_rows,
                governance_recommendations=governance_recommendation_rows,
                integrity_messages=integrity_messages,
            ),
        )
    )
    pages.append(("Execution Accountability", _build_execution_accountability_page(styles, palette, normalized_action_rows, exposure_status, negative_themes)))
    pages.append(("Top Negative Drivers", _build_risk_drivers_page(styles, normalized_themes, direction_symbol)))
    pages.append(("Client Signals", _build_client_signals_page(styles, praise_quote_entries, complaint_quote_entries)))
    pages.append(
        (
            "Appendix â€“ Supporting Metrics",
            [
                Paragraph("Appendix â€“ Supporting Metrics", styles["h1"]),
                Paragraph("Supporting metrics are provided below as tables.", styles["body"]),
                Spacer(1, 0.04 * inch),
                *_build_positive_reinforcements_page(styles, normalized_themes),
                Spacer(1, 0.04 * inch),
                *_build_appendix_page(styles, palette, normalized_themes, trend_points_list, preview_mode),
            ],
        )
    )

    story: List[object] = []
    page_labels: List[str] = []
    for index, (label, flowables) in enumerate(pages):
        page_labels.append(label)
        story.extend(flowables)
        if index < len(pages) - 1:
            story.append(PageBreak())

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.6 * inch,
        bottomMargin=1.0 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        title=display_title,
        author="Clarion",
    )

    context = {
        "palette": palette,
        "preview_mode": preview_mode,
        "page_sections": page_labels,
        "firm_name": firm_name or "Your Firm",
        "report_title": display_title,
        "report_date": report_date,
        "logo_path": logo_path,
        "exported_by": exported_by or "Unknown",
        "exported_role": exported_role or "member",
        "exported_at": exported_at or datetime.utcnow().isoformat(),
        "version_hash": version_hash or "n/a",
    }

    doc.build(story, canvasmaker=lambda *args, **kwargs: DeckCanvas(*args, context=context, **kwargs))

    buffer.seek(0)
    return buffer





