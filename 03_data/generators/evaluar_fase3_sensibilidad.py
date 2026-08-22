"""Evaluador Fase 3 — Análisis de sensibilidad al umbral (min_score) del
RuleBasedJudge, sobre el pipeline REAL (naive_retriever + run_bastanteo),
sin mocks.

Motivación: una primera pasada con min_score=0.0 mostró que el retriever
léxico (solapamiento de palabras, sin stopwords) confunde "hay solapamiento
con algo" con "el documento está presente", produciendo falsos positivos en
casos INCOMPLETO. Subir el umbral corrige eso pero introduce falsos
negativos en casos VALIDO (el vocabulario real del documento no coincide
literalmente con el de la query). Este script barre varios umbrales para
caracterizar ese trade-off de forma honesta, en vez de reportar un único
punto arbitrario.

Limitaciones declaradas explícitamente (no ocultas):
  1. naive_retriever sustituye al retriever semántico real (rag/) porque
     chromadb/llama-index no están instalados en este entorno.
  2. RuleBasedJudge nunca devuelve "contradicted" -> RECHAZADO no puede
     clasificarse correctamente con ningún umbral (limitación de diseño,
     no de tuning).
  3. VRAM no aplica: este pipeline es 100% heurística CPU sin modelos.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "04_src"))

from agent.bastanteo import run_bastanteo
from agent.catalog import BADA_REQUIREMENTS
from agent.judge import RuleBasedJudge
from ui.naive_retriever import build_naive_retriever


def load_manifest(dataset_dir: Path) -> list[dict]:
    with open(dataset_dir / "manifest.json") as f:
        return json.load(f)


def select_subset(manifest: list[dict], n_per_status: int) -> list[dict]:
    by_status: dict[str, list[dict]] = {}
    for case in manifest:
        by_status.setdefault(case["status_gold"], []).append(case)
    subset = []
    for status in ["VALIDO", "INCOMPLETO", "RECHAZADO"]:
        subset.extend(by_status.get(status, [])[:n_per_status])
    return subset


def evaluate_case(case: dict, min_score: float) -> dict:
    retrieve_fn = build_naive_retriever(case)
    judge = RuleBasedJudge(min_score=min_score)

    t0 = time.perf_counter()
    result = run_bastanteo(BADA_REQUIREMENTS, retrieve_fn, judge=judge, top_k=3)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    predicted_status = result["bastanteo_gold"]["status"]
    real_status = case["bastanteo_gold"]["status"]

    evidence = result["bastanteo_evidence"]
    doc_types_present = {d["document_type_gold"] for d in case["document_inventory"]}

    per_req_correct = 0
    per_req_total = 0
    for req, ev in zip(BADA_REQUIREMENTS, evidence):
        if req.evidence_type != "document":
            continue
        per_req_total += 1
        doc_expected_present = req.requirement_id in doc_types_present
        agent_found = ev["status"] == "supported"
        if doc_expected_present == agent_found:
            per_req_correct += 1

    return {
        "status_real": real_status,
        "status_predicted": predicted_status,
        "status_match": predicted_status == real_status,
        "requisito_accuracy": per_req_correct / per_req_total if per_req_total else 0.0,
        "latency_ms": elapsed_ms,
    }


def run_sweep(dataset_dir: Path, subset: list[dict], thresholds: list[float]) -> dict:
    cases = []
    for case_meta in subset:
        with open(dataset_dir / case_meta["file"]) as f:
            cases.append((case_meta["case_id"], json.load(f)))

    sweep_results = []
    for min_score in thresholds:
        results = [evaluate_case(case, min_score) for _, case in cases]
        n = len(results)

        by_scenario: dict[str, list[dict]] = {}
        for r in results:
            by_scenario.setdefault(r["status_real"], []).append(r)

        scenario_accuracy = {
            status: sum(r["status_match"] for r in rs) / len(rs)
            for status, rs in by_scenario.items()
        }

        sweep_results.append({
            "min_score": min_score,
            "status_accuracy_global": sum(r["status_match"] for r in results) / n,
            "requisito_accuracy_mean": sum(r["requisito_accuracy"] for r in results) / n,
            "latency_mean_ms": sum(r["latency_ms"] for r in results) / n,
            "scenario_accuracy": scenario_accuracy,
        })

    return {
        "n_cases": len(cases),
        "case_ids": [cid for cid, _ in cases],
        "sweep": sweep_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Barrido de sensibilidad al umbral min_score")
    parser.add_argument("--dataset", type=str, default="03_data/synthetic_v1")
    parser.add_argument("--n-per-status", type=int, default=3)
    parser.add_argument(
        "--thresholds", type=str, default="0.0,0.05,0.10,0.15,0.20,0.25,0.30,0.35,0.40"
    )
    parser.add_argument("--out", type=str, default="resultados_sensibilidad_umbral.json")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    manifest = load_manifest(dataset_dir)
    subset = select_subset(manifest, args.n_per_status)
    thresholds = [float(t) for t in args.thresholds.split(",")]

    print(f"📂 Dataset: {len(manifest)} casos totales, subset evaluado: {len(subset)}")
    print(f"🔬 Barriendo {len(thresholds)} umbrales: {thresholds}\n")

    output = run_sweep(dataset_dir, subset, thresholds)

    print(f"{'umbral':>8} {'acc.global':>11} {'acc.VALIDO':>11} {'acc.INCOMP':>11} {'acc.RECHAZ':>11} {'acc.requisito':>14} {'lat.media(ms)':>14}")
    for row in output["sweep"]:
        sa = row["scenario_accuracy"]
        print(
            f"{row['min_score']:>8.2f} "
            f"{row['status_accuracy_global']:>10.1%} "
            f"{sa.get('VALIDO', float('nan')):>10.1%} "
            f"{sa.get('INCOMPLETO', float('nan')):>10.1%} "
            f"{sa.get('RECHAZADO', float('nan')):>10.1%} "
            f"{row['requisito_accuracy_mean']:>13.1%} "
            f"{row['latency_mean_ms']:>13.3f}"
        )

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Guardado en {args.out}")

    # Mejor umbral por accuracy de requisito (métrica más informativa, ya
    # que status_accuracy global está limitada por el 0% estructural de
    # RECHAZADO en cualquier umbral)
    best = max(output["sweep"], key=lambda r: r["requisito_accuracy_mean"])
    print(f"\n🏆 Mejor umbral por accuracy de requisito: {best['min_score']} "
          f"({best['requisito_accuracy_mean']:.1%})")


if __name__ == "__main__":
    main()
