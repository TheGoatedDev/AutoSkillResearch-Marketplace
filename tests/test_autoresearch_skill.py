from pathlib import Path


def test_discard_path_updates_elo_state():
    skill_path = Path(".claude/skills/autoresearch/SKILL.md")
    content = skill_path.read_text()

    discard_block_start = content.index("If **discard**:")
    discard_block_end = content.index("**8. Check Exit Conditions**")
    discard_block = content[discard_block_start:discard_block_end]

    assert "python3 scripts/elo.py update" in discard_block
    assert "--result discard" in discard_block
