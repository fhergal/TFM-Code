"""Generador de dataset sintético BADA — Fase 1 (inyección de lógica de negocio).

Produce expedientes sintéticos conformes a `CanonicalDocumentParse v1.1`
(specs/canonical_document_parse.schema.json), coherentes entre documentos del
mismo expediente (mismo DNI/NUSS/nombre en todos los documentos que lo citan),
y con `bastanteo_gold` calculado de forma determinista a partir de qué
documentos se han incluido.

Es la Fase 1 del pipeline descrito en la memoria (Faker + reglas de negocio).
Las fases siguientes (LayoutDM para variabilidad estructural, SynthDoG para
render visual, augmentación) toman como entrada el JSON gold que aquí se
genera; no dependen de él en el otro sentido.

Diferencia respecto al script del Anexo C de la memoria (`generador_inss.py`):
aquel es un ejemplo genérico de "cómo generar datos con Faker" con un JSON
plano propio. Este genera directamente instancias reales del contrato
`CanonicalDocumentParse v1.1` que usa el resto del sistema (normalizer, RAG,
agente), usando los 6 tipos documentales y 8 requisitos reales de
`04_src/agent/catalog.py` (BADA_REQUIREMENTS).

Uso:
    pip install faker
    python3 generador_bada.py --n 20 --out ../synthetic_v1 --seed 42
"""

from __future__ import annotations

import argparse
import json
import random
import uuid
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

fake = Faker("es_ES")

# ---------------------------------------------------------------------------
# Lógica de negocio: identificadores administrativos válidos
# ---------------------------------------------------------------------------

_DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"


def generar_dni_valido() -> str:
    numero = random.randint(10000000, 99999999)
    letra = _DNI_LETTERS[numero % 23]
    return f"{numero}{letra}"


def generar_nuss() -> str:
    provincia = f"{random.randint(1, 52):02d}"
    secuencia = f"{random.randint(10000000, 99999999)}"
    control = f"{random.randint(0, 99):02d}"
    return f"{provincia}{secuencia}{control}"


def fecha_str(d: date) -> str:
    return d.strftime("%d/%m/%Y")


# ---------------------------------------------------------------------------
# Definición de los 6 documentos reales del expediente BADA
# (ver 04_src/agent/catalog.py y 04_src/ui/sample_case.json)
# ---------------------------------------------------------------------------

DOCUMENT_TYPES_REQUIRED = [
    "ae_ciu_sol_prestacion",     # DOC-0001, incluye campos identificativo + consentimiento
    "ae_con_cer_rgecivil",       # DOC-0002
    "ae_ciu_acr_residencia",     # DOC-0003
    "ae_ciu_acr_acreditativo",   # DOC-0004
]
DOCUMENT_TYPES_CONDITIONAL = [
    "ae_con_cer_vinculoconyugal",  # DOC-0005, solo si has_spouse
    "ae_con_cer_discapacidad",     # DOC-0006, solo si has_dependent_disability
]

# Requisitos evaluados por el agente sobre el expediente (BADA_REQUIREMENTS)
REQUIREMENTS = [
    ("ae_ciu_sol_prestacion", "document", "required"),
    ("ae_ciu_ide_identificativo", "field", "required"),
    ("ae_con_cer_rgecivil", "document", "required"),
    ("ae_ciu_acr_residencia", "document", "required"),
    ("ae_ciu_acr_acreditativo", "document", "required"),
    ("ae_con_cer_vinculoconyugal", "document", "conditional"),
    ("ae_con_cer_discapacidad", "document", "conditional"),
    ("ae_ciu_del_responsable", "field", "required"),
]


def _bbox(x0, y0, x1, y1):
    return {"x0": x0, "y0": y0, "x1": x1, "y1": y1, "unit": "pixel"}


def _block(block_id, block_type, text, bbox, reading_order, section, entity_type=None,
           required_for_bastanteo=False, label=None):
    b = {
        "block_id": block_id,
        "block_type": block_type,
        "text": text,
        "normalized_text": text,
        "bbox": bbox,
        "reading_order": reading_order,
        "semantics": {"section": section, "required_for_bastanteo": required_for_bastanteo},
    }
    if entity_type:
        b["semantics"]["entity_type"] = entity_type
    if label:
        b["label"] = label
    return b


# ---------------------------------------------------------------------------
# Generación de un expediente completo
# ---------------------------------------------------------------------------

def generar_persona() -> dict:
    genero = random.choice(["M", "F"])
    nombre = fake.first_name_male() if genero == "M" else fake.first_name_female()
    return {
        "nombre_completo": f"{nombre} {fake.last_name()} {fake.last_name()}",
        "dni": generar_dni_valido(),
        "nuss": generar_nuss(),
        "fecha_nacimiento": fecha_str(fake.date_of_birth(minimum_age=18, maximum_age=80)),
        "genero": genero,
    }


def documento_solicitud(persona: dict, dni_override: str | None = None,
                         incluir_consentimiento: bool = True) -> dict:
    dni_texto = dni_override if dni_override else persona["dni"]
    blocks = [
        _block("B001", "title",
               "Solicitud de asistencia sanitaria para migrantes en estancia temporal en España (formulario C-157)",
               _bbox(100, 60, 900, 120), 1, "cabecera"),
        _block("B002", "form_field", f"DNI del solicitante: {dni_texto}",
               _bbox(412, 826, 890, 904), 2, "datos_solicitante",
               entity_type="dni", required_for_bastanteo=True, label="DNI"),
        _block("B003", "form_field", f"Nombre y apellidos: {persona['nombre_completo']}",
               _bbox(100, 700, 900, 760), 3, "datos_solicitante",
               entity_type="person_name", required_for_bastanteo=True, label="Nombre"),
        _block("B004", "form_field", f"NUSS: {persona['nuss']}",
               _bbox(100, 780, 900, 820), 4, "datos_solicitante",
               entity_type="nuss", required_for_bastanteo=False, label="NUSS"),
        _block("B005", "paragraph",
               "Motivo de la solicitud: asistencia sanitaria durante la estancia temporal en "
               "España del pensionista español de origen residente en el extranjero.",
               _bbox(100, 950, 900, 1000), 5, "alegaciones"),
    ]
    if incluir_consentimiento:
        blocks.append(_block(
            "B006", "paragraph",
            "Declaro que son ciertos los datos incluidos en esta solicitud. Doy mi "
            "consentimiento para consultar y recabar electrónicamente los datos en poder "
            "de otras administraciones.",
            _bbox(100, 1050, 900, 1120), 6, "consentimiento"))
    blocks.append(_block("B007", "signature",
                          "Firma manuscrita del solicitante presente al pie del documento.",
                          _bbox(700, 3100, 950, 3300), 7, "cierre",
                          entity_type="signature_presence"))
    return {
        "document_id": "DOC-0001",
        "document_type_pred": "ae_ciu_sol_prestacion",
        "document_type_gold": "ae_ciu_sol_prestacion",
        "origin": {"source_format": "scan", "file_name": "C-157_solicitud.pdf", "page_count": 1},
        "document_metadata": {
            "issuer_org": "INSS", "language": "es", "signature_status": "firma_manuscrita",
        },
        "pages": [{"page_number": 1, "blocks": blocks}],
    }


def documento_generico(document_id: str, document_type: str, file_name: str, issuer_org: str,
                        texto: str, entity_type: str | None = None) -> dict:
    return {
        "document_id": document_id,
        "document_type_pred": document_type,
        "document_type_gold": document_type,
        "origin": {"source_format": "scan", "file_name": file_name, "page_count": 1},
        "document_metadata": {"issuer_org": issuer_org, "language": "es"},
        "pages": [{
            "page_number": 1,
            "blocks": [_block("B001", "paragraph", texto, _bbox(100, 100, 900, 150), 1,
                               "acreditacion", entity_type=entity_type)],
        }],
    }


def generar_expediente(idx: int, escenario: str) -> dict:
    """escenario in {'valido', 'incompleto', 'rechazado'}"""
    persona = generar_persona()
    has_spouse = random.random() < 0.35
    has_dependent = random.random() < 0.25

    case_id = f"EXP-SYN-{idx:04d}"

    # --- Contradicción deliberada para casos RECHAZADO: DNI no coincide ---
    dni_solicitud_override = None
    if escenario == "rechazado":
        dni_solicitud_override = generar_dni_valido()  # DNI distinto al del certificado

    documents = [documento_solicitud(persona, dni_override=dni_solicitud_override)]

    documents.append(documento_generico(
        "DOC-0002", "ae_con_cer_rgecivil", "certificado_nacimiento.pdf", "Registro Civil",
        f"Certificación literal de nacimiento de {persona['nombre_completo']} "
        f"(DNI {persona['dni']}) que acredita la nacionalidad española de origen.",
        entity_type="document_number"))

    documents.append(documento_generico(
        "DOC-0003", "ae_ciu_acr_residencia", "certificado_padron.pdf", "Consulado de España",
        f"Certificado de inscripción en el Padrón de Españoles Residentes en el Extranjero "
        f"(PERE) de {persona['nombre_completo']}.",
        entity_type="address"))

    # --- Documento(s) omitido(s) para casos INCOMPLETO ---
    # Se elige de forma determinista (no probabilística) cuál de los dos
    # documentos candidatos se omite, para garantizar que todo caso marcado
    # como "incompleto" quede realmente incompleto (bug real detectado en
    # validación: con lógica puramente aleatoria, algunos casos "incompleto"
    # no omitían ningún documento y el gold calculado salía VALIDO).
    omitir_doc4 = escenario == "incompleto" and random.random() < 0.7
    omitir_doc2 = escenario == "incompleto" and not omitir_doc4

    if not omitir_doc4:
        documents.append(documento_generico(
            "DOC-0004", "ae_ciu_acr_acreditativo", "certificado_laboral.pdf",
            "Consejería de Trabajo",
            f"Documento oficial que acredita que {persona['nombre_completo']} es "
            f"pensionista o trabajador por cuenta ajena en el país de procedencia."))

    if omitir_doc2:
        documents = [d for d in documents if d["document_id"] != "DOC-0002"]

    if has_spouse:
        conyuge = generar_persona()
        documents.append(documento_generico(
            "DOC-0005", "ae_con_cer_vinculoconyugal", "libro_familia.pdf", "Registro Civil",
            f"Libro de familia y certificado de inscripción de matrimonio de "
            f"{persona['nombre_completo']} con {conyuge['nombre_completo']}."))

    if has_dependent:
        documents.append(documento_generico(
            "DOC-0006", "ae_con_cer_discapacidad", "certificado_discapacidad.pdf", "IMSERSO",
            "Certificado de discapacidad del descendiente mayor de 26 años a cargo, "
            "con grado reconocido igual o superior al 65 por ciento.",
            entity_type=None))

    expected_document_map = [
        {"document_type": t, "required": True} for t in DOCUMENT_TYPES_REQUIRED
    ] + [
        {"document_type": t, "required": "condicional"} for t in DOCUMENT_TYPES_CONDITIONAL
    ]

    # --- bastanteo_gold determinista a partir de lo generado ---
    doc_types_present = {d["document_type_gold"] for d in documents}
    missing_required = [t for t in DOCUMENT_TYPES_REQUIRED if t not in doc_types_present]

    if escenario == "rechazado":
        status = "RECHAZADO"
        notes = "DNI del solicitante no coincide con el DNI acreditado en la certificación de nacimiento."
    elif missing_required:
        status = "INCOMPLETO"
        notes = f"Faltan documentos obligatorios: {', '.join(missing_required)}."
    else:
        status = "VALIDO"
        notes = "Expediente completo: todos los requisitos obligatorios y condicionales aplicables están soportados."

    bastanteo_gold = {"status": status, "notes": notes}

    case = {
        "schema_version": "1.1",
        "case_id": case_id,
        "procedure_type": "aex_gestprestaciones_bada",
        "source_batch_id": "synthetic-v1-fase1",
        "case_context": {
            "domain": "asistencia_sanitaria_migrantes",
            "language_expected": ["es"],
            "country": "ES",
        },
        "expected_document_map": expected_document_map,
        "document_inventory": documents,
        "bastanteo_gold": bastanteo_gold,
        # Metadatos internos de generación (no forman parte del contrato v1.1,
        # se usan para el análisis de la evaluación; se pueden separar en un
        # fichero de metadata si el validador es estricto con propiedades extra).
        "_gen_meta": {
            "escenario": escenario,
            "has_spouse": has_spouse,
            "has_dependent_disability": has_dependent,
            "persona_dni": persona["dni"],
        },
    }
    return case


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Genera dataset sintético BADA v1 (Fase 1: Faker + reglas de negocio)")
    parser.add_argument("--n", type=int, default=20, help="Número de expedientes a generar")
    parser.add_argument("--out", type=str, default="../synthetic_v1", help="Carpeta de salida")
    parser.add_argument("--seed", type=int, default=42, help="Semilla aleatoria (reproducibilidad)")
    args = parser.parse_args()

    random.seed(args.seed)
    Faker.seed(args.seed)

    out_dir = Path(__file__).parent / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # Distribución de escenarios: 60% válido, 25% incompleto, 15% rechazado
    escenarios = (
        ["valido"] * int(args.n * 0.60)
        + ["incompleto"] * int(args.n * 0.25)
        + ["rechazado"] * int(args.n * 0.15)
    )
    while len(escenarios) < args.n:
        escenarios.append("valido")
    random.shuffle(escenarios)

    manifest = []
    inconsistencias = []
    for i, escenario in enumerate(escenarios[: args.n], start=1):
        case = generar_expediente(i, escenario)
        # Chequeo de consistencia: un caso "incompleto"/"rechazado" debe dar
        # ese mismo gold, no VALIDO. Falla ruidosamente en vez de generar
        # datos de evaluación silenciosamente incorrectos.
        expected_status = {"valido": "VALIDO", "incompleto": "INCOMPLETO", "rechazado": "RECHAZADO"}[escenario]
        if case["bastanteo_gold"]["status"] != expected_status:
            inconsistencias.append((case["case_id"], escenario, case["bastanteo_gold"]["status"]))
        fname = f"{case['case_id']}.json"
        with open(out_dir / fname, "w", encoding="utf-8") as f:
            json.dump(case, f, ensure_ascii=False, indent=2)
        manifest.append({
            "case_id": case["case_id"],
            "file": fname,
            "escenario": escenario,
            "status_gold": case["bastanteo_gold"]["status"],
            "n_documentos": len(case["document_inventory"]),
        })

    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Generados {len(manifest)} expedientes en {out_dir}")
    for status in ["VALIDO", "INCOMPLETO", "RECHAZADO"]:
        n = sum(1 for m in manifest if m["status_gold"] == status)
        print(f"  {status}: {n}")

    if inconsistencias:
        print(f"\n⚠️  {len(inconsistencias)} inconsistencia(s) escenario↔gold detectada(s):")
        for case_id, escenario, status_real in inconsistencias:
            print(f"   - {case_id}: escenario={escenario!r} pero gold={status_real!r}")
        raise SystemExit(1)
    else:
        print("\nOK: todos los escenarios coinciden con su bastanteo_gold calculado.")


if __name__ == "__main__":
    main()
