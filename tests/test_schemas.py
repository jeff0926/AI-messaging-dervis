"""Tests for the data model schemas."""

from src.schemas import AgentPayload, Command, Notification, NotificationStatus


def test_command_creation():
    cmd = Command(
        user_id="user_123",
        source_channel="telegram",
        namespace="research_agent",
        action="run_autonomous_research",
        parameters={"query": "Quantum Computing"},
    )
    assert cmd.namespace == "research_agent"
    assert cmd.action == "run_autonomous_research"
    assert cmd.parameters["query"] == "Quantum Computing"
    assert cmd.command_id  # auto-generated


def test_agent_payload_from_command():
    cmd = Command(
        user_id="u1",
        source_channel="webhook",
        namespace="research_agent",
        action="summarize",
        parameters={"query": "test"},
        metadata={"chat_id": "999"},
    )
    payload = AgentPayload.from_command(cmd)
    assert payload.namespace == "research_agent"
    assert payload.action == "summarize"
    assert payload.payload == {"query": "test"}
    assert payload.context["user_id"] == "u1"
    assert payload.context["source_channel"] == "webhook"


def test_notification_serialization():
    notif = Notification(
        task_id="t1",
        command_id="c1",
        status=NotificationStatus.COMPLETED,
        target_channel="telegram",
        target_user_id="u1",
        message="Done!",
    )
    data = notif.model_dump(mode="json")
    assert data["status"] == "completed"
    assert data["message"] == "Done!"
