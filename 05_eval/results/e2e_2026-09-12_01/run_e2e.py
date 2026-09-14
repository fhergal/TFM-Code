"""Runner del lote e2e (run_id e2e_2026-09-12_01): evaluacion reproducible
end-to-end del pipeline de bastanteo sobre el dataset sintetico BADA v1.

Pipeline por caso (aislado + offline):
    case canonico -> chunking layout-aware -> indice ChromaDB (e5-small,
    coleccion UNICA por caso) -> retrieval trazable -> agente RuleBasedJudge
    -> dictamen + evidencia -> metricas del manifiesto.

Aislamiento: build_index usa por defecto una coleccion ChromaDB persistente
FIJA; reutilizarla contamina el retrieval entre expedientes (detectado en el
smoke). Aqui cada caso usa persist_dir + collection_name unicos, limpiados
antes de indexar.

Offline: exportar antes de ejecutar (el embedding esta en cache pero
sentence-transformers hace un HEAD a HuggingFace que la red del entorno
bloquea):
    HF_HUB_OFFLINE=1  TRANSFORMERS_OFFLINE=1

Uso:
    .venv/Scripts/python.exe 05_eval/results/e2e_2026-09-12_01/run_e2e.py
    .venv/Scripts/python.exe .../run_e2e.py --limit 3 --out /tmp/val   # validacion

Definiciones de metricas (declaradas para la memoria):
  - Clasificacion: status predicho (bastanteo_gold.status del agente) vs
    status_gold del caso, sobre {VALIDO, INCOMPLETO, RECHAZADO}.
  - retrieval_*_at_k: SOLO sobre requisitos cuyo requirement_id == document_type
    y con >=1 documento relevante presente en el caso (los requisitos tipo
    'field' -DNI, consentimiento- se excluyen: no son un documento). Un
    documento se considera recuperado si aparece como document_id de alguna
    de las top_k citas del requisito. precision = rel_recuperados/docs_recuperados;
    recall = rel_recuperados/rel_totales_presentes.
  - evidence_coverage: media por caso de (requisitos con evidencia vinculada /
    total requisitos).
  - grounding_validity: fraccion de citas vinculadas cuyo documento/pagina/
    bloque existe realmente en el caso.
  - Latencias: parser y normalizer = null (los sinteticos ya son canonicos, no
    hay paso Datalab ni normalizacion). indexing/retrieval/agent/e2e medidas.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

RUN_DIR = Path(__file__).resolve().parent
ROOT = RUN_DIR.parents[2]
SRC = ROOT / "04_src"
DATASET = ROOT / "03_data" / "synthetic_v1"
sys.path.insert(0, str(SRC))

from rag import build_chunks, build_index, build_nodes, query          # noqa: E402
from agent import RuleBasedJudge, run_bastanteo                         # noqa: E402
from agent.catalog import BADA_REQUIREMENTS                             # noqa: E402

CLASSES = ["VALIDO", "INCOMPLETO", "RECHAZADO"]


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _case_block_index(case: dict) -> dict:
    idx: dict = {}
    for doc in case.get("document_inventory", []):
        idx[doc["document_id"]] = {
            str(p["page_number"]): {b["block_id"] for b in p.get("blocks", []) if b.get("block_id")}
            for p in doc.get("pages", [])
        }
    return idx


def _doc_types(case: dict) -> dict:
    """document_id -> document_type_gold (presentes en el caso)."""
    return {d["document_id"]: d.get("document_type_gold") for d in case.get("document_inventory", [])}


def process_case(cid: str, out_dir: Path, min_score: float, top_k: int) -> dict:
    t_case = time.perf_counter()
    case = json.loads((DATASET / f"{cid}.json").read_bytes())
    gold_status = (case.get("bastanteo_gold") or {}).get("status")

    _dump(out_dir / "raw" / f"{cid}.json", case)
    _dump(out_dir / "normalized" / f"{cid}.json", case.get("document_inventory", []))

    # --- indexing (chunking + nodes + index ChromaDB aislado) ---
    t0 = time.perf_counter()
    chunks = []
    for doc in case.get("document_inventory", []):
        chunks.extend(build_chunks(doc, case_id=cid))
    nodes = build_nodes(chunks)
    case_chroma = out_dir / ".chroma" / cid
    shutil.rmtree(case_chroma, ignore_errors=True)
    index = build_index(nodes, persist_dir=str(case_chroma), collection_name=f"e2e-{cid}")
    lat_index = (time.perf_counter() - t0) * 1000
    _dump(out_dir / "chunks" / f"{cid}.json", chunks)

    # --- retrieval + agente (separando latencias) ---
    retrieval_log: list[dict] = []
    retr_ms = {"t": 0.0}

    def retrieve_fn(q: str, k: int) -> list[dict]:
        r0 = time.perf_counter()
        cites = query(index, q, top_k=k)
        retr_ms["t"] += (time.perf_counter() - r0) * 1000
        retrieval_log.append({"query": q, "top_k": k, "citations": cites})
        return cites

    t0 = time.perf_counter()
    result = run_bastanteo(BADA_REQUIREMENTS, retrieve_fn, judge=RuleBasedJudge(min_score=min_score), top_k=top_k)
    lat_bastanteo = (time.perf_counter() - t0) * 1000
    lat_retrieval = retr_ms["t"]
    lat_agent = max(0.0, lat_bastanteo - lat_retrieval)
    _dump(out_dir / "retrieval" / f"{cid}.json", retrieval_log)
    _dump(out_dir / "agent" / f"{cid}.json", result)

    pred_status = (result.get("bastanteo_gold") or {}).get("status")
    evid = result.get("bastanteo_evidence", [])

    # --- grounding: cada cita vinculada referencia doc/pagina/bloque existente ---
    bidx = _case_block_index(case)
    linked = grounded = 0
    grounding_problems = []
    for e in evid:
        did = e.get("linked_document_id")
        if not did:
            continue
        linked += 1
        pn = str(e["linked_page"]) if e.get("linked_page") is not None else None
        ok = did in bidx and (pn is None or pn in bidx[did])
        if ok and pn is not None:
            for bid in filter(None, (e.get("source_block_ids") or "").split(",")):
                if bid not in bidx[did][pn]:
                    ok = False
                    break
        grounded += int(ok)
        if not ok:
            grounding_problems.append(e.get("evidence_id"))

    # --- retrieval@k (solo requisitos doc-type con relevante presente) ---
    dt = _doc_types(case)
    req_by_query = {r.query: r for r in BADA_REQUIREMENTS}
    retr_points = []
    for entry in retrieval_log:
        req = req_by_query.get(entry["query"])
        if req is None:
            continue
        relevant = {docid for docid, dtype in dt.items() if dtype == req.requirement_id}
        if not relevant:
            continue  # requisito 'field' o tipo sin documento presente -> excluido
        retrieved = {c.get("document_id") for c in entry["citations"] if c.get("document_id")}
        hit = retrieved & relevant
        retr_points.append({
            "requirement_id": req.requirement_id,
            "precision_at_k": (len(hit) / len(retrieved)) if retrieved else 0.0,
            "recall_at_k": len(hit) / len(relevant),
        })

    n_req = len(BADA_REQUIREMENTS)
    coverage = linked / n_req if n_req else 0.0

    return {
        "case_id": cid,
        "gold_status": gold_status,
        "pred_status": pred_status,
        "correct": gold_status == pred_status,
        "n_evidence": len(evid),
        "evidence_linked": linked,
        "evidence_grounded": grounded,
        "grounding_problems": grounding_problems,
        "evidence_coverage": coverage,
        "retrieval_points": retr_points,
        "latency_ms": {
            "parser": None,       # N/A: sintetico ya canonico (sin Datalab)
            "normalizer": None,   # N/A: sintetico ya canonico
            "indexing": round(lat_index, 2),
            "retrieval": round(lat_retrieval, 2),
            "agent": round(lat_agent, 2),
            "end_to_end": round((time.perf_counter() - t_case) * 1000, 2),
        },
    }


def _prf(cm: dict, cls: str) -> dict:
    tp = cm[cls][cls]
    fp = sum(cm[g][cls] for g in CLASSES) - tp
    fn = sum(cm[cls][p] for p in CLASSES) - tp
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) else 0.0
    return {"precision": round(prec, 4), "recall": round(rec, 4), "f1": round(f1, 4), "support": tp + fn}


def compute_metrics(records: list[dict], min_score: float, top_k: int) -> dict:
    ok = [r for r in records if "error" not in r]
    n = len(ok)
    cm = {g: {p: 0 for p in CLASSES} for g in CLASSES}
    for r in ok:
        if r["gold_status"] in cm and r["pred_status"] in cm[r["gold_status"]]:
            cm[r["gold_status"]][r["pred_status"]] += 1
    correct = sum(cm[c][c] for c in CLASSES)
    per_class = {c: _prf(cm, c) for c in CLASSES}
    f1_macro = round(sum(per_class[c]["f1"] for c in CLASSES) / len(CLASSES), 4)

    all_points = [p for r in ok for p in r["retrieval_points"]]
    ret_p = round(sum(p["precision_at_k"] for p in all_points) / len(all_points), 4) if all_points else None
    ret_r = round(sum(p["recall_at_k"] for p in all_points) / len(all_points), 4) if all_points else None

    tot_linked = sum(r["evidence_linked"] for r in ok)
    tot_grounded = sum(r["evidence_grounded"] for r in ok)

    def lat_mean(key):
        vals = [r["latency_ms"][key] for r in ok if r["latency_ms"][key] is not None]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "n_cases": n,
        "min_score": min_score,
        "top_k": top_k,
        "accuracy": round(correct / n, 4) if n else None,
        "confusion_matrix": {"axes": "gold(fila) x pred(col)", "classes": CLASSES, "matrix": cm},
        "precision_per_class": {c: per_class[c]["precision"] for c in CLASSES},
        "recall_per_class": {c: per_class[c]["recall"] for c in CLASSES},
        "f1_per_class": {c: per_class[c]["f1"] for c in CLASSES},
        "f1_macro": f1_macro,
        "retrieval_precision_at_k": ret_p,
        "retrieval_recall_at_k": ret_r,
        "retrieval_at_k_n_points": len(all_points),
        "evidence_coverage": round(sum(r["evidence_coverage"] for r in ok) / n, 4) if n else None,
        "grounding_validity": round(tot_grounded / tot_linked, 4) if tot_linked else None,
        "grounding_linked_total": tot_linked,
        "latency_ms_mean": {
            "parser": lat_mean("parser"),
            "normalizer": lat_mean("normalizer"),
            "indexing": lat_mean("indexing"),
            "retrieval": lat_mean("retrieval"),
            "agent": lat_mean("agent"),
            "end_to_end": lat_mean("end_to_end"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RUN_DIR), help="Directorio de salida del run")
    ap.add_argument("--limit", type=int, default=None, help="Procesar solo los N primeros casos (validacion)")
    ap.add_argument("--cases", nargs="*", default=None, help="Lista explicita de case_id")
    ap.add_argument("--min-score", type=float, default=0.2)
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()

    out_dir = Path(args.out)
    manifest = json.loads((DATASET / "manifest.json").read_bytes())
    case_ids = args.cases or [c["case_id"] for c in manifest]
    if args.limit:
        case_ids = case_ids[: args.limit]

    print(f"== E2E == casos={len(case_ids)} min_score={args.min_score} top_k={args.top_k} out={out_dir}")
    t0 = time.time()
    records = []
    for cid in case_ids:
        try:
            r = process_case(cid, out_dir, args.min_score, args.top_k)
            flag = "OK " if r["correct"] else "XX "
            print(f"  {flag}{cid}: gold={r['gold_status']:<10} pred={r['pred_status']:<10} "
                  f"grounding={r['evidence_grounded']}/{r['evidence_linked']} e2e={r['latency_ms']['end_to_end']}ms")
        except Exception:
            print(f"  ERR {cid}:\n{traceback.format_exc()}")
            r = {"case_id": cid, "error": traceback.format_exc()}
        records.append(r)

    metrics = compute_metrics(records, args.min_score, args.top_k)
    metrics["elapsed_s"] = round(time.time() - t0, 2)
    metrics["errors"] = [r["case_id"] for r in records if "error" in r]
    _dump(out_dir / "metrics" / "metrics.json", metrics)
    _dump(out_dir / "metrics" / "per_case.json", records)

    print(f"\n=== METRICAS (min_score={args.min_score}) ===")
    print(f"  accuracy={metrics['accuracy']}  f1_macro={metrics['f1_macro']}")
    print(f"  recall_per_class={metrics['recall_per_class']}")
    print(f"  retrieval@{args.top_k}: P={metrics['retrieval_precision_at_k']} R={metrics['retrieval_recall_at_k']} "
          f"(n={metrics['retrieval_at_k_n_points']})")
    print(f"  evidence_coverage={metrics['evidence_coverage']}  grounding_validity={metrics['grounding_validity']}")
    print(f"  confusion (gold x pred): {metrics['confusion_matrix']['matrix']}")
    print(f"  latencias_ms(media)={metrics['latency_ms_mean']}")
    print(f"  errores={metrics['errors']}  elapsed={metrics['elapsed_s']}s")
    return 1 if metrics["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
