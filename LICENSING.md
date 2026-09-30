# Licensing

Licences apply by content, as described below. They are not alternative licences for the
entire repository.

## Project software — Apache-2.0

The project's own tools, scripts, tests and software configuration remain licensed under the
Apache License 2.0. The full text is in [LICENSE](LICENSE).

## Original annotations and documentation — CC BY 4.0

The bdf-review project's original contributions to the following content are licensed under
the Creative Commons Attribution 4.0 International licence (SPDX: `CC-BY-4.0`):

- Original annotations in `corpora/curated/`, including expected issues, curator notes,
  original false-positive explanations and original human judgments.
- `ANNOTATION_GUIDE.md`.
- Original project documentation, including `README.md`, `CHANGELOG.md`, this document and
  project-authored documentation in `corpora/`.

The full licence text is in [LICENSE-CC-BY-4.0](LICENSE-CC-BY-4.0).
When sharing this material or adaptations, credit the bdf-review project, link to
[mr-bench-review](https://github.com/Guillaume-Lombardo/mr-bench-review) and
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), and indicate any changes, as required
by the licence. Preserve any supplied attribution and notices.

This grant covers only original project contributions. It does not relicense upstream MR
titles or descriptions, quotations, code excerpts or other third-party material embedded in
annotations or documentation. Those retain their existing licences and attribution.

## Imported annotations and benchmark snapshots

Imported annotations retain their existing source licences:

- `corpora/review-bench/`: CC BY 4.0 annotations.
- `corpora/aacr/`: Apache-2.0 annotations.
- `corpora/martian-offline/`: MIT golden comments.

See each corpus's `SOURCE.md` and `corpus.json` for provenance and licensing information.
The documentation licence above does not override these imported-content licences.

All upstream code and documentation in `bench/*` branches retain their existing licences,
including component-specific licences. Consult the licence files and notices within each
snapshot and the case's `origin.license` metadata. Neither this project's Apache-2.0 licence
nor its CC BY 4.0 grant replaces those licences.

## Previously distributed versions

This update does not revoke Apache-2.0 rights already granted for previously distributed
versions of the project's original annotations and documentation.
