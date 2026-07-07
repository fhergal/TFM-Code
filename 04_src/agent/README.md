# 04_src/agent

Responsabilidad: orquestar el ciclo ReAct de bastanteo — invocar retrieval, comparar campos, y construir la respuesta final (`bastanteo_evidence` + `bastanteo_gold`) con trazabilidad.

No debe: parsear documentos directamente ni acoplarse al backend concreto del vector store.

Nota abierta (ver revisión de decisiones): confirmar si el LLM de este módulo necesita ser multimodal (VLM) o si basta un modelo de texto con buen tool-use, dado que ya opera sobre el JSON canónico y no sobre la imagen cruda.
