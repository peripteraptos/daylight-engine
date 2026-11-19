"""Render the documentation images in docs/ from the engine (requires matplotlib).

python scripts/render_docs.py
"""

from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from custom_components.daylight_engine.engine import (  # noqa: E402
    RgbSegment,
    TargetConfig,
    compute_target,
    profile_from_dict,
    solar_position,
)
from custom_components.daylight_engine.engine.color import kelvin_to_rgb  # noqa: E402

OUT = ROOT / "docs"
LAT, LON, TZ = 52.52, 13.405, ZoneInfo("Europe/Berlin")

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e6e5e1"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]

plt.rcParams.update(
    {
        "font.family": "Inter",
        "font.size": 10,
        "text.color": INK,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": GRID,
        "axes.facecolor": SURFACE,
        "figure.facecolor": SURFACE,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
    }
)


def day_series(day: date, step: int = 5):
    start = datetime.combine(day, datetime.min.time(), tzinfo=TZ)
    config = TargetConfig()
    times, kelvins, brightness, elevations = [], [], [], []
    for minute in range(0, 24 * 60 + 1, step):
        when = start + timedelta(minutes=minute)
        pos = solar_position(when, LAT, LON)
        t = compute_target(pos, config)
        times.append(when.replace(tzinfo=None))
        kelvins.append(t.kelvin)
        brightness.append(t.brightness)
        elevations.append(pos.elevation)
    return times, kelvins, brightness, elevations


def light_color(kelvin: float) -> tuple[float, float, float]:
    return tuple(c / 255 for c in kelvin_to_rgb(kelvin))  # type: ignore[return-value]


def sun_crossings(times, elevations):
    out = []
    for (t0, e0), (t1, e1) in zip(
        zip(times, elevations, strict=False), zip(times[1:], elevations[1:], strict=False), strict=False
    ):
        if (e0 < 0) != (e1 < 0):
            out.append((t0 + (t1 - t0) * (-e0 / (e1 - e0)), e1 > 0))
    return out


def time_axis(ax):
    ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 25, 3)))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))


def title(fig, main: str, sub: str):
    fig.text(0.04, 0.965, main, fontsize=14, fontweight="semibold", va="top")
    fig.text(0.04, 0.915, sub, fontsize=10, color=INK_2, va="top")


def render_today(day: date):
    times, kelvins, brightness, elevations = day_series(day)
    fig, (ax_k, ax_b) = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True, dpi=160)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.82, bottom=0.08, hspace=0.35)
    title(
        fig,
        f"Tagesverlauf {day:%d.%m.%Y} · Berlin",
        "Globaler Zielwert mit Standardeinstellungen – Linienfarbe = berechnete Lichtfarbe",
    )

    x = mdates.date2num(times)
    for ax, values, label, unit in (
        (ax_k, kelvins, "Farbtemperatur", "K"),
        (ax_b, brightness, "Helligkeit (logisch)", "%"),
    ):
        ax.fill_between(x, values, min(values) * (0.92 if unit == "K" else 0), color=GRID, alpha=0.35, lw=0)
        pts = list(zip(x, values, strict=False))
        segs = [pts[i : i + 2] for i in range(len(pts) - 1)]
        lc = LineCollection(segs, colors=[light_color(k) for k in kelvins[:-1]], linewidths=4.5)
        ax.add_collection(lc)
        ax.plot(x, values, color=INK_2, lw=1.1, alpha=0.8)
        ax.set_title(label, loc="left", fontsize=10.5, color=INK, fontweight="medium", pad=8)
        ax.yaxis.set_major_formatter(lambda v, _p, u=unit: f"{v:,.0f} {u}".replace(",", "."))
        for when, rising in sun_crossings(times, elevations):
            ax.axvline(when, color=MUTED, lw=1, ls=(0, (3, 3)))
            if ax is ax_k:
                ax.annotate(
                    f"{'Sonnenaufgang' if rising else 'Sonnenuntergang'} {when:%H:%M}",
                    (mdates.date2num(when), max(values)),
                    xytext=(6, -2),
                    textcoords="offset points",
                    fontsize=9,
                    color=INK_2,
                    va="top",
                )
    ax_k.set_ylim(min(kelvins) * 0.92, max(kelvins) * 1.06)
    ax_b.set_ylim(0, 108)
    ax_b.set_xlim(x[0], x[-1])
    time_axis(ax_b)
    fig.savefig(OUT / "01_tagesverlauf_heute.png")
    plt.close(fig)


def render_seasons():
    days = [
        (date(2026, 6, 21), "21. Juni"),
        (date(2026, 11, 19), "19. Nov."),
        (date(2026, 12, 21), "21. Dez."),
    ]
    fig, ax = plt.subplots(figsize=(10, 5), dpi=160)
    fig.subplots_adjust(left=0.08, right=0.88, top=0.8, bottom=0.1)
    title(
        fig,
        "Farbtemperatur im Jahresverlauf · Berlin",
        "Gleiche Einstellungen – der Verlauf folgt dem Sonnenstand",
    )
    base = date(2026, 1, 1)
    for (day, label), color in zip(days, SERIES, strict=False):
        times, kelvins, _, _ = day_series(day)
        xs = [datetime.combine(base, t.time()) for t in times]
        xs[-1] = datetime.combine(base, datetime.min.time()) + timedelta(days=1)
        ax.plot(xs, kelvins, color=color, lw=2, label=label, solid_capstyle="round")
    ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False, labelcolor=INK_2)
    ax.yaxis.set_major_formatter(lambda v, _p: f"{v:,.0f} K".replace(",", "."))
    ax.set_xlim(
        datetime.combine(base, datetime.min.time()),
        datetime.combine(base, datetime.min.time()) + timedelta(days=1),
    )
    time_axis(ax)
    fig.savefig(OUT / "02_jahreszeiten.png")
    plt.close(fig)


def render_profile():
    profile = profile_from_dict(json.loads((ROOT / "examples" / "rgb_cct_profile.json").read_text()))
    kelvin = 2400
    logical = [i / 10 for i in range(1, 1001)]
    cmds = [profile.resolve(v, kelvin) for v in logical]
    device = [c.brightness / 255 * 100 for c in cmds]

    fig = plt.figure(figsize=(10, 5.6), dpi=160)
    gs = fig.add_gridspec(
        2, 1, height_ratios=[5, 0.7], hspace=0.12, left=0.08, right=0.97, top=0.8, bottom=0.1
    )
    ax = fig.add_subplot(gs[0])
    strip = fig.add_subplot(gs[1], sharex=ax)
    title(
        fig,
        "Lampenprofil »Beispiel RGB+CCT«",
        f"Logische Helligkeit → Gerätebefehl bei {kelvin} K · 0–10 % RGB-Modus, 10–100 % CCT 1–100 %",
    )

    start = 0.0
    for i, seg in enumerate(profile.segments):
        is_rgb = isinstance(seg, RgbSegment)
        ax.axvspan(start, seg.end, color=SERIES[1] if is_rgb else SERIES[0], alpha=0.07, lw=0)
        ax.text(
            (start + seg.end) / 2 if is_rgb else start + 3,
            97,
            "RGB" if is_rgb else "CCT",
            ha="center" if is_rgb else "left",
            va="top",
            fontsize=9.5,
            fontweight="medium",
            color=INK_2,
        )
        if i:
            ax.axvline(start, color=MUTED, lw=1, ls=(0, (3, 3)))
        start = seg.end

    rgb_mask = [c.rgb_color is not None for c in cmds]
    for mask, color, label in (
        (rgb_mask, SERIES[1], "RGB-Segment"),
        ([not m for m in rgb_mask], SERIES[0], "CCT-Segment"),
    ):
        xs = [x for x, m in zip(logical, mask, strict=False) if m]
        ys = [y for y, m in zip(device, mask, strict=False) if m]
        ax.plot(xs, ys, color=color, lw=2, label=label, solid_capstyle="round")
    for seg in profile.segments:
        ax.scatter(
            [p.logical for p in seg.points],
            [p.device for p in seg.points],
            s=36,
            color=INK,
            zorder=5,
            edgecolor=SURFACE,
            linewidth=1.5,
            clip_on=False,
        )
    ax.annotate(
        "Kalibrierpunkte: 40 % im RGB-Modus ≈ 1 % CCT\n(wird in Phase 3 pro Lampe eingemessen)",
        (10, 40),
        xytext=(16, 52),
        textcoords="data",
        fontsize=9,
        color=INK_2,
        arrowprops={"arrowstyle": "-", "color": MUTED, "lw": 1},
    )
    ax.set_ylabel("Geräte-Helligkeit (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower right", frameon=False, labelcolor=INK_2)
    plt.setp(ax.get_xticklabels(), visible=False)

    colors = []
    for v, c in zip(logical, cmds, strict=False):
        rgb = c.rgb_color or kelvin_to_rgb(c.color_temp_kelvin or kelvin)
        scale = 0.3 + 0.7 * (v / 100) ** 0.5
        colors.append([min(1, ch / 255 * scale) for ch in rgb])
    strip.imshow([colors], aspect="auto", extent=(0, 100, 0, 1))
    strip.set_yticks([])
    strip.grid(False)
    strip.set_xlabel("Logische Helligkeit (%)")
    strip.set_xlim(0, 100)
    strip.text(-1, 0.5, "Lichtfarbe", ha="right", va="center", fontsize=9, color=INK_2)
    fig.savefig(OUT / "03_lampenprofil.png")
    plt.close(fig)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    render_today(date(2026, 11, 19))
    render_seasons()
    render_profile()
    print("written to", OUT)
