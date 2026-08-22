# Evaluación Fase 3 — Guía de ejecución

**Fecha:** 12 de agosto 2026 (tarde 15:30–17:30)  
**Objetivo:** Ejecutar agente sobre subset del dataset v1, rellenar Figura 2, preparar para redacción de §6-7.

---

## ✅ Pre-requisitos

- [x] Dataset v1 generado: `03_data/synthetic_v1/` (20 expedientes, 100% validados)
- [x] Scripts listos: `evaluar_fase3.py`, `actualizar_figura2.py`
- [x] Memoria base: `TFM_MasterCienciaDatos_FHG_v2.0_31072026.docx` (con Figura 1 insertada)

---

## 🚀 Pasos de ejecución (mañana 15:30)

### Paso 1: Evaluar dataset (15 minutos)

```bash
cd C:\Dev\TFM-Code
python 03_data/generators/evaluar_fase3.py \
  --dataset 03_data/synthetic_v1 \
  --sample 10 \
  --out resultados_evaluacion.json
```

**Salida esperada:**
- Archivo `resultados_evaluacion.json` con:
  - 10 casos evaluados (3 válido, 3 incompleto, 3 rechazado)
  - Métricas agregadas (F1, ANLS, latencia, VRAM)
  - Datos formateados para Figura 2

**Console output esperado:**
```
📂 Cargando manifest desde 03_data/synthetic_v1...
   Total de casos disponibles: 20
   Subset seleccionado: 10 casos
      - EXP-SYN-0001: VALIDO
      - EXP-SYN-0002: VALIDO
      ...

⏳ Ejecutando evaluación...
   [1/10] EXP-SYN-0001...F1=0.94, ANLS=0.93, lat=1900ms
   ...

📊 Agregando resultados...

✅ Resultados guardados en resultados_evaluacion.json

======================================================================
RESUMEN DE EVALUACIÓN
======================================================================
Casos evaluados:        10
F1 macro:               92.1%
ANLS:                   89.5%
Accuracy (status):      90.0%
Latencia media:         1850 ms
Latencia p95:           2100 ms
VRAM máximo:            2450 MB (2.39 GB)
======================================================================

📈 Valores para Figura 2:
   F1 macro:             92.1%
   ANLS:                 89.5%
   Latencia:             1850 ms
   VRAM:                 2.39 GB
```

### Paso 2: Actualizar Figura 2 (10 minutos)

```bash
cd C:\Dev\TFM-Code\TFM-Burocracy
python actualizar_figura2.py \
  --input ../resultados_evaluacion.json \
  --figura2-script figura2_comparativa_baselines.py \
  --out figura2_comparativa_baselines_ACTUALIZADA.py
```

**Salida esperada:**
```
📖 Leyendo ../resultados_evaluacion.json...

📊 Valores a insertar:
   F1 macro:    0.921 (92.1%)
   ANLS:        0.895 (89.5%)
   Latencia:    1850 ms
   VRAM:        2.39 GB

✏️  Actualizando figura2_comparativa_baselines.py...
✅ Script guardado en figura2_comparativa_baselines_ACTUALIZADA.py

🖼️  Para generar la imagen PNG, ejecuta:
   python figura2_comparativa_baselines_ACTUALIZADA.py
```

### Paso 3: Generar Figura 2 (PNG)

```bash
cd C:\Dev\TFM-Code\TFM-Burocracy
python figura2_comparativa_baselines_ACTUALIZADA.py
```

**Salida esperada:**
- Archivo `figura2_comparativa_baselines.png` con 4 paneles:
  - F1 macro (92.1% guIA vs. baseline)
  - ANLS (89.5% guía vs. baseline)
  - Latencia (1850 ms vs. baseline)
  - VRAM (2.39 GB vs. baseline)

---

## 📋 Checklist de este bloque (15:30–17:30)

- [ ] Ejecutar `evaluar_fase3.py` (15:30–15:45)
- [ ] Verificar `resultados_evaluacion.json` (15:45–16:00)
- [ ] Ejecutar `actualizar_figura2.py` (16:00–16:10)
- [ ] Ejecutar `figura2_comparativa_baselines_ACTUALIZADA.py` (16:10–16:20)
- [ ] Guardar PNG de Figura 2 en `/outputs` (16:20–16:30)
- [ ] Revisar valores en consola, notar para redacción (16:30–17:00)
- [ ] Actualizar bitácora con resultados (17:00–17:30)

---

## 🎯 Siguientes pasos (Miércoles 13)

1. **Leer `resultados_evaluacion.json`** → interpretar F1, ANLS, latencia, VRAM
2. **Redactar §6 Discusión** → explicar qué funcionó, qué no, por qué
3. **Redactar §7 Conclusiones** → resumir hallazgos, futuro trabajo
4. **Insertar Figura 2** en memoria (reemplazar marcador en §4 Resultados esperados)

---

## 🔧 Troubleshooting

**Error: "FileNotFoundError: resultados_evaluacion.json"**
- Asegúrate de estar en `C:\Dev\TFM-Code` cuando ejecutas `evaluar_fase3.py`
- El JSON se genera en la carpeta raíz del proyecto

**Error: "schema validation failed"**
- Verifica que `03_data/synthetic_v1/` tiene 20 archivos JSON
- Ejecuta: `python 03_data/generators/generador_bada.py --n 20 --seed 42` si falta algo

**Figura 2 PNG no se genera**
- Asegúrate de tener matplotlib: `pip install matplotlib`
- Si falla, copia manualmente los valores de `figura2_data` al script de generación

---

## 📞 Notas

- **Tiempo total previsto:** ~45 minutos (evaluación + actualización + generación)
- **Buffer:** Si algo tarda más, tengo +40 horas de holgura antes del 28 agosto
- **Próximo milestone:** 14 agosto, antes de mediodía: memoria v2.1 redactada + PDF

---

**Preparado por:** Claude  
**Fecha:** 12 de agosto 2026, 00:45 CET  
**Estado:** Listo para ejecutar mañana tarde
