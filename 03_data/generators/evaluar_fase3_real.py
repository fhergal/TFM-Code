"""Evaluador Fase 3 — REAL, sin mocks.

Ejecuta el pipeline real (naive_retriever + RuleBasedJudge + run_bastanteo)
sobre el dataset sintético v1, comparando el bastanteo_gold predicho por el
agente contra el bastanteo_gold ya calculado de forma determinista por el
generador (generador_bada.py) a partir de qué documentos están presentes.

Limitaciones conocidas y deliberadamente NO ocultadas:

1. Usa `naive_retriever` (solapamiento de palabras, sin embeddings) en vez
   del retriever semántico real de `rag/index_store.py`, porque
   chromadb/llama-index no están instalados en este entorno (mismo
   problema de red ya documentado en la bitácora del proyecto). El
   propio docstring de naive_retriever.py exige declarar esto en la
   memoria.

2. `RuleBasedJudge` solo puede devolver "supported" o "missing", nunca
   "contradicted" (no lee el contenido de las citas, solo mide
   solapamiento léxico). Por diseño, esto significa que los casos
   RECHAZADO (DNI del solicitante no coincide con el del certificado)
   NO pueden clasificarse correctamente con este judge -- es una
   limitación arquitectónica real, no un error del experimento.
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


def evaluate_case(dataset_dir: Path, case_meta: dict) -> dict:
    with open(dataset_dir / case_meta["file"]) as f:
        case = json.load(f)

    retrieve_fn = build_naive_retriever(case)
    judge = RuleBasedJudge(min_score=0.30)

    t0 = time.perf_counter()
    result = run_bastanteo(BADA_REQUIREMENTS, retrieve_fn, judge=judge, top_k=3)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    predicted_status = result["bastanteo_gold"]["status"]
    real_status = case["bastanteo_gold"]["status"]

    # Métrica por requisito: ¿el agente encontró evidencia (supported) donde
    # el generador dice que el documento SÍ está presente en el expediente?
    evidence = result["bastanteo_evidence"]
    doc_types_present = {d["document_type_gold"] for d in case["document_inventory"]}

    per_req_correct = 0
    per_req_total = 0
    for req, ev in zip(BADA_REQUIREMENTS, evidence):
        if req.evidence_type != "document":
            continue  # el naive retriever no distingue bien evidence_type=field
        per_req_total += 1
        doc_expected_present = req.requirement_id in doc_types_present
        agent_found = ev["status"] == "supported"
        if doc_expected_present == agent_found:
            per_req_correct += 1

    return {
        "case_id": case_meta["case_id"],
        "status_real": real_status,
        "status_predicted": predicted_status,
        "status_match": predicted_status == real_status,
        "n_requisitos_documento": per_req_total,
        "n_requisitos_correctos": per_req_correct,
        "requisito_accuracy": per_req_correct / per_req_total if per_req_total else 0.0,
        "latency_ms": round(elapsed_ms, 3),
        "n_docs_expediente": len(case["document_inventory"]),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluación REAL Fase 3 (sin mocks)")
    parser.add_argument("--dataset", type=str, default="03_data/synthetic_v1")
    parser.add_argument("--n-per-status", type=int, default=3)
    parser.add_argument("--out", type=str, default="resultados_evaluacion_real.json")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset)
    manifest = load_manifest(dataset_dir)
    subset = select_subset(manifest, args.n_per_status)

    print(f"📂 Dataset: {len(manifest)} casos totales, evaluando subset de {len(subset)}")
    for c in subset:
        print(f"   - {c['case_id']}: {c['status_gold']}")

    print("\n⏳ Ejecutando pipeline REAL (naive_retriever + RuleBasedJudge)...")
    results = []
    for i, case_meta in enumerate(subset, 1):
        r = evaluate_case(dataset_dir, case_meta)
        results.append(r)
        match_symbol = "✅" if r["status_match"] else "❌"
        print(
            f"   [{i}/{len(subset)}] {r['case_id']}: "
            f"real={r['status_real']:<10} predicho={r['status_predicted']:<10} {match_symbol}  "
            f"req_acc={r['requisito_accuracy']:.0%}  lat={r['latency_ms']:.2f}ms"
        )

    n = len(results)
    status_accuracy = sum(r["status_match"] for r in results) / n
    req_accuracy_mean = sum(r["requisito_accuracy"] for r in results) / n
    latency_mean = sum(r["latency_ms"] for r in results) / n
    latency_p95 = sorted(r["latency_ms"] for r in results)[int(n * 0.95) if int(n * 0.95) < n else n - 1]

    # Desglose por escenario (para que en la Discusión se vea explícitamente
    # que RECHAZADO falla de forma sistemática, no aleatoria)
    by_scenario: dict[str, list[dict]] = {}
    for r in results:
        by_scenario.setdefault(r["status_real"], []).append(r)
    scenario_breakdown = {
        status: {
            "n_casos": len(rs),
            "accuracy": sum(r["status_match"] for r in rs) / len(rs),
        }
        for status, rs in by_scenario.items()
    }

    output = {
        "metadata": {
            "dataset": str(dataset_dir),
            "n_cases": n,
            "pipeline": "naive_retriever (Jaccard word overlap) + RuleBasedJudge (min_score=0.0)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "limitaciones": [
                "naive_retriever sustituye al retriever semántico real (rag/index_store.py) "
                "porque chromadb/llama-index no están instalados en este entorno.",
                "RuleBasedJudge nunca devuelve 'contradicted' -> los casos RECHAZADO "
                "no pueden clasificarse correctamente por diseño (limitación arquitectónica, "
                "no fallo del experimento).",
                "VRAM no aplica a este pipeline: no usa ningún modelo de embeddings ni LLM, "
                "es 100% heurística CPU. La métrica de VRAM solo tendría sentido evaluando "
                "el pipeline semántico completo (rag/ con intfloat/multilingual-e5-small).",
            ],
        },
        "individual_results": results,
        "aggregated": {
            "status_accuracy": status_accuracy,
            "requisito_accuracy_mean": req_accuracy_mean,
            "latency_mean_ms": latency_mean,
            "latency_p95_ms": latency_p95,
        },
        "scenario_breakdown": scenario_breakdown,
    }

    with open(args.out, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Resultados guardados en {args.out}")
    print("\n" + "=" * 70)
    print("RESUMEN — EVALUACIÓN REAL (sin mocks)")
    print("=" * 70)
    print(f"Accuracy clasificación expediente (global): {status_accuracy:.1%}")
    print(f"Accuracy por requisito documental (media):  {req_accuracy_mean:.1%}")
    print(f"Latencia media (real, wall-clock):           {latency_mean:.2f} ms")
    print(f"Latencia p95:                                {latency_p95:.2f} ms")
    print("\nDesglose por escenario:")
    for status, data in scenario_breakdown.items():
        print(f"   {status:<12}: {data['accuracy']:.0%} accuracy ({data['n_casos']} casos)")
    print("=" * 70)


if __name__ == "__main__":
    main()
