"""Demo mínima en Gradio (ver README.md): carga de documento -> parseo ->
normalización -> indexación -> pregunta/respuesta y bastanteo, mostrando
evidencias trazables (documento fuente, pagina, bloque).

No contiene lógica core de parsing/retrieval/juicio -- todo eso vive en
parser/, normalizer/, rag/ y agent/. Este fichero solo cablea componentes
de Gradio contra 04_src/ui/pipeline.py.

Ejecutar:
    python 04_src/ui/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite ejecutar este fichero directamente (python 04_src/ui/app.py) sin
# haber instalado el paquete con pip install -e, igual que run_parser.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gradio as gr

from ui import pipeline


def _citations_to_rows(citations: list[dict]) -> list[list]:
    return [
        [c.get("document_id"), c.get("page_number"), c.get("section"), round(c.get("score") or 0, 3), c.get("text")]
        for c in citations
    ]


def _evidence_to_rows(evidence_list: list[dict]) -> list[list]:
    return [
        [
            e.get("requirement_id"),
            e.get("claim"),
            e.get("status"),
            e.get("linked_document_id") or "-",
            e.get("linked_page") or "-",
            e.get("justification_text"),
        ]
        for e in evidence_list
    ]


def on_process_document(file, case_id, procedure_type):
    if file is None:
        return None, "Sube un documento antes de procesar.", None
    try:
        case = pipeline.process_document(file.name, case_id=case_id or "EXP-0001", procedure_type=procedure_type)
        index = pipeline.build_index_for_case(case)
        retrieve_fn = pipeline.make_retrieve_fn_from_index(index)
        return retrieve_fn, f"Documento procesado. {len(case['document_inventory'])} documento(s) indexado(s).", case
    except pipeline.PipelineError as exc:
        return None, f"No se pudo procesar (modo real): {exc}", None


def on_load_demo():
    retrieve_fn = pipeline.demo_retrieve_fn()
    return retrieve_fn, "Modo demo cargado (expediente de ejemplo, sin API key ni dependencias pesadas)."


def on_ask(retrieve_fn, question):
    if retrieve_fn is None:
        return [["-", "-", "-", "-", "Primero procesa un documento o carga el modo demo."]]
    if not question:
        return []
    citations = pipeline.ask_question(retrieve_fn, question, top_k=5)
    if not citations:
        return [["-", "-", "-", "-", "Sin resultados para esa pregunta."]]
    return _citations_to_rows(citations)


def on_bastanteo(retrieve_fn):
    if retrieve_fn is None:
        return [], "Primero procesa un documento o carga el modo demo."
    result = pipeline.run_bastanteo_over_case(retrieve_fn)
    return _evidence_to_rows(result["bastanteo_evidence"]), (
        f"{result['bastanteo_gold']['status']} — {result['bastanteo_gold']['notes']}"
    )


with gr.Blocks(title="Bastanteo documental — demo TFM/SpecDD") as demo:
    gr.Markdown(
        "# Bastanteo documental (RAG agéntico)\n"
        "Demo de punta a punta: parseo -> normalizacion -> RAG -> agente de bastanteo.\n"
        "Usa **Modo real** con un documento y `DATALAB_API_KEY`, o **Modo demo** sin ninguna dependencia pesada."
    )

    retrieve_fn_state = gr.State(None)
    case_state = gr.State(None)
    status_box = gr.Textbox(label="Estado", interactive=False)

    with gr.Row():
        with gr.Column():
            gr.Markdown("### Modo real")
            file_input = gr.File(label="Documento (PDF/imagen)")
            case_id_input = gr.Textbox(label="case_id", value="EXP-2026-0001")
            procedure_input = gr.Textbox(label="procedure_type", value="prestacion_inss")
            process_btn = gr.Button("Procesar documento")
        with gr.Column():
            gr.Markdown("### Modo demo (sin API key)")
            demo_btn = gr.Button("Cargar expediente de ejemplo")

    process_btn.click(
        on_process_document,
        inputs=[file_input, case_id_input, procedure_input],
        outputs=[retrieve_fn_state, status_box, case_state],
    )
    demo_btn.click(on_load_demo, inputs=[], outputs=[retrieve_fn_state, status_box])

    gr.Markdown("---\n### Pregunta libre (retrieval trazable)")
    question_input = gr.Textbox(label="Pregunta", placeholder="Consta el DNI del solicitante?")
    ask_btn = gr.Button("Preguntar")
    citations_table = gr.Dataframe(
        headers=["documento", "pagina", "seccion", "score", "texto"],
        label="Citas recuperadas",
    )
    ask_btn.click(on_ask, inputs=[retrieve_fn_state, question_input], outputs=[citations_table])

    gr.Markdown("---\n### Bastanteo automatico (catalogo de ejemplo)")
    bastanteo_btn = gr.Button("Ejecutar bastanteo")
    evidence_table = gr.Dataframe(
        headers=["requisito", "claim", "estado", "documento", "pagina", "justificacion"],
        label="bastanteo_evidence",
    )
    gold_box = gr.Textbox(label="bastanteo_gold", interactive=False)
    bastanteo_btn.click(on_bastanteo, inputs=[retrieve_fn_state], outputs=[evidence_table, gold_box])


if __name__ == "__main__":
    demo.launch()
