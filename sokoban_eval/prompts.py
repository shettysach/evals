from pathlib import Path


SYSTEM_PROMPT = Path(__file__).with_name("prompts").joinpath("SYSTEM.md").read_text(
    encoding="utf-8"
)

USER_PROMPT = "Analyze the current Sokoban board image and choose the next action."
