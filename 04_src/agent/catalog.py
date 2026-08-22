"""Catalogo de `Requirement` para el caso de uso real usado en el PoC:
BADA (Base de Datos de Asistencia Sanitaria, prestacion 213), expediente
SGDA `aex_gestprestaciones_bada` -- formulario C-157 "Asistencia sanitaria
para migrantes en estancia temporal en Espana".

Fuente: mapa documental BADA v02.00 (BORRADOR) aportado por Fer + el
formulario C-157 real. Los `requirement_id` son directamente los codigos
de tipologia documental del SGDA (empiezan por `ae_`), para que la
evidencia del agente quede trazable hasta el mapa documental oficial, no
solo hasta un ID interno inventado.

BADA_REQUIREMENTS cubre el flujo tipico del Supuesto A/B del C-157:
solicitud + identificacion + acreditacion de residencia/situacion laboral
+ (si viaja con familiares) vinculo familiar + discapacidad si procede.

Este catalogo SIGUE siendo una base de trabajo, no el catalogo normativo
definitivo del TFM: faltan variantes (DNI vs NIE vs pasaporte, libro de
familia vs certificado de matrimonio, etc.) que se iran ampliando segun
Fer aporte mas ejemplos del mapa documental.
"""

from __future__ import annotations

from .base import Requirement

BADA_REQUIREMENTS: list[Requirement] = [
    Requirement(
        requirement_id="ae_ciu_sol_prestacion",
        claim="Consta la solicitud de prestacion (formulario C-157) cumplimentada",
        query="Consta el formulario de solicitud de asistencia sanitaria para migrantes en estancia temporal?",
        requirement_type="required",
        evidence_type="document",
    ),
    Requirement(
        requirement_id="ae_ciu_ide_identificativo",
        claim="Consta el documento identificativo (DNI/NIE/Pasaporte) del solicitante",
        query="Cual es el DNI, NIE o pasaporte del solicitante?",
        requirement_type="required",
        evidence_type="field",
    ),
    Requirement(
        requirement_id="ae_con_cer_rgecivil",
        claim="Consta la certificacion literal de nacimiento que acredita la nacionalidad espanola de origen",
        query="Consta la certificacion literal de nacimiento que acredita la nacionalidad espanola de origen?",
        requirement_type="required",
        evidence_type="document",
    ),
    Requirement(
        requirement_id="ae_ciu_acr_residencia",
        claim="Consta el certificado de inscripcion en el Padron de Espanoles Residentes en el Extranjero",
        query="Consta el certificado de inscripcion en el Padron de Espanoles Residentes en el Extranjero?",
        requirement_type="required",
        evidence_type="document",
    ),
    Requirement(
        requirement_id="ae_ciu_acr_acreditativo",
        claim="Consta el documento oficial que acredita la condicion de pensionista o trabajador en el pais de procedencia",
        query="Consta el documento oficial que acredita que es pensionista o trabajador en el pais de procedencia?",
        requirement_type="required",
        evidence_type="document",
    ),
    Requirement(
        requirement_id="ae_con_cer_vinculoconyugal",
        claim="Si viaja con conyuge, consta el libro de familia o certificado de inscripcion de matrimonio",
        query="Consta el libro de familia o certificado de inscripcion de matrimonio del conyuge?",
        requirement_type="conditional",
        evidence_type="document",
    ),
    Requirement(
        requirement_id="ae_con_cer_discapacidad",
        claim="Si hay descendientes mayores de 26 anos a cargo, consta el certificado de discapacidad (>=65%)",
        query="Consta el certificado de discapacidad de un descendiente mayor de 26 anos a cargo?",
        requirement_type="conditional",
        evidence_type="document",
    ),
    Requirement(
        requirement_id="ae_ciu_del_responsable",
        claim="Consta la declaracion/alegacion de consentimiento del solicitante",
        query="Da el solicitante su consentimiento para consultar datos de otras administraciones?",
        requirement_type="required",
        evidence_type="field",
    ),
]

# Alias retrocompatible: el resto del codigo (ui/pipeline.py) importa
# EXAMPLE_REQUIREMENTS por nombre. Se mantiene el alias para no tener que
# tocar mas ficheros al pasar del catalogo generico (DNI+firma) al real de BADA.
EXAMPLE_REQUIREMENTS = BADA_REQUIREMENTS
