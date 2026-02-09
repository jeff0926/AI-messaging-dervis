"""Tests for FunctionCatalog service and CatalogManager agent."""

import pytest
from unittest.mock import patch

from src.services.function_catalog import FunctionCatalog, FunctionEntry
from src.agents.catalog_manager import CatalogManager
from src.schemas import AgentPayload, NotificationStatus


# ------------------------------------------------------------------
# FunctionCatalog service tests
# ------------------------------------------------------------------

@pytest.fixture
def catalog(tmp_path):
    return FunctionCatalog(functions_dir=tmp_path)


def test_save_and_get(catalog):
    entry = FunctionEntry(name="find_trending", description="Find trending topics")
    catalog.save(entry)
    result = catalog.get("find_trending")
    assert result is not None
    assert result.name == "find_trending"
    assert result.description == "Find trending topics"


def test_get_nonexistent(catalog):
    assert catalog.get("nonexistent") is None


def test_list_all_empty(catalog):
    assert catalog.list_all() == []


def test_list_all_sorted(catalog):
    catalog.save(FunctionEntry(name="zebra", description="Z func"))
    catalog.save(FunctionEntry(name="alpha", description="A func"))
    entries = catalog.list_all()
    assert [e.name for e in entries] == ["alpha", "zebra"]


def test_delete(catalog):
    catalog.save(FunctionEntry(name="temp", description="temporary"))
    assert catalog.delete("temp") is True
    assert catalog.get("temp") is None


def test_delete_nonexistent(catalog):
    assert catalog.delete("nonexistent") is False


def test_search_by_name(catalog):
    catalog.save(FunctionEntry(name="find_trending", description="Trends"))
    catalog.save(FunctionEntry(name="summarize_text", description="Summaries"))
    results = catalog.search("trending")
    assert len(results) == 1
    assert results[0].name == "find_trending"


def test_search_by_description(catalog):
    catalog.save(FunctionEntry(name="func1", description="Analyze social media"))
    results = catalog.search("social")
    assert len(results) == 1


def test_search_by_tag(catalog):
    entry = FunctionEntry(name="func1", description="A function", tags=["research", "ai"])
    catalog.save(entry)
    results = catalog.search("research")
    assert len(results) == 1


def test_search_no_results(catalog):
    catalog.save(FunctionEntry(name="func1", description="A function"))
    assert catalog.search("xyz123") == []


def test_stats(catalog):
    catalog.save(FunctionEntry(name="f1", description="A", tags=["tag1", "tag2"]))
    catalog.save(FunctionEntry(name="f2", description="B", tags=["tag2", "tag3"]))
    stats = catalog.stats()
    assert stats["total_functions"] == 2
    assert sorted(stats["tags"]) == ["tag1", "tag2", "tag3"]


def test_persistence(tmp_path):
    """Functions persist across catalog instances."""
    cat1 = FunctionCatalog(functions_dir=tmp_path)
    cat1.save(FunctionEntry(name="persistent_func", description="I persist"))

    cat2 = FunctionCatalog(functions_dir=tmp_path)
    result = cat2.get("persistent_func")
    assert result is not None
    assert result.description == "I persist"


def test_save_overwrites(catalog):
    catalog.save(FunctionEntry(name="f1", description="version 1"))
    catalog.save(FunctionEntry(name="f1", description="version 2"))
    assert catalog.get("f1").description == "version 2"
    assert len(catalog.list_all()) == 1


def test_entry_summary():
    entry = FunctionEntry(name="func", description="Does stuff", tags=["ai", "research"])
    assert "func" in entry.summary()
    assert "Does stuff" in entry.summary()
    assert "ai" in entry.summary()


def test_entry_to_dict_and_back():
    entry = FunctionEntry(
        name="test", description="A test", source="print('hello')",
        tags=["demo"], created_by="user1",
    )
    data = entry.to_dict()
    restored = FunctionEntry.from_dict(data)
    assert restored.name == entry.name
    assert restored.source == entry.source
    assert restored.tags == entry.tags


# ------------------------------------------------------------------
# CatalogManager agent tests
# ------------------------------------------------------------------

def _payload(action: str, query: str = "", user_id: str = "user1") -> AgentPayload:
    return AgentPayload(
        command_id="cmd-1",
        namespace="catalog",
        action=action,
        payload={"query": query},
        context={"user_id": user_id, "source_channel": "telegram"},
    )


@pytest.fixture
def manager(tmp_path):
    catalog = FunctionCatalog(functions_dir=tmp_path)
    return CatalogManager(catalog=catalog)


@pytest.mark.asyncio
async def test_save_function(manager):
    result = await manager.handle(_payload("save", 'find_trending "Search trending topics"'))
    assert result.status == NotificationStatus.COMPLETED
    assert "find_trending" in result.message
    assert "saved" in result.message


@pytest.mark.asyncio
async def test_list_empty(manager):
    result = await manager.handle(_payload("list"))
    assert result.status == NotificationStatus.COMPLETED
    assert "empty" in result.message


@pytest.mark.asyncio
async def test_list_with_entries(manager):
    await manager.handle(_payload("save", 'func1 "First function"'))
    await manager.handle(_payload("save", 'func2 "Second function"'))
    result = await manager.handle(_payload("list"))
    assert result.status == NotificationStatus.COMPLETED
    assert "func1" in result.message
    assert "func2" in result.message
    assert "2 functions" in result.message


@pytest.mark.asyncio
async def test_info(manager):
    await manager.handle(_payload("save", 'my_func "A useful function"'))
    result = await manager.handle(_payload("info", "my_func"))
    assert result.status == NotificationStatus.COMPLETED
    assert "my_func" in result.message
    assert "A useful function" in result.message


@pytest.mark.asyncio
async def test_info_not_found(manager):
    result = await manager.handle(_payload("info", "nonexistent"))
    assert result.status == NotificationStatus.FAILED


@pytest.mark.asyncio
async def test_search(manager):
    await manager.handle(_payload("save", 'find_trending "Search trending topics"'))
    await manager.handle(_payload("save", 'summarize "Summarize text"'))
    result = await manager.handle(_payload("search", "trending"))
    assert result.status == NotificationStatus.COMPLETED
    assert "find_trending" in result.message
    assert "summarize" not in result.message


@pytest.mark.asyncio
async def test_delete(manager):
    await manager.handle(_payload("save", 'temp_func "Temporary"'))
    result = await manager.handle(_payload("delete", "temp_func"))
    assert result.status == NotificationStatus.COMPLETED
    assert "deleted" in result.message


@pytest.mark.asyncio
async def test_tag(manager):
    await manager.handle(_payload("save", 'my_func "A function"'))
    result = await manager.handle(_payload("tag", "my_func research ai"))
    assert result.status == NotificationStatus.COMPLETED
    assert "research" in result.message
    assert "ai" in result.message


@pytest.mark.asyncio
async def test_help(manager):
    result = await manager.handle(_payload("help"))
    assert result.status == NotificationStatus.COMPLETED
    assert "catalog" in result.message.lower()


@pytest.mark.asyncio
async def test_unknown_action(manager):
    result = await manager.handle(_payload("unknown_action"))
    assert result.status == NotificationStatus.FAILED


@pytest.mark.asyncio
async def test_admin_gate_blocks_non_admin(manager):
    with patch("src.agents.catalog_manager.ADMIN_USER_IDS", {"admin1"}):
        result = await manager.handle(
            _payload("save", 'blocked_func "Should fail"', user_id="not_admin")
        )
        assert result.status == NotificationStatus.FAILED
        assert "Permission denied" in result.message


@pytest.mark.asyncio
async def test_admin_gate_allows_admin(manager):
    with patch("src.agents.catalog_manager.ADMIN_USER_IDS", {"admin1"}):
        result = await manager.handle(
            _payload("save", 'allowed_func "Should work"', user_id="admin1")
        )
        assert result.status == NotificationStatus.COMPLETED


@pytest.mark.asyncio
async def test_public_actions_always_allowed(manager):
    await manager.handle(_payload("save", 'visible_func "Public read"'))
    with patch("src.agents.catalog_manager.ADMIN_USER_IDS", {"admin1"}):
        result = await manager.handle(_payload("list", user_id="random"))
        assert result.status == NotificationStatus.COMPLETED
        result = await manager.handle(_payload("search", "visible", user_id="random"))
        assert result.status == NotificationStatus.COMPLETED
