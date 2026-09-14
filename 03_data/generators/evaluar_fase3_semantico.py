"""Evaluador Fase 3 -- pipeline semantico real (ChromaDB + embeddings).

Variante de `evaluar_fase3_real.py` que sustituye `naive_retriever` por el
RAG semantico real de `rag/index_store.py` (LlamaIndex + ChromaDB +
`intfloat/multilingual-e5-small`). Se separa en un script propio en vez de
modificar `evaluar_fase3_real.py` porque ese fichero documenta, en su propio
docstring, una limitacion (falta de chromadb/llama-index) que ya no es
cierta en este entorno -- se deja intacto como registro historico de esa
limitacion, y este script sustituye su rol de ahora en adelante.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "04_src"))

from agent.bastanteo import run_bastanteo
from agent.catalog import BADA_REQUIREMENTS
from agent.judge import RuleBasedJudge
from rag.chunking import build_chunks
from rag.index_store import build_index, build_nodes, query as rag_query


def build_case_index(case: dict, persist_dir: Path, embed_model):
    chunks = []
    for document in case.get("document_inventory", []):
        chunks.extend(build_chunks(document, case_id=case.get("case_id")))
    nodes = build_nodes(chunks)
    collection_name = f"case_{case['case_id'].replace('-', '_').lower()}"
    return build_index(
        nodes,
        persist_dir=persist_dir,
        collection_name=collection_name,
        embed_model=embed_model,
    )


def load_manifest(dataset_dir: Path) -> list[dict]:
    with open(dataset_dir / "manifest.json", encoding="utf-8") as f:
        return json.load(f)


def select_subset(manifest: list[dict], n_per_status: int) -> list[dict]:
    by_status: dict[str, list[dict]] = {}
    for case in manifest:
        by_status.setdefault(case["status_gold"], []).append(case)
    subset = []
    for status in ["VALIDO", "INCOMPLETO", "RECHAZADO"]:
        subset.extend(by_status.get(status, [])[:n_per_status])
    return subset


def evaluate_case(dataset_dir: Path, case_meta: dict, persist_dir: Path, embed_model, min_score: float) -> dict:
    with open(dataset_dir / case_meta["file"], encoding="utf-8") as f:
        case = json.load(f)

    t_index0 = time.perf_counter()
    index = build_case_index(case, persist_dir, embed_model)
    index_ms = (time.perf_counter() - t_index0) * 1000

    def retrieve_fn(q: str, k: int):
        return rag_query(index, q, top_k=k)

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
        "case_id": case_meta["case_id"],
        "status_real": real_status,
        "status_predicted": predicted_status,
        "status_match": predicted_status == real_status,
        "n_requisitos_documento": per_req_total,
        "n_requisitos_correctos": per_req_correct,
        "requisito_accuracy": per_req_correct / per_req_total if per_req_total else 0.0,
        "latency_ms": round(elapsed_ms, 3),
        "index_ms": round(index_ms, 3),
        "n_docs_expediente": len(case["document_inventory"]),
    }


def run_evaluation(
    dataset_dir: Path,
    n_per_status: int,
    min_score: float,
    out_path: Path,
    embed_model,
) -> dict:
    manifest = load_manifest(dataset_dir)
    subset = select_subset(manifest, n_per_status)

    print(f"Dataset: {len(manifest)} casos totales, evaluando subset de {len(subset)}")
    for c in subset:
        print(f"   - {c['case_id']}: {c['status_gold']}")

    # No usamos tempfile.TemporaryDirectory como context manager: en Windows,
    # ChromaDB (via sqlite3) mantiene el fichero de la coleccion abierto un
    # instante mas alla del `with`, y el borrado automatico lanza
    # PermissionError. Se crea manualmente y se borra con `ignore_errors`.
    tmp = tempfile.mkdtemp(prefix="fase3_chroma_")
    try:
        persist_dir = Path(tmp)
        print(f"\nEjecutando pipeline SEMANTICO real (ChromaDB + embeddings, min_score={min_score})...")
        results = []
        for i, case_meta in enumerate(subset, 1):
            r = evaluate_case(dataset_dir, case_meta, persist_dir, embed_model, min_score)
            results.append(r)
            match_symbol = "OK" if r["status_match"] else "X"
            print(
                f"   [{i}/{len(subset)}] {r['case_id']}: "
                f"real={r['status_real']:<10} predicho={r['status_predicted']:<10} {match_symbol}  "
                f"req_acc={r['requisito_accuracy']:.0%}  lat={r['latency_ms']:.1f}ms  idx={r['index_ms']:.1f}ms"
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    n = len(results)
    status_accuracy = sum(r["status_match"] for r in results) / n
    req_accuracy_mean = sum(r["requisito_accuracy"] for r in results) / n
    latency_mean = sum(r["latency_ms"] for r in results) / n
    latency_p95 = sorted(r["latency_ms"] for r in results)[int(n * 0.95) if int(n * 0.95) < n else n - 1]

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
            "pipeline": (
                "rag.index_store (ChromaDB + intfloat/multilingual-e5-small) "
                f"+ RuleBasedJudge (min_score={min_score})"
            ),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "limitaciones": [
                "RuleBasedJudge nunca devuelve 'contradicted' -> los casos RECHAZADO "
                "no pueden clasificarse correctamente por diseno (limitacion "
                "arquitectonica del judge, no del retriever semantico).",
                "Cada caso se indexa en una coleccion ChromaDB aislada y efimera "
                "(directorio temporal); no representa un indice compartido a escala.",
                "min_score calibrado empiricamente sobre un subset reducido antes de "
                "aplicarlo a este run; no validado en un dataset independiente.",
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

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nResultados guardados en {out_path}")
    print("\n" + "=" * 70)
    print("RESUMEN -- EVALUACION SEMANTICA (ChromaDB + embeddings reales)")
    print("=" * 70)
    print(f"Accuracy clasificacion expediente (global): {status_accuracy:.1%}")
    print(f"Accuracy por requisito documental (media):  {req_accuracy_mean:.1%}")
    print(f"Latencia media (agente, sin indexado):       {latency_mean:.2f} ms")
    print(f"Latencia p95:                                {latency_p95:.2f} ms")
    print("\nDesglose por escenario:")
    for status, data in scenario_breakdown.items():
        print(f"   {status:<12}: {data['accuracy']:.0%} accuracy ({data['n_casos']} casos)")
    print("=" * 70)

    return output


def main():
    parser = argparse.ArgumentParser(description="Evaluacion Fase 3 -- RAG semantico real")
    parser.add_argument("--dataset", type=str, default="03_data/synthetic_v1")
    parser.add_argument("--n-per-status", type=int, default=3)
    parser.add_argument("--min-score", type=float, default=0.75)
    parser.add_argument("--out", type=str, default="resultados_evaluacion_semantica.json")
    args = parser.parse_args()

    print("Cargando modelo de embeddings (intfloat/multilingual-e5-small)...")
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    embed_model = HuggingFaceEmbedding(model_name="intfloat/multilingual-e5-small")
    print("Modelo cargado.")

    run_evaluation(
        dataset_dir=Path(args.dataset),
        n_per_status=args.n_per_status,
        min_score=args.min_score,
        out_path=Path(args.out),
        embed_model=embed_model,
    )


if __name__ == "__main__":
    main()
