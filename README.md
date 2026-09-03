# 2D Sokoban VLM evaluation

An 8×8 visual Sokoban environment intended for tool-using VLM evaluations.
Each puzzle contains two or three brown boxes, matching full-cell green goals,
and a large blue player circle. It uses the same OpenAI-compatible
chat-completions/tool-call pattern as DSRF.

## Run

```bash
uv sync
uv run main.py
```

Keyboard controls:

- Arrow keys: manually move the player.
- The VLM automatically requests and executes actions until the puzzle is
  solved or the server reports an error.
- R: reset the episode.
- 1–9: load that puzzle; 0: load puzzle 10.
- Escape or close window: quit.

For manual testing without a VLM:

```bash
uv run main.py --single-player --puzzle 1
```


To enable VLM control, point `VLM_URL` at an OpenAI-compatible server:

```bash
VLM_URL=http://127.0.0.1:8080 uv run main.py
```

The client posts to `${VLM_URL}/v1/chat/completions`, with the board PNG as an
inline `data:image/png;base64,...` image and a forced `sokoban_action` tool
call. A blank `model` field is used for llama-server compatibility; override it
with `VLM_MODEL` when needed. `VLM_TIMEOUT` defaults to 120 seconds.

`main.py` defaults to `http://127.0.0.1:8080`; change it only when needed with
`--vlm-url`. Each VLM turn is requested with Space, so the rendered board and
every action remain easy to inspect. The full valid action history is replayed as
`assistant` tool calls followed by `tool` acknowledgements, matching DSRF's
conversation protocol.
