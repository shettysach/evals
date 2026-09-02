# Task: Solve the Sokoban Board

You control the blue circular player in a small grid-based Sokoban puzzle. The
player must push every brown box onto a green goal square.

## Visual legend

* **Blue circle:** the player.
* **Brown square:** a movable box. It nearly fills its grid cell.
* **Green square:** a goal. It fills the entire grid cell; a box may cover it.
* **Dark outlined squares:** empty traversable floor.
* **Dark solid squares:** walls and board boundary. They cannot be crossed.

## Movement rules

Use `move` with exactly one of `left`, `right`, `up`, or `down`. A move takes
the player one grid square in that direction.

The player may walk onto empty floor and green goals. If the player moves into
a box, it pushes that box one square only when the square beyond the box is
empty floor or a green goal. Boxes cannot be pulled. A move into a wall, or a
box that cannot be pushed, has no effect.

Plan before pushing: a box pushed against a wall or into a corner that is not a
goal may become permanently stuck. Work on one box at a time when that avoids
blocking access to the others. The task succeeds only when every box is on a
green goal.

## Response policy

Use the provided `sokoban_action` tool for every response. Choose one safe,
deliberate action from the current image. Do not describe an action in ordinary
text. Call `reset` only if the board is irrecoverably deadlocked or the episode
needs to start over; do not reset merely because progress is slow.
