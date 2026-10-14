# Contributing

Corrections, new components, clearer explanations and better source evidence are
welcome. You do not need to prove a new theorem to make a useful contribution.
Browse the [directory](generated/DIRECTORY.md) and search existing IDs first.

## Prepare a contribution

Fork the repository, create a branch and open a pull request. Include the affected
IDs, what changes, the exact argument or formal revision, unresolved prerequisites,
source and licence pointers, and your local validation results. Maintainers may
make direct updates under the same evidence and validation requirements.

Add new components to `components.jsonl`; put field corrections and evidenced
relations in `annotations.json`. Use the templates for formal components. Keep
stable IDs and preserve failed, withdrawn and dormant variants; link corrections
and supersessions instead of removing their history. Source occurrence identity
does not establish mathematical equivalence.

State assumptions and quantifiers precisely. Preserve coefficients, signs, masks,
natural zeros, exceptional terms, independent heights and input contracts. Keep
proved statements, conditional implications and open estimates distinct. When
correcting wording or provenance, do not silently strengthen a mathematical claim.

## Check locally

```sh
python catalogue.py validate-contribution --root .
python catalogue.py refresh --root .
python catalogue.py validate --catalogue generated
```

Commit the maintained inputs and their regenerated outputs. Do not edit generated
pages or shards directly. Templates and fixtures are excluded from catalogue
inputs. Review affected queries and links as well as validation output.

These checks establish data consistency, not mathematical correctness. Reviewers
use trusted tools and will not execute contributor scripts as proof evidence.
Do not add GitHub Actions workflows or hosted/self-hosted runner jobs. Upstream
CI receipts are welcome as evidence tied to their actual source revision.

## Supply useful evidence

Prefer publicly accessible, immutable source links with exact locators and
attribution. If evidence cannot be shared, label that limitation honestly and
preserve a provenance hash; a hash is not a substitute for reviewable proof.
Do not include credentials, operational logs, host paths, task/session IDs or
material you lack permission to redistribute.

Formal contributions need exact repository/revision/path, fully qualified names,
package requirements and toolchain versions. Separate reported checks from actual
typechecking, axiom auditing and kernel verification. Each claimed stage needs a
receipt bound to that same revision; signatures and imports alone are textual
evidence.

Cite entries in papers and submissions with their stable IDs and pinned catalogue
permalinks, preserving original-paper attribution. Add reciprocal public-artifact
links only when a public version and exact section, theorem or declaration support
them. Distinguish textual occurrence, mention, documented use and claimed use.

Paper/record-to-Lean use links require both an actually published paper or submitted
record and full end-to-end formalization of the corresponding proof. Supply exact
versions, complete verification evidence and the components actually used. A
submitted record may await review. Drafts, intended submissions, partial proofs
and isolated helpers do not qualify, even under a weaker use-link label. Keep
source-location and import provenance separate. Reusable Lean components can be
contributed independently of a qualifying publication link.

## Keep your branch current

Inspect local changes and fetched updates before integrating:

```sh
git status --short
git fetch origin
git log --oneline HEAD..origin/main
```

For a clean, nondiverged branch, use `git pull --ff-only`. Otherwise preserve your
work and resolve the integration deliberately; do not reset or force-update it.
Sync before relying on changed records and before submitting. Repositories that
consume this catalogue as a submodule manage their own revision pins separately.

## Licensing

Submit original tool changes under MIT and original descriptions and metadata
under CC BY 4.0. Identify third-party material and its actual terms, preserve
notices, and ensure you have authority to contribute it. These licences do not
relicense imported sources or claim ownership of mathematical facts. See
[Licensing and attribution](LICENSING.md).
