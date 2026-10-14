# QRH Catalogue

A collaborative catalogue of mathematics and formal components for research on
the quasi-Riemann hypothesis. Browse results, open estimates, useful identities,
conditional reductions, obstructions and earlier approaches—or contribute a
missing component, a correction or a better source reference.

Start with the [linked directory](generated/DIRECTORY.md), search with the CLI,
or read [Contributing](CONTRIBUTING.md). Python's standard library is sufficient;
the committed catalogue contains everything needed to browse, query, contribute
and run its data validators.

## Find and reuse a component

```sh
python catalogue.py query cofactor --topic mobius --status open
python catalogue.py query --kind lemma --tag pr:26 --formalization textual
python catalogue.py query c11 --conditional --source-relative
python catalogue.py show --id G227
python catalogue.py traverse --id G227 --direction both --depth 1
```

Text terms and repeated topic, method, object, tag and status filters are ANDed;
repeated kind and origin filters are ORed. Use `--review` and `--formalization`
for their separate evidence fields, or `--json --limit 100` for query JSON.
`show` accepts stable IDs and unambiguous aliases. `traverse` follows evidenced
relations; an empty dependency list means no dependency has been recorded.

Follow each component's exact source, assumptions, quantifier order and evidence
before using it. Mathematical status, independent review and formal verification
are separate. A source declaration, import, scalar check or catalogue validation
does not establish a theorem. Source-reported verification stays labelled as such.
If source material is unavailable publicly, its provenance hash records identity,
not independent verification or permission to redistribute it.

**Current qualification:** c11 = 312864909/2500000000 = .1251459636 is a
conditional source-relative benchmark. PR15's author reports that its stronger
weighted source estimate and complete endpoint remain unfinished.

## Contribute

Contributions can add mathematical or Lean components, clarify a statement,
document an unresolved assumption, improve attribution, supply revision-bound
verification evidence, or connect existing components with an evidenced relation.
Search first, then follow the [contribution guide](CONTRIBUTING.md).

- Add records to `components.jsonl` with a unique stable ID, a title, a kind,
  precise mathematical content, source pointers and evidence.
- Put maintained field corrections and evidenced relations in `annotations.json`.
  Preserve earlier evidence and explain what a correction supersedes.
- Use the [formal component template](templates/formal-component.json) for Lean
  modules, declarations and other reusable formal components.
- Keep failed, withdrawn and dormant variants discoverable. Their exact failure
  scope can be useful to the next contributor.

```sh
python catalogue.py validate-contribution --root .
python catalogue.py refresh --root .
python catalogue.py validate --catalogue generated
```

Run these checks locally and include the results in your pull request. Validation
checks data and links without fetching external sources; it is not proof review.
This repository does not run GitHub Actions or runner jobs. Existing upstream CI
receipts may still be cited as source evidence.

## Record structure

Records use schema version 1. Unknown information remains unknown.

| Fields | Purpose |
|---|---|
| `id`, `aliases`, `identity_kind`, `semantic_component_id` | Stable identity; distinguish source occurrences from mathematical equivalence. |
| `title`, `kind`, `origin`, `author`, `source_revision` | Description, collection and source attribution. |
| `statement`, `hypotheses`, `quantifier_scope`, `quantitative_targets`, `quantitative_returns` | Exact mathematical content and scope. |
| `mathematical_status`, `review_status`, `formalization_status` | Separate claims and evidence for each stage. |
| `status_labels`, `conditional`, `source_relative` | Discovery labels with their evidence basis. |
| `topics`, `methods`, `objects`, `tags` | Navigation facets; inferred tags do not prove applicability. |
| `pointers`, `source_record`, `raw_source_record`, `source_terms` | Source locations, provenance, attribution and licensing. |
| `relations`, `unresolved_prerequisites`, `evidence` | Evidenced links, remaining obligations and field provenance. |
| `formal_component`, `public_artifact` | Formal metadata and public paper or submission metadata. |

The imported baseline is in `base-data/*.jsonl` and `base-coverage.json`.
Contributions and annotations are maintained separately. Files under `generated/`
are reproducible outputs: do not edit them by hand. Data shards stay below 16 MiB;
the search index uses byte offsets for exact lookups. Coverage counts represent
source occurrences, not numbers of new or proved theorems.

Use `related` or `mentions` for an association; `depends_on`, `formalizes`,
`implements` and `supersedes` require evidence for that stronger relationship.
For example, a supersession annotation has `source`, `target`, `kind` and
`evidence` fields; refresh adds the inverse `superseded_by` link.

## Formal components and published use

For a formal component, supply the exact repository, revision and path; fully
qualified declaration name and namespace; toolchain and package versions;
imports, statement, licence and relevant mathematical links. Keep reported,
typechecked, axioms-audited and kernel-checked evidence distinct and bound to the
same revision. Textual imports use `imports`, not a presumed proof dependency.

Public papers and record submissions can have `public-paper` or
`public-submission` records with `public_artifact` metadata: kind, URL, version,
status and an exact section, theorem or declaration locator. Distinguish mention
from documented use and claimed use. Textual source-location links alone do not
establish derivation or reuse.

Paper/record-to-Lean use links require both an actually published paper or
submitted record and a complete end-to-end formalization of its corresponding
proof. Cite the exact versions and components actually used. Submission acceptance
is not required. Drafts, planned submissions, partial formalizations and isolated
helpers do not qualify, including under a weaker use-link label. Formalization
contributors should supply the final-use evidence; maintainers review the links.
Lean components can be contributed and reused before such a link qualifies.

To cite a catalogue entry, use its stable ID and commit- or tag-pinned permalink,
using the `page` and anchor returned by a query. Preserve the original source and
author citation. A catalogue citation provides navigation and provenance, not
proof certification.

Original tool contributions use MIT and original descriptions and metadata use
CC BY 4.0. Third-party material retains its terms and attribution; see
[Licensing and attribution](LICENSING.md).
