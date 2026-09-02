from __future__ import annotations

from dataclasses import dataclass

Position = tuple[int, int]
DIRECTIONS: dict[str, Position] = {
    "left": (-1, 0),
    "right": (1, 0),
    "up": (0, -1),
    "down": (0, 1),
}
BOARD_WIDTH = 8
BOARD_HEIGHT = 8


@dataclass(frozen=True)
class StepResult:
    action: str
    moved: bool
    pushed: bool
    completed: bool


class SokobanEnv:
    """Small deterministic 8×8 Sokoban board with a guaranteed simple layout."""

    width = BOARD_WIDTH
    height = BOARD_HEIGHT
    walls = frozenset(
        (x, y)
        for y in range(BOARD_HEIGHT)
        for x in range(BOARD_WIDTH)
        if x in {0, BOARD_WIDTH - 1} or y in {0, BOARD_HEIGHT - 1}
    )
    goals = frozenset({(2, 1), (5, 1)})
    initial_boxes = frozenset({(2, 3), (5, 3)})
    initial_player = (3, 4)

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> StepResult:
        self.boxes = set(self.initial_boxes)
        self.player = self.initial_player
        self.steps = 0
        return StepResult("reset", moved=True, pushed=False, completed=False)

    @property
    def completed(self) -> bool:
        return self.boxes == self.goals

    def move(self, direction: str) -> StepResult:
        if direction not in DIRECTIONS:
            raise ValueError(f"Unsupported direction: {direction}")
        dx, dy = DIRECTIONS[direction]
        next_player = (self.player[0] + dx, self.player[1] + dy)
        moved = False
        pushed = False
        if next_player not in self.walls:
            if next_player not in self.boxes:
                self.player = next_player
                moved = True
            else:
                beyond_box = (next_player[0] + dx, next_player[1] + dy)
                if beyond_box not in self.walls and beyond_box not in self.boxes:
                    self.boxes.remove(next_player)
                    self.boxes.add(beyond_box)
                    self.player = next_player
                    moved = True
                    pushed = True
        self.steps += 1
        return StepResult(f"move({direction})", moved, pushed, self.completed)
