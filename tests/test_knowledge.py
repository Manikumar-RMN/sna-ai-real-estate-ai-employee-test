from core import CompositeKnowledgeProvider, KnowledgeItem
from core.knowledge_memory import InMemoryKnowledgeProvider


def test_in_memory_knowledge_search_ranks_matches():
    provider = InMemoryKnowledgeProvider([
        KnowledgeItem(id="1", title="Pricing", content="Basic plan costs 9999"),
        KnowledgeItem(id="2", title="Cancellation", content="Cancel within 7 days"),
    ])

    results = provider.search("pricing plan", limit=1)

    assert results[0].id == "1"
    assert results[0].score == 2.0


def test_composite_provider_combines_sources():
    first = InMemoryKnowledgeProvider([
        KnowledgeItem(id="1", title="FAQ", content="Support is available")
    ])
    second = InMemoryKnowledgeProvider([
        KnowledgeItem(id="2", title="Product", content="Support includes onboarding")
    ])

    results = CompositeKnowledgeProvider([first, second]).search("support", limit=2)

    assert [item.id for item in results] == ["1", "2"]
