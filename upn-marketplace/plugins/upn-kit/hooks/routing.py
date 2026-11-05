"""PreToolUse on Agent / Task: sets the model for helper agents from model-routing.json.

A model the person or Claude asked for by name always wins; this only fills the gap. Reads hooks/model-routing.json
("agents" table). The main window's own model is theirs to choose in Claude Code (/model); a hook cannot change it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402


def main():
    d = _lib.read_input()
    if d.get("tool_name") not in ("Agent", "Task"):
        return
    ti = dict(d.get("tool_input") or {})
    if ti.get("model"):
        return
    table = _lib.load_json(Path(__file__).resolve().parent / "model-routing.json", {}).get("agents", {})
    # the person's own override table, if they made one
    table.update(_lib.load_json(_lib.DATA / "model-routing.json", {}).get("agents", {}))
    row = table.get(ti.get("subagent_type") or "general-purpose")
    if not row or not row.get("model"):
        return
    ti["model"] = row["model"]
    _lib.emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow",
                                      "updatedInput": ti,
                                      "additionalContext": "ROUTING: %s runs on %s." % (ti.get("subagent_type") or "general-purpose", row["model"])}})


if __name__ == "__main__":
    _lib.run(main)
