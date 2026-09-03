import json
from collections import deque

import pytest

from sokoban_eval.env import LEVELS, SokobanEnv
from sokoban_eval.vlm import ACTION_TOOL, Action, OAIChatClient


def _minimum_pushes(env: SokobanEnv) -> int | None:
    """Push-based BFS: walking within a reachable region is free."""
    directions = ((-1, 0), (1, 0), (0, -1), (0, 1))

    def reachable(player: tuple[int, int], boxes: frozenset[tuple[int, int]]):
        cells = {player}
        pending = [player]
        while pending:
            x, y = pending.pop()
            for dx, dy in directions:
                next_cell = (x + dx, y + dy)
                if (
                    next_cell not in cells
                    and next_cell not in env.walls
                    and next_cell not in boxes
                ):
                    cells.add(next_cell)
                    pending.append(next_cell)
        return cells

    start_boxes = frozenset(env.boxes)
    pending = deque([(env.player, start_boxes, 0)])
    seen = {(env.player, start_boxes)}
    while pending:
        player, boxes, pushes = pending.popleft()
        if boxes == env.goals:
            return pushes
        walkable = reachable(player, boxes)
        for box_x, box_y in boxes:
            for dx, dy in directions:
                required_player = (box_x - dx, box_y - dy)
                destination = (box_x + dx, box_y + dy)
                if (
                    required_player not in walkable
                    or destination in env.walls
                    or destination in boxes
                ):
                    continue
                next_boxes = frozenset((boxes - {(box_x, box_y)}) | {destination})
                state = ((box_x, box_y), next_boxes)
                if state not in seen:
                    seen.add(state)
                    pending.append(((box_x, box_y), next_boxes, pushes + 1))
    return None


def test_levels_are_8_by_8_with_two_or_three_boxes_and_goals() -> None:
    assert len(LEVELS) == 10
    env = SokobanEnv()
    assert (env.width, env.height) == (8, 8)
    for level in LEVELS:
        env.select_level(level.number)
        assert len(env.boxes) == len(env.goals)
        assert 2 <= len(env.boxes) <= 3


def test_all_shipped_levels_are_solvable() -> None:
    for level in LEVELS:
        assert _minimum_pushes(SokobanEnv(level.number)) is not None, level.name


def test_box_pushes_only_into_open_cell() -> None:
    env = SokobanEnv()
    env.player = (2, 3)
    result = env.move("up")
    assert result.moved and result.pushed
    assert env.player == (2, 2)
    assert (2, 1) in env.boxes


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


def test_vlm_history_replays_prior_user_image_before_tool_acknowledgement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted: list[dict[str, object]] = []
    responses = iter((
        {"choices": [{"message": {"tool_calls": [{"id": "call_1", "function": {
            "name": "sokoban_action", "arguments": '{"action":"move","direction":"up"}',
        }}]}}]},
        {"choices": [{"message": {"tool_calls": [{"id": "call_2", "function": {
            "name": "sokoban_action", "arguments": '{"action":"move","direction":"right"}',
        }}]}}]},
    ))

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return json.dumps(next(responses)).encode()

    def urlopen(request, timeout):
        posted.append(json.loads(request.data))
        return Response()

    monkeypatch.setattr("sokoban_eval.vlm.urllib.request.urlopen", urlopen)
    client = OAIChatClient("http://example.test")
    first = client.complete(b"first", None)
    client.commit(first)
    client.complete(b"second", "move(up)")

    messages = posted[1]["messages"]
    assert [message["role"] for message in messages] == [
        "system", "user", "assistant", "tool", "user",
    ]
