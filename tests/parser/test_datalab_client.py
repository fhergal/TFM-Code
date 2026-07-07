"""Tests del wrapper de parser (DatalabParser), sin llamar a la API real.

Se simula (monkeypatch) datalab_sdk.DatalabClient para no gastar creditos ni
depender de red durante los tests. El objetivo es comprobar que ParserResult
se rellena correctamente a partir de lo que devuelve el SDK, no probar el
SDK de Datalab en si.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


class _FakeConvertResult:
    """Imita el objeto que devuelve datalab_sdk.DatalabClient.convert(...)."""

    def __init__(self):
        self.json = {"blocks": [{"block_id": "b1", "type": "paragraph", "text": "hola"}]}
        self.markdown = "# hola"
        self.page_count = 1
        self.parse_quality_score = 4.2
        self.cost_breakdown = {"cents": 3}
        self.checkpoint_id = "chk_123"


class _FakeDatalabClient:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def convert(self, path, options=None):
        assert Path(path).exists(), "el fake client tambien exige que el fichero exista"
        return _FakeConvertResult()


class _FakeConvertOptions:
    def __init__(self, output_format="json", mode="balanced"):
        self.output_format = output_format
        self.mode = mode


@pytest.fixture(autouse=True)
def fake_datalab_sdk(monkeypatch):
    """Inyecta un modulo `datalab_sdk` falso en sys.modules antes de importar
    nuestro codigo, para no depender del paquete real ni de la API."""
    fake_module = types.ModuleType("datalab_sdk")
    fake_module.DatalabClient = _FakeDatalabClient
    fake_module.ConvertOptions = _FakeConvertOptions
    monkeypatch.setitem(sys.modules, "datalab_sdk", fake_module)
    monkeypatch.setenv("DATALAB_API_KEY", "fake-key-for-tests")
    yield


@pytest.fixture
def sample_file(tmp_path):
    f = tmp_path / "documento.pdf"
    f.write_bytes(b"%PDF-1.4 contenido de prueba")
    return f


def test_parse_returns_parser_result_with_expected_fields(sample_file):
    from parser import get_parser

    parser = get_parser("datalab", mode="balanced")
    result = parser.parse(sample_file, output_format="json")

    assert result.backend == "datalab"
    assert result.source_path == sample_file
    assert result.output_format == "json"
    assert result.raw == {"blocks": [{"block_id": "b1", "type": "paragraph", "text": "hola"}]}
    assert result.page_count == 1
    assert result.quality_score == 4.2
    assert result.elapsed_seconds is not None and result.elapsed_seconds >= 0
    assert result.extra_metadata["checkpoint_id"] == "chk_123"


def test_parse_raises_if_file_missing(tmp_path):
    from parser import get_parser

    parser = get_parser("datalab")
    with pytest.raises(FileNotFoundError):
        parser.parse(tmp_path / "no_existe.pdf")


def test_missing_api_key_raises_clear_error(monkeypatch, fake_datalab_sdk):
    monkeypatch.delenv("DATALAB_API_KEY", raising=False)
    from parser import get_parser

    with pytest.raises(RuntimeError, match="DATALAB_API_KEY"):
        get_parser("datalab")


def test_unknown_backend_raises_value_error():
    from parser import get_parser

    with pytest.raises(ValueError, match="datalab"):
        get_parser("no-existe-este-backend")
