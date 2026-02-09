"""Tests for ConversationStore — per-user conversation memory."""

import pytest

from src.services.conversation import ConversationStore


@pytest.fixture
def store():
    return ConversationStore(max_history=5)


def test_add_and_get_messages(store):
    store.add_user_message("u1", "Hello", "telegram")
    store.add_assistant_message("u1", "Hi there", "telegram")
    history = store.get_history("u1", "telegram")
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there"}


def test_separate_channels(store):
    store.add_user_message("u1", "msg-telegram", "telegram")
    store.add_user_message("u1", "msg-slack", "slack")
    assert len(store.get_history("u1", "telegram")) == 1
    assert len(store.get_history("u1", "slack")) == 1
    assert store.get_history("u1", "telegram")[0]["content"] == "msg-telegram"


def test_separate_users(store):
    store.add_user_message("u1", "from-u1", "ch")
    store.add_user_message("u2", "from-u2", "ch")
    assert len(store.get_history("u1", "ch")) == 1
    assert len(store.get_history("u2", "ch")) == 1


def test_max_history_limit(store):
    for i in range(10):
        store.add_user_message("u1", f"msg-{i}")
    history = store.get_history("u1")
    assert len(history) == 5  # max_history=5
    assert history[0]["content"] == "msg-5"  # oldest kept


def test_clear_user(store):
    store.add_user_message("u1", "hello", "ch")
    store.add_user_message("u2", "hello", "ch")
    store.clear("u1", "ch")
    assert len(store.get_history("u1", "ch")) == 0
    assert len(store.get_history("u2", "ch")) == 1


def test_clear_all(store):
    store.add_user_message("u1", "a")
    store.add_user_message("u2", "b")
    store.clear_all()
    assert store.stats()["conversations"] == 0


def test_stats(store):
    store.add_user_message("u1", "a", "ch1")
    store.add_user_message("u1", "b", "ch1")
    store.add_user_message("u2", "c", "ch2")
    stats = store.stats()
    assert stats["conversations"] == 2
    assert stats["total_messages"] == 3


def test_empty_history_returns_list(store):
    history = store.get_history("nobody", "nowhere")
    assert history == []
    assert isinstance(history, list)
