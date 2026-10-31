# Dataset provenance and exact symmetry contract

## Pinned source

- Repository: https://huggingface.co/datasets/lewismoten/tic-tac-toe
- Revision: `6ea253e1fa7de4a61eedeab6bbd9d8117af1fcb7`
- Manifest SHA-256: `0258d03ac9a2fd5bbf590736f9758d982d5f179e7415a4ca771418b22b1f2777`
- Primary history SHA-256: `a4539c7cde214440f3369085725ad32faaba03d5de3265c6a8333bdc12723597`
- License: Apache-2.0. Downloaded source README, LICENSE and generator have separately pinned digests.

`python scripts/prepare_dataset.py` obtains missing files at this immutable revision, verifies all five JSONL digests/counts and the upstream manifest, and audits all primary rows. It does not overwrite a changed local file silently. Use `--offline` to forbid downloads.

## Completed audit

All **294,778** unique nonterminal histories passed protocol validation: square alphabet, chronology, no repeated squares, no continuation after terminal play, derived board and next player, readable board rendering, and exact deterministic/all-optimal labels from an independently implemented minimax audit oracle.

Those histories correspond to **4,520** nonterminal boards. There are **zero board-label conflicts**: the same board has the same deterministic target regardless of the chronology that reached it. This justifies a board-state-dependent neural candidate, while preserving a raw-history input validator. It does not prove an arbitrary chronological model is board-dependent.

Tie order is `ebdfhcgia`. The oracle lives in dataset tooling and must not be imported into deployed neural inference. The eventual policy must come from the trained network's executed outputs, with legal masking and documented tie resolution.

See `results/dataset-audit.json` for exact history-length counts and digests.

## Symmetry audit and a rejected shortcut

`python scripts/audit_symmetry.py` checks every nonterminal board using explicit original-to-transformed permutations and inverse move mappings.

- The **4,520 nonterminal boards** reduce to **627 dihedral-canonical nonterminal boards**.
- This is distinct from the dataset's **765 canonical reachable boards**, which also include terminal positions.
- Predicting the complete canonical optimal-move set, inverse-mapping it, then applying the original-coordinate tie order reproduces all deterministic targets: **zero mismatches**.
- Picking only the first canonical target and inverse-mapping that single move fails **406 boards**. These are exact behavior failures, not numerical-logit differences.

A centered first move gives a simple conceptual counterexample: the board is unchanged by rotation, but the selected corner is not. Therefore fixed deterministic original-coordinate tie preference cannot simply be assumed rotation-equivariant.

An Approach-C neural model must predict the optimal set from its weights. The transformation wrapper does not compute optimality, repair incorrect predicted sets, or contain a stored policy. All-set equality and deterministic-move equality need separate evaluation, and no such learned model is accepted by this audit alone.

Canonicalization here is an explicit preprocessing/coordinate wrapper, not a claim that the original model contains learned flip/rotation layers. Board-state representation, chronological representation and symmetry-aware set prediction remain separately named candidates.
