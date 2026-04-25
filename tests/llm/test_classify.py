from __future__ import annotations

from app.core.config import Settings
from app.services.classify import classify_document
from app.services.llm.client import FakeLLMClient


async def test_classify_uses_fake_llm_for_signal_false() -> None:
    llm = FakeLLMClient(
        {"*": '{"signal": false, "category": "noise", "priority": "low", "confidence": 0.91}'}
    )

    result = await classify_document(
        normalized_text="| From | spam@example.com |\n| Subject | Werbung |",
        llm=llm,
        settings=Settings(),
    )

    assert result.signal is False
    assert result.category == "noise"
    assert result.confidence == 0.91


async def test_classify_parses_heating_signal() -> None:
    llm = FakeLLMClient(
        {
            "*": (
                '{"signal": true, "category": "mieter/heizung", '
                '"priority": "high", "confidence": 0.94}'
            )
        }
    )

    result = await classify_document(
        normalized_text=(
            "| From | julius.nette@outlook.com |\n"
            "| Subject | Heizung defekt |\n\n"
            "## Body\n\nIn EH-001 ist die Heizung kalt."
        ),
        llm=llm,
        settings=Settings(),
    )

    assert result.signal is True
    assert result.category == "mieter/heizung"
    assert result.priority == "high"
