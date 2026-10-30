"""Versioned wire contracts only. Evaluation logic lives in the independent repository."""

import re
from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["queued", "reviewing", "incomplete", "delivery_failed", "available"]
Reviewer = Literal["evidence", "engineer", "sceptic", "impact", "delivery"]
Text = Annotated[str, Field(min_length=1, max_length=4000)]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceFile(WireModel):
    name: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=50000)

    @field_validator("content")
    @classmethod
    def text_content(cls, value: str) -> str:
        value = value.replace("\r\n", "\n").replace("\r", "\n")
        if not value.strip():
            raise ValueError("Evidence files must not be empty.")
        return value

    @field_validator("name")
    @classmethod
    def safe_name(cls, value: str) -> str:
        from pathlib import PurePosixPath

        extensions = {
            ".txt",
            ".md",
            ".csv",
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".dart",
            ".java",
            ".go",
            ".rs",
            ".html",
            ".css",
            ".sql",
            ".json",
            ".yaml",
            ".yml",
            ".c",
            ".cpp",
            ".h",
        }
        if (
            not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]*", value)
            or ".." in value
            or value.endswith((" ", "."))
            or PurePosixPath(value).suffix.lower() not in extensions
        ):
            raise ValueError("Use a plain accepted text/source filename.")
        return value


class CouncilEvidence(WireModel):
    title: str = Field(min_length=1, max_length=200)
    research_question: str = Field(min_length=1, max_length=10000)
    findings: str = Field(min_length=1, max_length=20000)
    methods: str = Field(default="", max_length=20000)
    results: str = Field(default="", max_length=20000)
    limitations: str = Field(default="", max_length=10000)
    files: list[EvidenceFile] = Field(default_factory=list, max_length=20)

    @field_validator("title", "research_question", "findings", "methods", "results", "limitations")
    @classmethod
    def normalized_text(cls, value: str) -> str:
        return value.replace("\r\n", "\n").replace("\r", "\n").strip()

    @model_validator(mode="after")
    def safe_evidence(self) -> "CouncilEvidence":
        values = [
            self.title,
            self.research_question,
            self.findings,
            self.methods,
            self.results,
            self.limitations,
        ] + [f.content for f in self.files]
        try:
            for value in values:
                value.encode("utf-8", errors="strict")
                if any(ord(c) < 32 and c not in "\r\n\t" for c in value):
                    raise ValueError("Control characters are not accepted.")
        except UnicodeError as exc:
            raise ValueError("Evidence must be valid UTF-8.") from exc
        if not all(value.strip() for value in values[:3]):
            raise ValueError("Title, question and findings are required.")
        if sum(len(value) for value in values) > 200000:
            raise ValueError("Total evidence exceeds 200,000 characters.")
        if len({f.name.casefold() for f in self.files}) != len(self.files):
            raise ValueError("Duplicate filenames are not accepted.")
        return self


class Ref(WireModel):
    evidence_id: str = Field(pattern=r"^E[0-9]{2}$")
    start_line: int = Field(ge=1, strict=True)
    end_line: int = Field(ge=1, strict=True)


class Strength(WireModel):
    detail: Text
    evidence: list[Ref] = Field(min_length=1, max_length=10)


class Issue(WireModel):
    title: str = Field(min_length=1, max_length=200)
    severity: Literal["Critical", "Moderate", "Nitpick"]
    claim_status: Literal["supported", "contradicted", "not_verifiable"]
    detail: Text
    consequence: Text
    improvement: Text
    verification: Text
    evidence: list[Ref] = Field(min_length=1, max_length=10)


class Review(WireModel):
    reviewer: Reviewer
    strengths: list[Strength] = Field(max_length=10)
    issues: list[Issue] = Field(max_length=15)
    limitations: list[Text] = Field(min_length=1, max_length=10)


class Priority(WireModel):
    title: str
    severity: Literal["Critical", "Moderate", "Nitpick"]
    reviewers: list[Reviewer]
    issues: list[Issue]
    disagreement: bool


class CouncilReport(WireModel):
    version: Literal["1.0"]
    simulated: bool
    model: str
    prompt_version: str
    summary: str
    reviewers: list[Review] = Field(min_length=5, max_length=5)
    priorities: list[Priority]
    limitations: list[str]

    @model_validator(mode="after")
    def all_reviewers(self) -> "CouncilReport":
        if {r.reviewer for r in self.reviewers} != {
            "evidence",
            "engineer",
            "sceptic",
            "impact",
            "delivery",
        }:
            raise ValueError("Exactly five different reviewers are required.")
        return self


class RemoteAssessment(BaseModel):
    id: UUID
    status: Literal["queued", "running", "incomplete", "completed"]
    completed_reviewers: int = Field(ge=0, le=5)
    project: CouncilEvidence
    report: CouncilReport | None = None


class SupervisorCreate(WireModel):
    faculty_id: UUID


class SupervisorRead(WireModel):
    faculty_id: UUID | None
    display_name: str | None


class FacultyRead(WireModel):
    id: UUID
    display_name: str


class FacultyList(WireModel):
    items: list[FacultyRead]


class AssessmentRead(WireModel):
    id: UUID
    submission_id: UUID
    title: str
    status: Status
    completed_reviewers: int
    created_at: datetime
    error: str | None
    supervisor_name: str


class AssessmentDetail(AssessmentRead):
    report: dict[str, Any] | None
    evidence: CouncilEvidence


class AssessmentList(WireModel):
    items: list[AssessmentRead]


class PdfRead(WireModel):
    content_base64: str
