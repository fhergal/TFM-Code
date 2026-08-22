"""Figura 2 (v2, real) — Análisis de sensibilidad al umbral min_score del
RuleBasedJudge, sobre el pipeline real (naive_retriever + run_bastanteo),
evaluado sobre los 20 expedientes del dataset sintético v1 completo.

Sustituye a la estructura original de 4 paneles (F1/ANLS/Latencia/VRAM
"guIA vs. baseline"), que no encajaba con lo que hay implementado hoy: no
existe todavía un "guIA final" que comparar contra un baseline -- lo que
existe es un baseline heurístico (RuleBasedJudge + naive_retriever) cuyo
comportamiento se caracteriza aquí honestamente antes de pasar a
retrieval semántico real.

Datos: resultados_sensibilidad_umbral_completo.json (20/20 casos,
generado por evaluar_fase3_sensibilidad.py, sin mocks).
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

RESULTS_FILE = Path(__file__).parent.parent / "resultados_sensibilidad_umbral_completo.json"
OUT_FILE = Path(__file__).parent / "figura2_sensibilidad_umbral.png"


def main():
    with open(RESULTS_FILE) as f:
        data = json.load(f)

    sweep = data["sweep"]
    n_cases = data["n_cases"]

    thresholds = [r["min_score"] for r in sweep]
    acc_global = [r["status_accuracy_global"] * 100 for r in sweep]
    acc_valido = [r["scenario_accuracy"].get("VALIDO", 0) * 100 for r in sweep]
    acc_incompleto = [r["scenario_accuracy"].get("INCOMPLETO", 0) * 100 for r in sweep]
    acc_rechazado = [r["scenario_accuracy"].get("RECHAZADO", 0) * 100 for r in sweep]
    acc_requisito = [r["requisito_accuracy_mean"] * 100 for r in sweep]
    latencia = [r["latency_mean_ms"] for r in sweep]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    fig.suptitle(
        f"Sensibilidad del baseline heurístico (RuleBasedJudge + naive_retriever) "
        f"al umbral min_score\nDataset sintético BADA v1 — {n_cases}/{n_cases} expedientes evaluados",
        fontsize=12, fontweight="bold",
    )

    # Panel 1: accuracy por escenario + global vs umbral
    ax1 = axes[0]
    ax1.plot(thresholds, acc_global, "o-", label="Accuracy global", color="black", linewidth=2.5)
    ax1.plot(thresholds, acc_valido, "s--", label="VALIDO", color="#2ca02c")
    ax1.plot(thresholds, acc_incompleto, "^--", label="INCOMPLETO", color="#ff7f0e")
    ax1.plot(thresholds, acc_rechazado, "x--", label="RECHAZADO", color="#d62728")
    ax1.axvspan(0.15, 0.25, alpha=0.12, color="green", label="Zona óptima")
    ax1.set_xlabel("Umbral min_score (RuleBasedJudge)")
    ax1.set_ylabel("Accuracy de clasificación (%)")
    ax1.set_title("Accuracy por escenario vs. umbral")
    ax1.set_ylim(-5, 105)
    ax1.legend(loc="center right", fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Panel 2: accuracy por requisito + latencia (eje secundario)
    ax2 = axes[1]
    ax2.plot(thresholds, acc_requisito, "D-", color="#1f77b4", label="Accuracy por requisito documental")
    ax2.axvspan(0.15, 0.25, alpha=0.12, color="green")
    ax2.set_xlabel("Umbral min_score (RuleBasedJudge)")
    ax2.set_ylabel("Accuracy por requisito (%)", color="#1f77b4")
    ax2.tick_params(axis="y", labelcolor="#1f77b4")
    ax2.set_ylim(60, 105)
    ax2.set_title("Accuracy por requisito + latencia")
    ax2.grid(True, alpha=0.3)

    ax2b = ax2.twinx()
    ax2b.plot(thresholds, latencia, "v:", color="gray", label="Latencia media (ms)", alpha=0.7)
    ax2b.set_ylabel("Latencia media (ms)", color="gray")
    ax2b.tick_params(axis="y", labelcolor="gray")

    lines1, labels1 = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines1 + lines2, labels1 + labels2, loc="lower right", fontsize=9)

    fig.text(
        0.5, -0.02,
        "Nota: RECHAZADO (0% en todo el rango) es una limitación arquitectónica de RuleBasedJudge "
        "(nunca devuelve 'contradicted'), no un fallo de tuning. "
        "VRAM no se reporta: pipeline 100% heurístico CPU, sin modelos de embeddings ni LLM.",
        ha="center", fontsize=8.5, style="italic", color="#444444", wrap=True,
    )

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.savefig(OUT_FILE, dpi=150, bbox_inches="tight")
    print(f"✅ Figura guardada en {OUT_FILE}")


if __name__ == "__main__":
    main()
