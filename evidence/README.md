# Evidence

`examples/` is the committed demonstration: one real model-driven discovery run and seven
replays, each a directory with the recorder's hash-chained `log.jsonl` and, where a run ended,
`result.json`. See [examples/README.md](examples/README.md) for what each one shows.

`runs/` is where every live run lands (`handrail replay --evidence`, `author`, `verify`,
`serve`). It is gitignored: runs can hold screenshots of whatever the application showed.
Secrets never reach either directory; the recorder masks every value registered as a secret
before it writes, and the examples were grepped for the demo password before committing.

To check a log has not been edited since it was written:

```bash
uv run python -c "from handrail.kernel.evidence import verify_chain; print(verify_chain(__import__('pathlib').Path('evidence/examples/1-replay-success/log.jsonl')))"
```
