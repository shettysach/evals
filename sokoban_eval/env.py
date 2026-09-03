from __future__ import annotations

from dataclasses import dataclass

Position = tuple[int, int]
DIRECTIONS: dict[str, Position] = {
    "left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
}


@dataclass(frozen=True)
class Level:
    number: int
    name: str
    difficulty: str
    rows: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.rows) != 8 or any(len(row) != 8 for row in self.rows):
            raise ValueError("Each Sokoban level must be an 8×8 grid")
        if any(cell not in "# .$@" for row in self.rows for cell in row):
            raise ValueError("Level contains an unsupported tile")
        boxes = sum(row.count("$") for row in self.rows)
        if boxes not in {2, 3}:
            raise ValueError("Each level must contain two or three boxes")
        if sum(row.count(".") for row in self.rows) != boxes:
            raise ValueError("Each level must have one goal per box")
        if sum(row.count("@") for row in self.rows) != 1:
            raise ValueError("Each level must contain one player")


LEVELS = (
    Level(1, "First Pushes", "Easy", ("########", "# .    #", "# $    #", "#   @$.#", "#      #", "#      #", "#      #", "########")),
    Level(2, "Two Directions", "Easy", ("########", "# .    #", "# $    #", "#   $ .#", "#  @   #", "#      #", "#      #", "########")),
    Level(3, "Left Delivery", "Moderate", ("########", "# .    #", "# $    #", "#      #", "#.$@   #", "#      #", "#      #", "########")),
    Level(4, "Outside Goals", "Moderate", ("########", "#      #", "#. $ $.#", "#      #", "#   @  #", "#      #", "#      #", "########")),
    Level(5, "Top and Bottom", "Moderate", ("########", "# .#   #", "# $    #", "#      #", "#    $ #", "#   @  #", "#    . #", "########")),
    Level(6, "Wide Delivery", "Challenging", ("########", "#.     #", "#      #", "#      #", "# $  $.#", "#   @  #", "#      #", "########")),
    Level(7, "Three Lanes", "Challenging", ("########", "#.     #", "#     .#", "# $ $ $#", "#   @  #", "#      #", "#  .   #", "########")),
    Level(8, "Three Deliveries", "Challenging", ("########", "#.     #", "#      #", "#   $ .#", "# $  $ #", "#   @  #", "#  .   #", "########")),
    Level(9, "Crossing Paths", "Hard", ("########", "#.     #", "#      #", "#      #", "# $$ $.#", "#   @  #", "#  .   #", "########")),
    Level(10, "Final Arrangement", "Hard", ("########", "#.     #", "#   #  #", "# $ #$.#", "#  .$  #", "#   @  #", "#      #", "########")),
)


@dataclass(frozen=True)
class StepResult:
    action: str
    moved: bool
    pushed: bool
    completed: bool


class SokobanEnv:
    """A deterministic 8×8 Sokoban environment with ten fixed puzzle levels."""

    width = 8
    height = 8

    def __init__(self, level: int = 1) -> None:
        self.select_level(level)

    @property
    def level(self) -> Level:
        return LEVELS[self.level_index]

    @property
    def completed(self) -> bool:
        return self.boxes == self.goals

    def select_level(self, number: int) -> StepResult:
        if not 1 <= number <= len(LEVELS):
            raise ValueError(f"Level must be in 1..{len(LEVELS)}")
        self.level_index = number - 1
        self._load(self.level)
        return StepResult("reset", moved=True, pushed=False, completed=False)

    def reset(self) -> StepResult:
        self._load(self.level)
        return StepResult("reset", moved=True, pushed=False, completed=False)

    def _load(self, level: Level) -> None:
        self.walls: set[Position] = set()
        self.goals: set[Position] = set()
        self.boxes: set[Position] = set()
        for y, row in enumerate(level.rows):
            for x, cell in enumerate(row):
                if cell == "#": self.walls.add((x, y))
                elif cell == ".": self.goals.add((x, y))
                elif cell == "$": self.boxes.add((x, y))
                elif cell == "@": self.player = (x, y)
        self.steps = 0

    def move(self, direction: str) -> StepResult:
        if direction not in DIRECTIONS:
            raise ValueError(f"Unsupported direction: {direction}")
        dx, dy = DIRECTIONS[direction]
        next_player = (self.player[0] + dx, self.player[1] + dy)
        moved = pushed = False
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
                    moved = pushed = True
        self.steps += 1
        return StepResult(f"move({direction})", moved, pushed, self.completed)
