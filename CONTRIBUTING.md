# Contributing

Browse the directory and search existing IDs before adding a component. Keep failed, withdrawn and dormant variants available; link corrections rather than deleting their history. Source occurrence identity and semantic equivalence have separate evidence requirements. Preserve coefficients, masks, natural zeros, exceptional terms, independent heights, input contracts and quantifier order.

External contributors: fork the public repository, create a branch and submit a pull request with the changed mathematical records, public source/license pointers and evidence. For Hailey's owner-directed maintenance, direct commits and ordinary pushes to `main` are authorized now and for future synchronization; no PR is required. Apply the same evidence, review and local validation requirements, and never force-push. Include the affected IDs, the exact argument or formal revision, unresolved prerequisites and the local validation result. New components belong in `components.jsonl`; maintained annotations and links belong in `annotations.json`. Rebuild with `python catalogue.py refresh --root .` and validate with the commands in README. Templates/fixtures are outside catalogue inputs. Do not supply contributor scripts as proof-review evidence or expect reviewers to execute them.

Use local workers for validation/review. Do not add active `.github/workflows` runner jobs or any GitHub Actions/self-hosted-runner orchestration. GitHub repository/PR APIs and the local watcher/CLI suffice. Preserve legitimate upstream CI evidence links without treating them as authority to run hosted jobs here.

Formal contributions must identify exact public repository/ref/path, fully qualified names, module/package requirements and toolchain versions. Separate reported checks from actual typechecking, axiom auditing and kernel checks. Supply revision-bound receipts for each claimed stage. Source signatures and imports alone remain textual evidence. Mathematical/proof review is distinct from data-validation success.

Link catalogue entries in papers and submissions using their stable IDs and exact catalogue commit/tag-pinned permalinks. Keep original-paper attribution. Add reciprocal public paper/submission and use links only when a public version and exact section/theorem/declaration support them. Record mere mention, documented use and claimed-but-unverified use separately; a catalogue link is not proof verification.

Check for upstream updates before starting work and before publishing a direct update or pull request:

```powershell
git status --short
git fetch origin
git log --oneline HEAD..origin/main
```

Inspect the fetched changes. If your checkout is clean and no local commits diverge, `git pull --ff-only` updates it safely. If dirty or diverged, preserve your work and resolve the integration explicitly; do not reset, force-update or automatically rebase it. Adapt `main` to the repository's actual default branch.

When using this repository as QRH's `catalogue/` submodule, `git submodule update --init catalogue` checks out the parent repository's recorded pin. Fetching a newer public catalogue does not silently change that pin. Advancing it requires review, a deliberate checkout of the desired catalogue revision and a parent commit of the submodule pointer. Preserve local submodule changes; no destructive checkout/reset/rebase is part of routine upkeep. The private QRH repository remains private.

Do not submit private operational data, absolute host paths, task/session IDs, credentials, fetch logs or unlicensed upstream proof bodies. Restricted mathematical pointers must be labelled restricted, with source hashes/provenance preserved. Public mathematical statements and assumptions must remain intact; a privacy edit must not quietly strengthen a theorem.

Submit original tool contributions under MIT and original descriptions/metadata under CC BY4.0. Identify and preserve all third-party terms and attribution; these contribution licences do not relicense imported proof/text or claim ownership of mathematical facts. Read [LICENSING.md](LICENSING.md).
