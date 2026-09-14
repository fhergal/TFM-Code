# Verificación de reproducibilidad — 2026-09-14

Re-ejecución independiente de `05_eval/results/e2e_2026-09-12_01/run_e2e.py`
(mismo script, mismos parámetros: `min_score=0.72`, `top_k=3`, 20 casos del
dataset sintético BADA v1), dos días después del run oficial citado en el
Anexo F de la memoria, sobre un checkout limpio de `C:\Dev\TFM-Code`.

No se ha modificado la memoria (ya cerrada) ni el Anexo F: esta carpeta es
material de apoyo para la defensa del 21-sep-2026, no un anexo nuevo.

## Resultado

Reproducción **exacta** de la clasificación y de todas las métricas de
decisión y recuperación del run congelado:

| Métrica | e2e_2026-09-12_01 (oficial) | e2e_2026-09-14_repro (hoy) |
|---|---|---|
| accuracy | 0,65 | 0,65 |
| f1_macro | 0,3692 | 0,3692 |
| recall VÁLIDO / INCOMPLETO / RECHAZADO | 1,00 / 0,20 / 0,00 | 1,00 / 0,20 / 0,00 |
| matriz de confusión | idéntica | idéntica |
| retrieval@3 (P / R, n=85) | 0,51 / 1,00 | 0,5078 / 1,00 |
| evidence_coverage | 0,88 | 0,8812 |
| grounding_validity | 1,00 | 1,00 |

Únicas diferencias: latencias (más lentas hoy — indexación 8,86 s vs 5,41 s,
retrieval 694 ms vs 335 ms, e2e 9,56 s vs 5,75 s), atribuibles a la máquina/
carga en el momento de ejecutar, no al pipeline ni a los datos.

No se versiona el índice ChromaDB binario (`.chroma/`, generado por caso y
descartable) por el mismo motivo que en `e2e_2026-09-12_01/`.

## Cómo se generó

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python 05_eval/results/e2e_2026-09-12_01/run_e2e.py \
    --min-score 0.72 --out 05_eval/results/e2e_2026-09-14_repro/
```
