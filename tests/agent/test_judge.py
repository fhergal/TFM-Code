import pytest

from agent.judge import RuleBasedJudge, get_judge, AnthropicJudge


def test_rule_based_judge_returns_missing_when_no_citations():
    judge = RuleBasedJudge()
    status, justification, citation = judge.judge("Consta el DNI", [])

    assert status == "missing"
    assert citation is None
    assert "no se encontro" in justification.lower() or "no se encontró" in justification.lower() or "DNI" in justification


def test_rule_based_judge_returns_supported_for_best_scoring_citation():
    judge = RuleBasedJudge(min_score=0.5)
    citations = [
        {"document_id": "DOC-0001", "page_number": 1, "score": 0.4, "text": "ruido"},
        {"document_id": "DOC-0001", "page_number": 2, "score": 0.9, "text": "DNI: 12345678Z"},
    ]

    status, justification, citation = judge.judge("Consta el DNI", citations)

    assert status == "supported"
    assert citation["page_number"] == 2
    assert "0.900" in justification


def test_rule_based_judge_returns_missing_when_best_score_below_threshold():
    judge = RuleBasedJudge(min_score=0.8)
    citations = [{"document_id": "DOC-0001", "page_number": 1, "score": 0.3, "text": "algo"}]

    status, justification, citation = judge.judge("Consta el DNI", citations)

    assert status == "missing"
    assert citation is None


def test_get_judge_factory_returns_rule_based_by_default():
    judge = get_judge()
    assert isinstance(judge, RuleBasedJudge)


def test_get_judge_factory_rejects_unknown_backend():
    with pytest.raises(ValueError):
        get_judge("no-existe")


def test_anthropic_judge_is_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        get_judge("anthropic")
