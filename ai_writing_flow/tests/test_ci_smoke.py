import os
import pytest
from pathlib import Path

# Ensure CI fast-path is active
os.environ.setdefault("CI", "true")

# Import after setting env
from ai_writing_flow.ai_writing_flow_v2 import AIWritingFlowV2


def test_ci_smoke_fast_path(tmp_path):
    flow = AIWritingFlowV2(
        monitoring_enabled=True,
        alerting_enabled=False,
        quality_gates_enabled=False,
        storage_path=str(tmp_path / "metrics")
    )

    inputs = {
        "topic_title": "CI Smoke",
        "platform": "LinkedIn",
        "file_path": str(tmp_path / "content.md"),
        "content_type": "STANDALONE",
        "content_ownership": "ORIGINAL",
        "viral_score": 5.0,
    }

    # Create the file to avoid FS validation noise
    Path(inputs["file_path"]).parent.mkdir(parents=True, exist_ok=True)
    Path(inputs["file_path"]).write_text("# smoke\n", encoding="utf-8")

    state = flow.kickoff(inputs)

    assert getattr(state, "current_stage", None) in {"completed", "finalized", "topic_received"}
    assert getattr(state, "topic_title", "") == "CI Smoke"
