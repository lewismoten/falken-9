# Study016 reproduction

This is offline source/evidence, not a runnable C64 release. No model packet or runtime binary is included in the ZIP.

## Inputs

Supply the accepted 5195-byte packet separately at:

`artifacts/flexible-integer/q11-w16-a32-early-interp/model.f9j`

SHA256: `fe180f8a931f9d92d8aa39da337bc819d0dbe4e6d971edcba00324fbc18a91c1`.

Use an existing CPU Python with torch, numpy and Pillow. Study016 used `/home/ai/falken-9/.venv/bin/python`; no installs or GPU were used. Matplotlib was unavailable, so the final renderer uses Pillow and writes matching explicit SVG elements without installing dependencies. This did not change the frozen panel or any outcome.

From the extracted study root (set `PY` to your interpreter):

```sh
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD"
PY=/home/ai/falken-9/.venv/bin/python
"$PY" study016.py fresh-results016
"$PY" audit016.py fresh-results016 > fresh-results016/independent-audit016.json
"$PY" render016.py fresh-results016
```

`fresh-results016` must not already exist. All data and visual artifacts should match the bundled `results016`, except that `results016.json` records actual absolute import locations and necessarily changes after relocation. The packet is never recovered from a sibling checkout by these scripts.

Tests: `"$PY" -m unittest test_study016 -v`. Integration tests intentionally perform a fresh binding; branch enumeration never counts as neural execution. Tests use the Hermes scratch directory `/home/ai/.hermes/cache/scratch` in this environment. They need the separately supplied packet and included `results016` fixtures.

`finish016.py` is the original local finalization controller: its preservation checks intentionally refer to the original absolute read-only roots and it expects an unused `reproduced016` / `bundle-smoke016`. Use the three portable analysis commands above after extraction, rather than expecting original-machine preservation inventories to apply elsewhere.

## Guarantees and exclusions

- Exactly three fixed policies and two player roles; no added policy search.
- Real whole-network binding covers 627 canonical boards once each per analysis run; full raw restoration covers 4520 nonterminal boards.
- Independent scalar packet/forward/minimax audit, independent bottom-up rational DP, plus explicit adversarial complete-history enumeration.
- Complete stages, raw sets and logits, per-state DAG values, route counts, exact outcome probabilities and two annotated PNG/SVG pairs.
- All-domain training/audit exposure is acknowledged: no new model-heldout claim.
- Prior studies and accepted protected main files are preserved; mutable parent-owned docs excluded.
- No cache, counterfactual policy or solver is installed in deployed runtime.
- No training, native edits, exports, publication, service, installs, GPU or further study.

Start with `results016/REPORT016.md`; consult root `verification016.json` for completed local verification and bundle SHA256.
