# 05_eval

Tests, métricas y resultados de la evaluación (F1 documental, ANLS de campos, latencia/VRAM, explicabilidad/grounding).

`results/` está excluido de git salvo que se decida versionar resultados concretos citados en la memoria.

## Evaluación oficial end-to-end: `results/e2e_2026-09-12_01/`

Excepción explícita a la regla anterior: esta carpeta **sí está versionada**, como configuración
congelada del experimento citado en la memoria (Anexo F, §9.6.2 y siguientes) — `accuracy=0.65`,
`f1_macro=0.3692`, `min_score=0.72`, `top_k=3`, sobre los 20 casos del dataset sintético BADA v1.

Contenido:

- `config/` — manifiesto del dataset y del run, barrido de calibración de `min_score`.
- `raw/`, `normalized/`, `chunks/`, `retrieval/`, `agent/` — salida intermedia por expediente en
  cada etapa del pipeline (parser → normalizador → chunking → retrieval semántico → agente).
- `metrics/metrics.json`, `metrics/per_case.json` — métricas agregadas y por expediente (matriz de
  confusión, precision/recall/F1 por clase, recall@3, cobertura de evidencia, grounding, latencias).
- `figures/` — figura de la matriz de confusión (SVG) tal como se referencia en la memoria.
- `logs/e2e-run.log` — log de ejecución del run oficial.
- `run_e2e.py`, `sweep_threshold_real.py`, `make_figures.py` — scripts usados para producir el run
  y calibrar `min_score`.

No se versiona el índice ChromaDB binario (`.chroma/`, ~8 MB) generado durante el run: no aporta
nada legible y es reconstruible a partir de `chunks/` + el modelo de embeddings
(`intfloat/multilingual-e5-small`) declarado en `config/run_manifest.json`.
