"""Print the per-corpus distribution as Markdown tables (used to refresh README.md).

uv run tools/stats.py
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from contract import Case, Corpus

ROOT = Path(__file__).resolve().parents[1]


def row(counter: Counter[str], keys: list[str]) -> str:
    return " | ".join(str(counter.get(key, 0)) for key in keys)


def main() -> None:
    corpora = sorted(p for p in (ROOT / "corpora").iterdir() if (p / "corpus.json").is_file())
    print("| Corpus | Created | Default | Cases | Clean | Issues | Location | Severity | Licence |")
    print("| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |")
    loaded = {}
    for path in corpora:
        corpus = Corpus.model_validate_json((path / "corpus.json").read_text())
        cases = [
            Case.model_validate_json(p.read_text()) for p in sorted((path / "cases").glob("*.json"))
        ]
        loaded[corpus.name] = cases
        issues = sum(len(case.expected_issues) for case in cases)
        clean = sum(case.kind.value == "clean" for case in cases)
        print(
            f"| `{corpus.name}` | {corpus.created_at} | {'yes' if corpus.default else 'no'} | "
            f"{len(cases)} | {clean} | {issues} | {corpus.location_precision.value} | "
            f"{'yes' if corpus.severity_available else 'no'} | {corpus.licence} |"
        )
    for name, cases in loaded.items():
        languages = Counter(case.language.value for case in cases)
        sizes = Counter(case.size.value for case in cases)
        kinds = Counter(case.kind.value for case in cases)
        tiers = Counter(case.tier.value if case.tier else "none" for case in cases)
        issues = [issue for case in cases for issue in case.expected_issues]
        categories = Counter(issue.category.value for issue in issues)
        severities = Counter(issue.severity.value if issue.severity else "null" for issue in issues)
        print(f"\n### `{name}`\n")
        print("| Dimension | Distribution |")
        print("| --- | --- |")
        for label, counter in (
            ("language", languages),
            ("size", sizes),
            ("kind", kinds),
            ("tier", tiers),
            ("category", categories),
            ("severity", severities),
        ):
            print(f"| {label} | " + ", ".join(f"{k} {v}" for k, v in counter.most_common()) + " |")


if __name__ == "__main__":
    main()
