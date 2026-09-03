from __future__ import annotations

import argparse
import os
from io import BytesIO

import pygame

from sokoban_eval.env import LEVELS, SokobanEnv
from sokoban_eval.vlm import OAIChatClient

CELL_SIZE = 88
HEADER_HEIGHT = 74
WINDOW_SIZE = (SokobanEnv.width * CELL_SIZE, SokobanEnv.height * CELL_SIZE + HEADER_HEIGHT)
DEFAULT_VLM_URL = "http://127.0.0.1:8080"


class GameApp:
    def __init__(
        self,
        client: OAIChatClient | None,
        *,
        level: int = 1,
    ) -> None:
        pygame.init()
        pygame.display.set_caption("2D Sokoban VLM Eval")
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.font = pygame.font.Font(None, 25)
        self.small_font = pygame.font.Font(None, 20)
        self.clock = pygame.time.Clock()
        self.env = SokobanEnv(level)
        self.client = client
        self.vlm_turns = 0
        self.last_action: str | None = None
        self.status = "Arrows: play · 1–10: level · Space: ask VLM · R: reset"

    def run(self) -> None:
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self._handle_key(event.key)
            if self.client is not None and not self.env.completed:
                self._ask_vlm()
            self.draw()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()

    def _handle_key(self, key: int) -> bool:
        if key == pygame.K_ESCAPE:
            return False
        directions = {
            pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
            pygame.K_UP: "up", pygame.K_DOWN: "down",
        }
        if key in directions:
            self._apply_move(directions[key])
        elif key == pygame.K_r:
            self.env.reset()
            self.last_action = "reset"
            self.status = "Environment reset."
        elif key == pygame.K_SPACE:
            self._ask_vlm()
        elif pygame.K_1 <= key <= pygame.K_9:
            self._select_level(key - pygame.K_0)
        elif key == pygame.K_0:
            self._select_level(10)
        return True

    def _select_level(self, number: int) -> None:
        self.env.select_level(number)
        self.last_action = None
        level = self.env.level
        self.status = f"Level {level.number}: {level.name} ({level.difficulty})"

    def _apply_move(self, direction: str) -> None:
        result = self.env.move(direction)
        self.last_action = result.action
        if result.completed:
            self.status = f"Solved in {self.env.steps} moves! Press R to run again."
        elif result.moved:
            self.status = f"{result.action}{' — box pushed' if result.pushed else ''}"
        else:
            self.status = f"{result.action} blocked"

    def _ask_vlm(self) -> None:
        if self.client is None:
            self.status = "Set VLM_URL to enable VLM actions."
            return
        self.status = "Requesting VLM action…"
        self.vlm_turns += 1
        print(f"VLM request {self.vlm_turns}", flush=True)
        self.draw()
        pygame.display.flip()
        try:
            completion = self.client.complete(self.board_png(), self.last_action)
            action = completion.action
            print(f"VLM action: {action.label()}", flush=True)
            if action.action == "reset":
                self.env.reset()
                self.last_action = action.label()
                self.status = "VLM: reset"
            else:
                self._apply_move(action.direction or "")
                self.status = "VLM: " + self.status
            self.client.commit(completion)
        except Exception as exc:
            self.client = None
            print(f"VLM error: {type(exc).__name__}: {exc}", flush=True)
            self.status = f"VLM error: {type(exc).__name__}: {exc}"

    def board_png(self) -> bytes:
        board = pygame.Surface((SokobanEnv.width * CELL_SIZE, SokobanEnv.height * CELL_SIZE))
        self._draw_board(board, origin_y=0)
        stream = BytesIO()
        pygame.image.save(board, stream, "board.png")
        return stream.getvalue()

    def draw(self) -> None:
        self.screen.fill((23, 29, 39))
        self._draw_board(self.screen, origin_y=HEADER_HEIGHT)
        level = self.env.level
        title = self.font.render(
            f"SOKOBAN · {level.number}/10 · {level.name} ({level.difficulty})",
            True,
            (238, 242, 255),
        )
        status = self.small_font.render(self.status, True, (193, 204, 224))
        self.screen.blit(title, (14, 10))
        self.screen.blit(status, (14, 42))

    def _draw_board(self, surface: pygame.Surface, *, origin_y: int) -> None:
        for y in range(SokobanEnv.height):
            for x in range(SokobanEnv.width):
                rect = pygame.Rect(x * CELL_SIZE, origin_y + y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if (x, y) in self.env.walls:
                    pygame.draw.rect(surface, (48, 55, 67), rect)
                    pygame.draw.rect(surface, (31, 36, 46), rect, 3)
                else:
                    pygame.draw.rect(surface, (224, 230, 237), rect)
                    pygame.draw.rect(surface, (175, 185, 198), rect, 1)
                    if (x, y) in self.env.goals:
                        pygame.draw.rect(surface, (72, 184, 105), rect)
        inset = round(CELL_SIZE * 0.05)
        for x, y in self.env.boxes:
            rect = pygame.Rect(x * CELL_SIZE + inset, origin_y + y * CELL_SIZE + inset,
                               CELL_SIZE - 2 * inset, CELL_SIZE - 2 * inset)
            pygame.draw.rect(surface, (142, 88, 51), rect, border_radius=5)
            pygame.draw.rect(surface, (94, 54, 33), rect, 3, border_radius=5)
        px, py = self.env.player
        center = (px * CELL_SIZE + CELL_SIZE // 2, origin_y + py * CELL_SIZE + CELL_SIZE // 2)
        pygame.draw.circle(surface, (43, 121, 220), center, round(CELL_SIZE * 0.45))
        pygame.draw.circle(surface, (22, 72, 143), center, round(CELL_SIZE * 0.45), 3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visual 2D Sokoban VLM evaluation")
    parser.add_argument("--vlm-url", default=DEFAULT_VLM_URL)
    parser.add_argument("--model", default=os.getenv("VLM_MODEL", ""))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("VLM_TIMEOUT", "120")))
    parser.add_argument("--puzzle", type=int, choices=range(1, len(LEVELS) + 1), default=1)
    parser.add_argument("--single-player", action="store_true", help="Disable VLM requests; use arrow keys to play.")
    parser.add_argument(
        "--history",
        type=int,
        default=0,
        help="Number of completed VLM turns to replay (default: 0).",
    )
    args = parser.parse_args()
    if args.history < 0:
        parser.error("--history must be non-negative")
    client = None if args.single_player else OAIChatClient(
        args.vlm_url,
        timeout=args.timeout,
        model=args.model,
        history_turns=args.history,
    )
    GameApp(client, level=args.puzzle).run()
