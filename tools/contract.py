"""Dataset contract v1: corpus metadata and case files.

This module is the executable form of the contract described in README.md. The bdf-review
runner (T19) carries an identical copy; change both together and bump ``schema_version``.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1
SHA = r"^[0-9a-f]{40}$"
CORPUS_NAME = r"^[a-z0-9][a-z0-9-]*$"
CASE_ID = r"^[a-z0-9][a-z0-9-]*-[0-9]{3,}$"


class Strict(BaseModel):
    """Immutable model that rejects unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class Language(StrEnum):
    PYTHON = "python"
    JAVA = "java"
    TYPESCRIPT = "typescript"
    JAVASCRIPT = "javascript"
    GO = "go"
    RUBY = "ruby"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    CSHARP = "csharp"
    PHP = "php"
    OTHER = "other"


class Size(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class Kind(StrEnum):
    PLANTED = "planted"
    REVERTED_FIX = "reverted_fix"
    REAL = "real"
    CLEAN = "clean"


class Tier(StrEnum):
    PILOT = "pilot"
    CORE = "core"
    EXTENDED = "extended"


class Category(StrEnum):
    SECURITY = "security"
    CORRECTNESS = "correctness"
    MAINTAINABILITY = "maintainability"
    TESTS = "tests"


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class LocationPrecision(StrEnum):
    LINES = "lines"
    FILE = "file"
    NONE = "none"


class Annotation(StrEnum):
    HUMAN = "human"
    LLM = "llm"
    MIXED = "mixed"


def size_for(changed_lines: int) -> Size:
    """Size class of a change from its added plus deleted lines."""
    if changed_lines < 100:
        return Size.SMALL
    if changed_lines <= 600:
        return Size.MEDIUM
    return Size.LARGE


def _check_range(file: str | None, start: int | None, end: int | None) -> None:
    if file is None and (start is not None or end is not None):
        raise ValueError("lines require a file")
    if (start is None) != (end is None):
        raise ValueError("line_start and line_end are both set or both null")
    if start is not None and end is not None and end < start:
        raise ValueError("line_end must not precede line_start")


class Location(Strict):
    """Alternative place where the same issue may legitimately be reported."""

    file: str = Field(min_length=1)
    line_start: int | None = Field(default=None, gt=0)
    line_end: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def valid_range(self) -> Self:
        _check_range(self.file, self.line_start, self.line_end)
        return self


class ExpectedIssue(Strict):
    id: str = Field(pattern=r"^i[0-9]+$")
    file: str | None = Field(min_length=1)
    line_start: int | None = Field(gt=0)
    line_end: int | None = Field(gt=0)
    category: Category
    severity: Severity | None
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    outside_diff: bool
    alternative_locations: tuple[Location, ...]
    source_category: str | None
    source_text: str | None

    @model_validator(mode="after")
    def valid_range(self) -> Self:
        _check_range(self.file, self.line_start, self.line_end)
        return self

    @property
    def located(self) -> bool:
        return self.file is not None and self.line_start is not None


class KnownFalsePositive(Strict):
    file: str | None = Field(min_length=1)
    line_start: int | None = Field(gt=0)
    line_end: int | None = Field(gt=0)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_range(self) -> Self:
        _check_range(self.file, self.line_start, self.line_end)
        return self


class Origin(Strict):
    repository: str = Field(pattern=r"^https://")
    commit: str = Field(pattern=SHA)
    license: str = Field(min_length=1)
    source_case: str | None
    source_url: str | None


class Case(Strict):
    schema_version: Literal[1]
    corpus: str = Field(pattern=CORPUS_NAME)
    id: str = Field(pattern=CASE_ID)
    language: Language
    size: Size
    kind: Kind
    tier: Tier | None
    base_branch: str
    head_branch: str
    base_sha: str = Field(pattern=SHA)
    head_sha: str = Field(pattern=SHA)
    mr_title: str = Field(min_length=1)
    mr_description: str
    origin: Origin | None
    expected_issues: tuple[ExpectedIssue, ...]
    known_false_positives: tuple[KnownFalsePositive, ...] = ()
    annotator_notes: str

    @model_validator(mode="after")
    def consistent(self) -> Self:
        prefix = f"bench/{self.corpus}/{self.id}/"
        if self.base_branch != prefix + "base" or self.head_branch != prefix + "head":
            raise ValueError(f"branches must be {prefix}base and {prefix}head")
        if self.kind is Kind.CLEAN and self.expected_issues:
            raise ValueError("a clean case has no expected issues")
        if self.kind is not Kind.CLEAN and not self.expected_issues:
            raise ValueError("only clean cases may have no expected issues")
        ids = [issue.id for issue in self.expected_issues]
        if len(set(ids)) != len(ids):
            raise ValueError("expected issue ids must be unique within a case")
        return self


class Corpus(Strict):
    schema_version: Literal[1]
    name: str = Field(pattern=CORPUS_NAME)
    title: str = Field(min_length=1)
    origin: str = Field(min_length=1)
    source_url: str | None
    licence: str = Field(min_length=1)
    default: bool
    annotation: Annotation
    location_precision: LocationPrecision
    severity_available: bool
    created_at: date


class Dataset(Strict):
    schema_version: Literal[1]
    dataset_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
