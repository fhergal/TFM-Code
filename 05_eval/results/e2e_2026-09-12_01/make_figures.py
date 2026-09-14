"""Genera las figuras de resultados (SVG, sin dependencias externas -- no hay
matplotlib instalado en .venv ni en el sistema, y no se quiere alterar el
entorno congelado del pre-run) a partir de los JSON de metricas ya calculados:

  - resultados_sensibilidad_umbral_completo.json   (barrido naive_retriever)
  - config/threshold_sweep_real.json               (barrido retriever real)
  - metrics/metrics.json                            (lote e2e oficial)

Salida: 05_eval/results/e2e_2026-09-12_01/figures/*.svg
"""

from __future__ import annotations

import json
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
ROOT = RUN_DIR.parents[2]
FIG_DIR = RUN_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

NAIVE_SWEEP = json.loads((ROOT / "resultados_sensibilidad_umbral_completo.json").read_bytes())["sweep"]
REAL_SWEEP = json.loads((RUN_DIR / "config" / "threshold_sweep_real.json").read_bytes())["sweep"]
METRICS = json.loads((RUN_DIR / "metrics" / "metrics.json").read_bytes())

PALETTE = {
    "bg": "#ffffff", "grid": "#e2e8f0", "text": "#1e293b", "muted": "#64748b",
    "naive": "#94a3b8", "real": "#2563eb", "accent": "#dc2626", "ok": "#16a34a",
    "warn": "#d97706", "valido": "#2563eb", "incompleto": "#d97706", "rechazado": "#dc2626",
}

SVG_HEAD = '''<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Arial, sans-serif">
<rect width="{w}" height="{h}" fill="{bg}"/>
'''


def _text(x, y, s, size=13, fill=None, anchor="start", weight="normal"):
    fill = fill or PALETTE["text"]
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>\n')


# ---------------------------------------------------------------- figura 1
def fig_threshold_sweep():
    w, h = 900, 480
    pad_l, pad_r, pad_t, pad_b = 70, 30, 50, 60
    plot_w, plot_h = w - pad_l - pad_r, h - pad_t - pad_b

    def to_xy(t, acc, tmin, tmax):
        x = pad_l + (t - tmin) / (tmax - tmin) * plot_w
        y = pad_t + (1 - acc) * plot_h
        return x, y

    svg = [SVG_HEAD.format(w=w, h=h, bg=PALETTE["bg"])]
    svg.append(_text(w / 2, 26, "Sensibilidad de min_score: naive_retriever vs. retriever real", 16, weight="bold", anchor="middle"))

    # grid + ejes
    for i in range(6):
        gy = pad_t + plot_h * i / 5
        val = 1 - i / 5
        svg.append(f'<line x1="{pad_l}" y1="{gy}" x2="{pad_l+plot_w}" y2="{gy}" stroke="{PALETTE["grid"]}" stroke-width="1"/>')
        svg.append(_text(pad_l - 10, gy + 4, f"{val:.1f}", 11, PALETTE["muted"], "end"))
    svg.append(_text(20, h / 2, "status_accuracy_global", 12, PALETTE["muted"], "middle") .replace('text-anchor="middle"', f'text-anchor="middle" transform="rotate(-90 20 {h/2})"'))

    tmin, tmax = 0.0, 0.95
    for tv in [0.0, 0.2, 0.4, 0.6, 0.72, 0.95]:
        gx = pad_l + (tv - tmin) / (tmax - tmin) * plot_w
        svg.append(f'<line x1="{gx}" y1="{pad_t}" x2="{gx}" y2="{pad_t+plot_h}" stroke="{PALETTE["grid"]}" stroke-width="1" stroke-dasharray="3,3"/>')
        svg.append(_text(gx, pad_t + plot_h + 20, f"{tv:g}", 11, PALETTE["muted"], "middle"))
    svg.append(_text(pad_l + plot_w / 2, h - 12, "min_score (umbral RuleBasedJudge)", 12, PALETTE["muted"], "middle"))

    def polyline(points, color, width=2.5):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        return f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"/>'

    naive_pts = [to_xy(r["min_score"], r["status_accuracy_global"], tmin, tmax) for r in NAIVE_SWEEP]
    real_pts = [to_xy(r["min_score"], r["status_accuracy_global"], tmin, tmax) for r in REAL_SWEEP]
    svg.append(polyline(naive_pts, PALETTE["naive"]))
    svg.append(polyline(real_pts, PALETTE["real"]))
    for x, y in naive_pts:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{PALETTE["naive"]}"/>')
    for x, y in real_pts:
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{PALETTE["real"]}"/>')

    # marcadores de umbral elegido
    x_naive_chosen, y_naive_chosen = to_xy(0.20, 0.85, tmin, tmax)
    x_real_chosen, y_real_chosen = to_xy(0.72, 0.65, tmin, tmax)
    svg.append(f'<circle cx="{x_naive_chosen:.1f}" cy="{y_naive_chosen:.1f}" r="6" fill="none" stroke="{PALETTE["naive"]}" stroke-width="2"/>')
    svg.append(f'<circle cx="{x_real_chosen:.1f}" cy="{y_real_chosen:.1f}" r="6" fill="none" stroke="{PALETTE["real"]}" stroke-width="2"/>')
    svg.append(_text(x_real_chosen + 12, y_real_chosen + 4, "0.72 -> acc=0.65 (elegido, real)", 11, PALETTE["real"]))
    svg.append(_text(x_naive_chosen, y_naive_chosen - 16, "0.20 -> acc=0.85", 11, PALETTE["muted"], "middle"))
    svg.append(_text(x_naive_chosen, y_naive_chosen - 2, "(naive, NO usable)", 10, PALETTE["muted"], "middle"))

    # leyenda (esquina inferior derecha, lejos de las curvas y anotaciones)
    lx, ly = pad_l + plot_w - 210, pad_t + plot_h - 46
    svg.append(f'<rect x="{lx-14}" y="{ly-16}" width="210" height="52" fill="white" stroke="{PALETTE["grid"]}"/>')
    svg.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+24}" y2="{ly}" stroke="{PALETTE["naive"]}" stroke-width="3"/>')
    svg.append(_text(lx + 30, ly + 4, "naive_retriever (lexico)", 11))
    svg.append(f'<line x1="{lx}" y1="{ly+22}" x2="{lx+24}" y2="{ly+22}" stroke="{PALETTE["real"]}" stroke-width="3"/>')
    svg.append(_text(lx + 30, ly + 26, "retriever real (e5-small)", 11))

    svg.append("</svg>")
    (FIG_DIR / "fig1_sensibilidad_umbral_naive_vs_real.svg").write_text("".join(svg), encoding="utf-8")


# ---------------------------------------------------------------- figura 2
def fig_confusion_matrix():
    classes = METRICS["confusion_matrix"]["classes"]
    m = METRICS["confusion_matrix"]["matrix"]
    n = len(classes)
    w, h = 560, 520
    pad_l, pad_t, cell = 150, 110, 110

    svg = [SVG_HEAD.format(w=w, h=h, bg=PALETTE["bg"])]
    svg.append(_text(w / 2, 30, "Matriz de confusion (gold x pred) -- lote e2e, n=20", 15, weight="bold", anchor="middle"))
    svg.append(_text(w / 2, 50, "min_score=0.72, top_k=3, retriever real", 11, PALETTE["muted"], "middle"))

    maxv = max(m[g][p] for g in classes for p in classes) or 1
    for i, g in enumerate(classes):
        svg.append(_text(pad_l - 15, pad_t + i * cell + cell / 2 + 5, g, 12, anchor="end", weight="bold"))
        for j, p in enumerate(classes):
            v = m[g][p]
            x, y = pad_l + j * cell, pad_t + i * cell
            intensity = v / maxv
            color = f"rgba(37,99,235,{0.12 + 0.75*intensity:.2f})" if v > 0 else "#f8fafc"
            svg.append(f'<rect x="{x}" y="{y}" width="{cell-4}" height="{cell-4}" fill="{color}" stroke="{PALETTE["grid"]}"/>')
            txt_color = PALETTE["text"] if intensity < 0.55 else "#ffffff"
            svg.append(_text(x + (cell-4)/2, y + (cell-4)/2 + 6, str(v), 22, txt_color, "middle", "bold"))
    for j, p in enumerate(classes):
        svg.append(_text(pad_l + j * cell + (cell-4)/2, pad_t - 15, p, 12, anchor="middle", weight="bold"))

    svg.append(_text(pad_l + n * cell / 2, pad_t - 60, "PREDICHO", 11, PALETTE["muted"], "middle"))
    svg.append(_text(30, pad_t + n * cell / 2, "GOLD", 11, PALETTE["muted"], "middle").replace(f'y="{pad_t + n * cell / 2}"', f'y="{pad_t + n * cell / 2}" transform="rotate(-90 30 {pad_t + n * cell / 2})"'))

    svg.append("</svg>")
    (FIG_DIR / "fig2_matriz_confusion_e2e.svg").write_text("".join(svg), encoding="utf-8")


# ---------------------------------------------------------------- figura 3
def fig_per_class_bars():
    classes = METRICS["confusion_matrix"]["classes"]
    metrics_names = [("precision_per_class", "Precision"), ("recall_per_class", "Recall"), ("f1_per_class", "F1")]
    colors = {"VALIDO": PALETTE["valido"], "INCOMPLETO": PALETTE["incompleto"], "RECHAZADO": PALETTE["rechazado"]}

    w, h = 780, 420
    pad_l, pad_r, pad_t, pad_b = 60, 30, 60, 90
    plot_w, plot_h = w - pad_l - pad_r, h - pad_t - pad_b
    group_w = plot_w / len(metrics_names)
    bar_w = group_w / (len(classes) + 1)

    svg = [SVG_HEAD.format(w=w, h=h, bg=PALETTE["bg"])]
    svg.append(_text(w / 2, 28, "Precision / Recall / F1 por clase -- lote e2e (n=20)", 15, weight="bold", anchor="middle"))

    for i in range(6):
        gy = pad_t + plot_h * i / 5
        val = 1 - i / 5
        svg.append(f'<line x1="{pad_l}" y1="{gy}" x2="{pad_l+plot_w}" y2="{gy}" stroke="{PALETTE["grid"]}"/>')
        svg.append(_text(pad_l - 10, gy + 4, f"{val:.1f}", 11, PALETTE["muted"], "end"))

    for gi, (key, label) in enumerate(metrics_names):
        gx0 = pad_l + gi * group_w
        svg.append(_text(gx0 + group_w / 2, pad_t + plot_h + 25, label, 13, weight="bold", anchor="middle"))
        for ci, cls in enumerate(classes):
            val = METRICS[key][cls]
            bx = gx0 + (ci + 0.5) * bar_w
            bh = val * plot_h
            by = pad_t + plot_h - bh
            svg.append(f'<rect x="{bx - bar_w*0.4:.1f}" y="{by:.1f}" width="{bar_w*0.8:.1f}" height="{bh:.1f}" fill="{colors[cls]}"/>')
            svg.append(_text(bx, by - 6, f"{val:.2f}", 10, PALETTE["text"], "middle"))
        svg.append(f'<line x1="{gx0+group_w}" y1="{pad_t}" x2="{gx0+group_w}" y2="{pad_t+plot_h}" stroke="{PALETTE["grid"]}" stroke-dasharray="2,2"/>')

    lx, ly = pad_l, h - 30
    for i, cls in enumerate(classes):
        svg.append(f'<rect x="{lx + i*160}" y="{ly-10}" width="14" height="14" fill="{colors[cls]}"/>')
        svg.append(_text(lx + i*160 + 20, ly + 2, cls, 12))

    svg.append("</svg>")
    (FIG_DIR / "fig3_precision_recall_f1_por_clase.svg").write_text("".join(svg), encoding="utf-8")


# ---------------------------------------------------------------- figura 4
def fig_latency_breakdown():
    lat = METRICS["latency_ms_mean"]
    stages = [("indexing", "Indexado\n(chunking+embed+Chroma)"), ("retrieval", "Retrieval"), ("agent", "Agente\n(juicio)")]
    vals = [lat[k] for k, _ in stages]
    total = lat["end_to_end"]

    w, h = 760, 380
    pad_l, pad_r, pad_t, pad_b = 260, 60, 50, 40
    plot_w = w - pad_l - pad_r

    svg = [SVG_HEAD.format(w=w, h=h, bg=PALETTE["bg"])]
    svg.append(_text(w / 2, 28, "Latencia media por etapa -- lote e2e (n=20, ms)", 15, weight="bold", anchor="middle"))
    svg.append(_text(w / 2, 46, f"end_to_end medio = {total:.0f} ms/caso (parser/normalizer: N/A, sintetico ya canonico)", 11, PALETTE["muted"], "middle"))

    maxv = max(vals) * 1.15
    bar_h = 40
    gap = 26
    y0 = pad_t + 30
    for i, ((key, label), v) in enumerate(zip(stages, vals)):
        y = y0 + i * (bar_h + gap)
        bw = v / maxv * plot_w
        svg.append(_text(pad_l - 12, y + bar_h / 2 + 5, label.replace("\n", " "), 12, anchor="end"))
        svg.append(f'<rect x="{pad_l}" y="{y}" width="{bw:.1f}" height="{bar_h}" fill="{PALETTE["real"]}" opacity="{0.5 + 0.15*i}"/>')
        svg.append(_text(pad_l + bw + 10, y + bar_h / 2 + 5, f"{v:.1f} ms", 12, weight="bold"))

    svg.append("</svg>")
    (FIG_DIR / "fig4_latencia_por_etapa.svg").write_text("".join(svg), encoding="utf-8")


if __name__ == "__main__":
    fig_threshold_sweep()
    fig_confusion_matrix()
    fig_per_class_bars()
    fig_latency_breakdown()
    print("Figuras generadas en", FIG_DIR)
