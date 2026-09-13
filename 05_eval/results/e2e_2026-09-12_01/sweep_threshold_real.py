"""Barrido de sensibilidad de `min_score` (RuleBasedJudge) sobre el
RETRIEVER REAL (ChromaDB + intfloat/multilingual-e5-small), para fijar el
umbral operativo del lote e2e oficial.

Por que hace falta (no se puede reutilizar el barrido anterior): el barrido
en `resultados_sensibilidad_umbral_completo.json` se hizo con `naive_retriever`
(solapamiento lexico, scores ~0.0-0.5). El retriever semantico real produce
similitud coseno normalizada en un rango mucho mas estrecho y alto (~0.70-0.83,
ver sonda manual). El umbral 0.20 heredado de ese barrido queda por debajo de
CUALQUIER score real -> el juez marca todo como "supported" -> todo VALIDO
(confirmado en la validacion de 3 casos del e2e: accuracy=0.33, recall
INCOMPLETO=RECHAZADO=0).

Optimizacion: la recuperacion (embedding + ChromaDB) NO depende del umbral,
solo el juicio posterior. Por caso: se construye el indice UNA vez, se
recuperan las citas de los 8 requisitos UNA vez (top_k fijo), y se cachean.
El barrido de umbrales reutiliza esas citas cacheadas (RuleBasedJudge.judge
y _compute_gold son deterministas y sin red) -- evita repetir 20 casos x
N_umbrales embeddings.

Salida: 05_eval/results/e2e_2026-09-12_01/config/threshold_sweep_real.json
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
ROOT = RUN_DIR.parents[2]
SRC = ROOT / "04_src"
DATASET = ROOT / "03_data" / "synthetic_v1"
sys.path.insert(0, str(SRC))

from rag import build_chunks, build_index, build_nodes, query          # noqa: E402
from agent.bastanteo import _build_evidence, _compute_gold             # noqa: E402
from agent.catalog import BADA_REQUIREMENTS                             # noqa: E402
from agent.judge import RuleBasedJudge                                  # noqa: E402

TOP_K = 3
# Rango informado por sonda manual (scores reales observados ~0.69-0.83);
# se barre algo mas ancho para no asumir el limite de antemano.
THRESHOLDS = [round(0.55 + 0.01 * i, 2) for i in range(41)]  # 0.55 .. 0.95


def collect_citations_per_case() -> list[dict]:
    """Construye el indice REAL una vez por caso y cachea las citas de los
    8 requisitos (top_k=3). No depende del umbral."""
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    out = []
    for i, entry in enumerate(manifest, start=1):
        cid = entry["case_id"]
        case = json.loads((DATASET / f"{cid}.json").read_bytes())
        chunks = []
        for doc in case["document_inventory"]:
            chunks.extend(build_chunks(doc, case_id=cid))
        nodes = build_nodes(chunks)
        case_chroma = RUN_DIR / ".chroma_sweep" / cid
        shutil.rmtree(case_chroma, ignore_errors=True)
        index = build_index(nodes, persist_dir=str(case_chroma), collection_name=f"sweep-{cid}")

        per_req = []
        for req in BADA_REQUIREMENTS:
            cites = query(index, req.query, top_k=TOP_K)
            per_req.append({"requirement": req, "citations": cites})

        out.append({
            "case_id": cid,
            "status_gold": entry["status_gold"],
            "per_req": per_req,
        })
        print(f"  [{i}/{len(manifest)}] {cid} indexado y recuperado ({len(chunks)} chunks)")
    return out


def evaluate_at_threshold(cached: list[dict], min_score: float) -> dict:
    judge = RuleBasedJudge(min_score=min_score)
    n = len(cached)
    correct = 0
    by_class_total = {"VALIDO": 0, "INCOMPLETO": 0, "RECHAZADO": 0}
    by_class_correct = {"VALIDO": 0, "INCOMPLETO": 0, "RECHAZADO": 0}
    latencies = []

    for c in cached:
        t0 = time.perf_counter()
        evidence_list = []
        for j, pr in enumerate(c["per_req"], start=1):
            req = pr["requirement"]
            status, text, best = judge.judge(req.claim, pr["citations"])
            evidence_list.append(_build_evidence(req, j, status, text, best))
        gold_pred = _compute_gold(evidence_list, BADA_REQUIREMENTS)
        latencies.append((time.perf_counter() - t0) * 1000)

        g = c["status_gold"]
        by_class_total[g] += 1
        if gold_pred["status"] == g:
            correct += 1
            by_class_correct[g] += 1

    scenario_accuracy = {
        k: (by_class_correct[k] / by_class_total[k] if by_class_total[k] else None)
        for k in by_class_total
    }
    return {
        "min_score": min_score,
        "status_accuracy_global": round(correct / n, 4),
        "scenario_accuracy": scenario_accuracy,
        "latency_mean_ms": round(sum(latencies) / len(latencies), 4),
    }


def main() -> int:
    print("== Recuperando citas reales (indice ChromaDB + e5-small) por caso, una sola vez ==")
    t0 = time.time()
    cached = collect_citations_per_case()
    print(f"   listo en {time.time() - t0:.1f}s\n")

    print(f"== Barriendo {len(THRESHOLDS)} umbrales sobre {len(cached)} casos (sin red, cacheado) ==")
    sweep = [evaluate_at_threshold(cached, t) for t in THRESHOLDS]

    best = max(sweep, key=lambda r: r["status_accuracy_global"])
    best_acc = best["status_accuracy_global"]
    plateau = [r for r in sweep if r["status_accuracy_global"] == best_acc]
    lo, hi = plateau[0]["min_score"], plateau[-1]["min_score"]
    center = round((lo + hi) / 2, 2)
    # min_score central mas cercano a un valor de la rejilla realmente barrida
    chosen = min(THRESHOLDS, key=lambda t: abs(t - center))

    result = {
        "retriever": "real (ChromaDB + intfloat/multilingual-e5-small)",
        "n_cases": len(cached),
        "top_k": TOP_K,
        "sweep": sweep,
        "best_accuracy": best_acc,
        "plateau_range": [lo, hi],
        "chosen_min_score": chosen,
        "chosen_min_score_rationale": (
            f"Centro de la meseta de accuracy maxima [{lo}, {hi}] "
            f"(status_accuracy_global={best_acc}), analogo al criterio usado en el "
            f"barrido con naive_retriever pero recalculado sobre el retriever real."
        ),
        "known_limitation": (
            "RuleBasedJudge nunca devuelve 'contradicted': los casos RECHAZADO "
            "(datos presentes pero contradictorios, p.ej. DNI no coincide) son "
            "estructuralmente inclasificables con este juez, para cualquier umbral. "
            "Ademas, con el retriever semantico real los scores de citas relevantes "
            "e irrelevantes se solapan en una banda estrecha (~0.70-0.83): no existe "
            "un umbral que separe limpiamente 'requisito satisfecho' de 'requisito "
            "ausente' basandose solo en el score maximo -- limitacion arquitectonica "
            "del juicio por umbral de similitud, no un problema de tuning."
        ),
    }

    out_path = RUN_DIR / "config" / "threshold_sweep_real.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'min_score':>10} {'acc_global':>11} {'VALIDO':>8} {'INCOMPLETO':>11} {'RECHAZADO':>10}")
    for r in sweep:
        sa = r["scenario_accuracy"]
        print(f"{r['min_score']:>10} {r['status_accuracy_global']:>11} "
              f"{sa['VALIDO']:>8} {sa['INCOMPLETO']:>11} {sa['RECHAZADO']:>10}")

    print(f"\n=== mejor accuracy_global={best_acc} en meseta [{lo}, {hi}] -> elegido min_score={chosen} ===")
    print(f"Guardado en {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
