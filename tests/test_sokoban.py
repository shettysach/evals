import json

import pytest

from sokoban_eval.env import SokobanEnv
from sokoban_eval.vlm import ACTION_TOOL, Action


def test_board_is_an_8_by_8_two_box_two_goal_puzzle() -> None:
    env = SokobanEnv()
    assert (env.width, env.height) == (8, 8)
    assert len(env.boxes) == len(env.goals) == 2


def test_box_pushes_only_into_open_cell() -> None:
    env = SokobanEnv()
    env.player = (2, 4)
    result = env.move("up")
    assert result.moved and result.pushed
    assert env.player == (2, 3)
    assert (2, 2) in env.boxes


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ('{"action":"move","direction":"left"}', "move(left)"),
        ('{"action":"reset"}', "reset"),
    ],
)
def test_tool_arguments_are_strict(arguments: str, expected: str) -> None:
    assert Action.from_arguments(arguments).label() == expected


@pytest.mark.parametrize(
    "arguments",
    [
        '{}',
        '{"action":"move"}',
        '{"action":"reset","direction":"up"}',
        '{"action":"move","direction":"diagonal"}',
        '{"action":"move","direction":"left","extra":true}',
    ],
)
def test_invalid_tool_arguments_are_rejected(arguments: str) -> None:
    with pytest.raises(ValueError):
        Action.from_arguments(arguments)


def test_schema_has_only_the_requested_actions_and_directions() -> None:
    properties = ACTION_TOOL["function"]["parameters"]["properties"]
    assert properties["action"]["enum"] == ["move", "reset"]
    assert properties["direction"]["enum"] == ["left", "right", "up", "down"]
