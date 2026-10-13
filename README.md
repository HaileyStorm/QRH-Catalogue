# QRH Catalogue

A unified mathematical catalogue for QRH research: established source-relative results, conditional transfers, open estimates, identities, obstructions, failed variants, dormant approaches and reusable formal components. Use the [linked directory](generated/DIRECTORY.md) to browse without a search query.

**c11=312864909/2500000000=.1251459636 is a conditional source-relative benchmark.** PR15's author reports that its stronger weighted source estimate and complete endpoint remain unfinished. A source declaration, successful scalar check, matching name, imported module or kernel-related label does not establish an unconditional theorem.

The catalogue is public and runs with Python's standard library. The private QRH research repository is an optional owner-side import source; access to it is unnecessary for browsing, querying, validating, adding records or maintaining annotations. Public primary sources have immutable links. Restricted QRH proof/review pointers are explicitly labelled and retain their source hashes. External sources are not fetched by validation.

Validation and review run on local workers only. GitHub provides repository/PR APIs, and a local watcher/CLI performs execution. Do not add active GitHub Actions workflows or GitHub-hosted/self-hosted-runner orchestration. Upstream CI evidence links can still be cited.

```powershell
python catalogue.py query cofactor --topic mobius --status open
python catalogue.py query --kind lemma --tag pr:26 --formalization textual
python catalogue.py query c11 --conditional --source-relative
python catalogue.py show --id G227
python catalogue.py show --id HIST-PR1-M01
python catalogue.py traverse --id F04.C --direction both --depth 1
python catalogue.py traverse --id G227 --relation mentions --direction in
python catalogue.py validate --catalogue generated
python catalogue.py validate-contribution --root .
```

Text terms are ANDed. Repeated tag/topic/method/object/status filters are ANDed; repeated kind/origin filters are ORed. `--review` and `--formalization` search their respective status fields. `--json --limit 100` returns machine-readable query output. `show` accepts exact record IDs and unambiguous aliases. `traverse` follows both directions by default; use `--relation depends_on`, `supersedes`, `superseded_by`, `formalizes` or `implements` after evidenced links have been contributed. Empty dependency/supersession results mean no evidenced link is recorded, not that an argument has no prerequisites.

The linked review facet groups unknown, source-reported and maintained evidence; inspect each record's exact review text and receipt. Its grouping does not establish independent acceptance. Formalization facets retain the separate recorded status. Dotted imported declaration names remain literal source names; a full namespace/name stays unknown until supported explicitly.

Records use schema version1:

| Fields | Meaning |
|---|---|
| id, aliases, identity_kind, semantic_component_id | Stable source occurrence and semantic/local component identity remain distinct. Exact source groups establish equal bytes/spans, not equivalent theorems. |
| title, kind, origin, author, source_revision | Mathematical unit, public collection/PR and credited source revision. Unknown values remain null. Internal cycles/usage live only in QRH's private overlay. |
| statement, hypotheses, quantifier_scope, quantitative_targets, quantitative_returns | Exact available mathematical content and its scope. Missing quantified contracts are not supplied by the importer. |
| mathematical_status, review_status, formalization_status | Separate source mathematics, review evidence and formalization evidence. Source-asserted proofs retain their original qualification. |
| status_labels, conditional, source_relative | Discovery labels; inferred wording labels carry an evidence basis. c11 qualification is explicit. |
| topics, methods, objects, tags | Stable navigation facets. Keyword-assigned facets are marked inferred and do not assert applicability. |
| pointers, source_record, raw_source_record, source_terms | Immutable public source or restricted proof/review reference; intake hash/row locator; public mathematical source-field projection; source-specific attribution and terms. |
| relations, unresolved_prerequisites, evidence | Directed evidenced links, explicit remaining obligations and field provenance. Mentions/imports/subject analogues are not proved dependencies. |
| formal_component | Reusable Lean metadata and exact-revision verification stages; see [formal contribution template](templates/formal-component.json). |
| public_artifact | Public paper/manuscript/record-submission identity, URL, version, captured status and exact source evidence. |

`base-data/*.jsonl` and `base-coverage.json` preserve the public projection of the owner intake. `components.jsonl` contains contributed records. `annotations.json` contains maintained field annotations and evidenced relations. `generated/data/*.jsonl`, `index.json`, browse pages and `coverage.json` are reproducible outputs. Record shards stay below16MiB for normal Git hosting. Do not hand-edit generated files. The search index stores byte offsets, so exact lookup reads one record. Full coverage receipts retain each inventory row's represented ID; counts are source/index occurrences, not counts of new or proved theorems.

Add a component to `components.jsonl` with a unique stable ID, title, kind, exact public source pointers and evidence. Use `templates/formal-component.json` for a reusable Lean module/declaration. Add field changes to `annotations.json` as `"record-id": {"field": {"value": ..., "evidence": ...}}`. A status change needs its exact argument/review receipt; preserve previous evidence in the source and explain supersession. Link a supersession with `{"source":"new-id","target":"old-id","kind":"supersedes","evidence":{...}}`; rebuilding adds the inverse `superseded_by`. Equivalent statements require actual equivalence evidence. A bare mention uses `mentions` or `related`.

```powershell
python catalogue.py validate-contribution --root .
python catalogue.py refresh --root .
python catalogue.py validate --catalogue generated
```

To add a formal component, record module/package/declaration/theorem/lemma/definition/instance/tactic kind as appropriate; exact repository/ref/path and fully qualified name/namespace; Lean/Mathlib/toolchain versions and imports/packages; public license/source notice; precise statement and mathematical component links. Keep source-reported, typechecked, axioms-audited and kernel-checked stages distinct. Every positive verification claim needs evidence bound to the same exact revision. Leave versions, checks and names unknown when unsupported. Add `formalizes`/`implements` links through annotations; `depends_on` requires a checked dependency argument, while textual imports use `imports`. The illustrative fixture is excluded from every real catalogue count. No formalization or kernel run was performed for this catalogue import.

For public papers and leaderboard/record submissions, add a `public-paper` or `public-submission` component with `public_artifact` fields: `artifact_kind`, `public_url`, `version`, `status`, and exact section/theorem/declaration evidence. Add component→artifact links as `documented_use`, `mentioned_in` or `claimed_use`, with evidence containing the public URL and exact `section`, `theorem`, `declaration`, `line_start` or `locator`. Both directions are available through `traverse`; artifact pages list recorded links. Initial `appears_in`/`contains_statement_occurrence` links establish textual source locations only. A module import or shared submission does not prove derivation reuse. Keep private cycle usage in the separate QRH usage/provenance overlay keyed by these public IDs.

Catalogue entries can and should be linked in papers/submissions. Cite the stable entry ID and an exact commit/tag-pinned permalink, for example `https://github.com/HaileyStorm/QRH-Catalogue/blob/<commit-or-tag>/generated/records/<page>.md#<entry-anchor>` using the entry's actual `page` from query output. Preserve the original-paper and author attribution. Add reciprocal public artifact/use records only with source evidence. A catalogue link alone does not verify a proof.

Owner-only private intake (not needed by contributors): `build --repo <private-QRH> --output <private-intake>` followed by `export-public --repo <private-QRH> --private-catalogue <private-intake> --output <public-generated> --private-receipt <private-receipt>`. Review the public-field projection. To explicitly install that projection as the standalone base, rerun the export with `--base-root <public-repository-root>`; without this option an export changes only the candidate generated output, and refresh still uses the previous base. Preserve annotations/components and refresh. Never publish the full private intake, operational logs or unlicensed proof bodies.

For contribution and safe updates, read [CONTRIBUTING.md](CONTRIBUTING.md). Our new tools use MIT and our original descriptions/metadata use CC BY4.0, copyright2026 Hailey Collet; see [licensing and attribution](LICENSING.md). Third-party material retains its original terms and credit. No copyright claim is made in bare mathematical facts.

## Keeping the catalogue current

During QRH research and formalization, query this catalogue before developing or reusing related arguments. Reconcile records when public reusable components, argument revisions, source intake, verification receipts, papers/submissions or status corrections become available. Maintain `components.jsonl` and `annotations.json`, regenerate, run both local validators, and inspect the affected queries and links. Preserve historical variants, exact source identities, attribution and unresolved obligations. Private source libraries remain separate; catalogue maintenance is not permission to publish them.

Hailey has authorized direct commits and ordinary pushes to `main` for owner-directed initial population and future synchronization. No catalogue PR is required for that work; external contributors follow CONTRIBUTING. Fetch and review upstream before editing and before publishing, preserve concurrent changes, and never force-push. Submodule parent pins, where used, require their own reviewed update. This maintenance workflow uses local validation and does not introduce scheduled polling or hosted jobs.
