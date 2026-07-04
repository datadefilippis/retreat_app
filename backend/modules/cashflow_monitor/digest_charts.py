"""
Digest Charts — Matplotlib chart generation for PDF reports.

All functions return PNG bytes (BytesIO). No files written to disk.
Brand colors: blue=#2563EB, green=#16A34A, red=#DC2626, gray=#6B7280.
"""

import io
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend (no GUI)
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np


# ── Brand colors ─────────────────────────────────────────────────────────────
BLUE = "#2563EB"
GREEN = "#16A34A"
RED = "#DC2626"
AMBER = "#F59E0B"
GRAY = "#6B7280"
LIGHT_GRAY = "#F3F4F6"
WHITE = "#FFFFFF"

# ── Locale labels ────────────────────────────────────────────────────────────
_LABELS = {
    "it": {"revenue": "Ricavi", "expenses": "Uscite", "cumulative": "Cashflow cumulativo", "categories": "Categorie"},
    "en": {"revenue": "Revenue", "expenses": "Expenses", "cumulative": "Cumulative cashflow", "categories": "Categories"},
    "de": {"revenue": "Einnahmen", "expenses": "Ausgaben", "cumulative": "Kumulierter Cashflow", "categories": "Kategorien"},
    "fr": {"revenue": "Revenus", "expenses": "Dépenses", "cumulative": "Cashflow cumulé", "categories": "Catégories"},
}

_WEEKDAYS = {
    "it": ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"],
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "de": ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
    "fr": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
}


def _setup_style():
    """Apply clean, modern chart style."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.15,
        "grid.linestyle": "-",
        "figure.facecolor": WHITE,
        "axes.facecolor": WHITE,
    })


def _to_bytes(fig) -> bytes:
    """Convert matplotlib figure to PNG bytes and close."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=WHITE, edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _fmt_eur(val: float) -> str:
    """Format EUR value for chart labels."""
    if abs(val) >= 1_000_000:
        return f"€{val / 1_000_000:.1f}M"
    if abs(val) >= 1_000:
        return f"€{val / 1_000:.1f}k"
    return f"€{val:.0f}"


def generate_daily_chart(
    sales_by_date: Dict[str, float],
    expenses_by_date: Dict[str, float],
    purchases_by_date: Optional[Dict[str, float]] = None,
    locale: str = "it",
) -> bytes:
    """Grouped bar chart: revenue vs total outflows per day."""
    _setup_style()
    labels = _LABELS.get(locale, _LABELS["it"])

    dates = sorted(set(list(sales_by_date.keys()) + list(expenses_by_date.keys())))
    if not dates:
        return _empty_chart(labels["revenue"])

    revenues = [sales_by_date.get(d, 0) for d in dates]
    expenses = [expenses_by_date.get(d, 0) + (purchases_by_date or {}).get(d, 0) for d in dates]

    # Use short day labels if <= 14 days, else dates
    if len(dates) <= 14:
        from datetime import date as dt_date
        x_labels = []
        weekdays = _WEEKDAYS.get(locale, _WEEKDAYS["it"])
        for d in dates:
            try:
                day = dt_date.fromisoformat(d)
                x_labels.append(f"{weekdays[day.weekday()]}\n{day.day}")
            except Exception:
                x_labels.append(d[-5:])
    else:
        x_labels = [d[-5:] for d in dates]  # MM-DD

    x = np.arange(len(dates))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 3.5))
    bars1 = ax.bar(x - width / 2, revenues, width, label=labels["revenue"],
                   color=BLUE, alpha=0.85, zorder=3)
    bars2 = ax.bar(x + width / 2, expenses, width, label=labels["expenses"],
                   color=RED, alpha=0.65, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=7)
    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_eur(v)))
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_ylabel("")
    fig.tight_layout()

    return _to_bytes(fig)


def generate_cumulative_chart(
    sales_by_date: Dict[str, float],
    expenses_by_date: Dict[str, float],
    purchases_by_date: Optional[Dict[str, float]] = None,
    locale: str = "it",
) -> bytes:
    """Area chart: cumulative net cashflow over time."""
    _setup_style()
    labels = _LABELS.get(locale, _LABELS["it"])

    dates = sorted(set(list(sales_by_date.keys()) + list(expenses_by_date.keys())))
    if not dates:
        return _empty_chart(labels["cumulative"])

    cumulative = []
    running = 0.0
    for d in dates:
        rev = sales_by_date.get(d, 0)
        exp = expenses_by_date.get(d, 0) + (purchases_by_date or {}).get(d, 0)
        running += rev - exp
        cumulative.append(running)

    fig, ax = plt.subplots(figsize=(8, 3))
    x = range(len(dates))

    # Fill positive green, negative red
    cumulative_arr = np.array(cumulative)
    ax.fill_between(x, cumulative_arr, 0,
                     where=cumulative_arr >= 0, color=GREEN, alpha=0.2, zorder=2)
    ax.fill_between(x, cumulative_arr, 0,
                     where=cumulative_arr < 0, color=RED, alpha=0.2, zorder=2)
    ax.plot(x, cumulative, color=BLUE, linewidth=2, zorder=3)
    ax.axhline(y=0, color=GRAY, linewidth=0.5, linestyle="--", zorder=1)

    # X labels
    if len(dates) <= 14:
        ax.set_xticks(list(x))
        ax.set_xticklabels([d[-5:] for d in dates], fontsize=7)
    else:
        step = max(1, len(dates) // 10)
        ax.set_xticks(list(x)[::step])
        ax.set_xticklabels([dates[i][-5:] for i in range(0, len(dates), step)], fontsize=7)

    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_eur(v)))
    ax.set_title(labels["cumulative"], fontsize=11, fontweight="bold", loc="left")
    fig.tight_layout()

    return _to_bytes(fig)


def generate_category_chart(
    categories: List[dict],
    title: str = "",
    locale: str = "it",
    color: str = BLUE,
    max_items: int = 6,
) -> bytes:
    """Horizontal bar chart: top categories by amount."""
    _setup_style()

    if not categories:
        return _empty_chart(title or "Categories")

    items = categories[:max_items]
    items.reverse()  # Largest on top

    names = [item.get("_id") or item.get("category", "?") for item in items]
    values = [item.get("total", 0) for item in items]

    # Truncate long names
    names = [n[:20] + "..." if len(n) > 20 else n for n in names]

    fig, ax = plt.subplots(figsize=(5, max(2, len(items) * 0.5 + 0.5)))
    bars = ax.barh(range(len(names)), values, color=color, alpha=0.8, height=0.6, zorder=3)

    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=8)
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: _fmt_eur(v)))

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                _fmt_eur(val), va="center", fontsize=7, color=GRAY)

    if title:
        ax.set_title(title, fontsize=10, fontweight="bold", loc="left")

    ax.invert_yaxis()
    fig.tight_layout()

    return _to_bytes(fig)


def generate_health_gauge(score: int, label: str = "", locale: str = "it") -> bytes:
    """Semi-circular gauge for health score (0-100)."""
    _setup_style()

    fig, ax = plt.subplots(figsize=(3, 2), subplot_kw={"projection": "polar"})

    # Gauge background
    theta_bg = np.linspace(np.pi, 0, 100)
    ax.fill_between(theta_bg, 0.6, 1.0, color=LIGHT_GRAY, alpha=0.5)

    # Gauge fill (proportional to score)
    score_clamped = max(0, min(100, score))
    theta_fill = np.linspace(np.pi, np.pi - (score_clamped / 100) * np.pi, 50)

    if score_clamped >= 70:
        gauge_color = GREEN
    elif score_clamped >= 40:
        gauge_color = AMBER
    else:
        gauge_color = RED

    ax.fill_between(theta_fill, 0.6, 1.0, color=gauge_color, alpha=0.8)

    # Center text
    ax.text(np.pi / 2, 0.0, str(score), ha="center", va="center",
            fontsize=28, fontweight="bold", color=gauge_color,
            transform=ax.transData)
    ax.text(np.pi / 2, -0.3, "/100", ha="center", va="center",
            fontsize=10, color=GRAY, transform=ax.transData)
    if label:
        ax.text(np.pi / 2, -0.55, label, ha="center", va="center",
                fontsize=9, color=GRAY, transform=ax.transData)

    ax.set_ylim(0, 1.2)
    ax.set_theta_zero_location("W")
    ax.set_thetamin(0)
    ax.set_thetamax(180)
    ax.axis("off")
    fig.tight_layout()

    return _to_bytes(fig)


def _empty_chart(title: str = "") -> bytes:
    """Generate a placeholder chart when no data is available."""
    _setup_style()
    fig, ax = plt.subplots(figsize=(5, 2))
    ax.text(0.5, 0.5, "No data available", ha="center", va="center",
            fontsize=12, color=GRAY, transform=ax.transAxes)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10, fontweight="bold", loc="left")
    fig.tight_layout()
    return _to_bytes(fig)
