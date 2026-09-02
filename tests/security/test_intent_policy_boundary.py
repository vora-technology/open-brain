from pathlib import Path


def test_policy_module_has_no_task_creation_dependency() -> None:
    source = (
        Path(__file__).parents[2]
        / "packages/engine/src/open_brain_engine/core/policy.py"
    ).read_text()
    prohibited = ("create_task", "upsert_task", "enqueue_task", "TaskStore", "task_id")
    assert all(token not in source for token in prohibited)
