#!/usr/bin/env python3
"""Static guard for likely non-ISO Pascal dialect features.

This is not a full ISO 7185 parser. It flags common FreePascal, Delphi, and
Object Pascal clues so a Pascal dataset can reject obvious dialect drift.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    column: int
    rule_id: str
    message: str
    snippet: str


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: re.Pattern[str]
    message: str


TOKEN_RULES = [
    Rule("FP_UNIT", re.compile(r"\bunit\b", re.IGNORECASE), "unit declarations are not ISO 7185 Pascal programs"),
    Rule(
        "FP_SECTION",
        re.compile(r"\b(?:interface|implementation|initialization|finalization)\b", re.IGNORECASE),
        "unit sections are not ISO 7185 Pascal",
    ),
    Rule(
        "FP_STRING_TYPE",
        re.compile(
            r"(?:(?::|(?<!:)=)\s*)string\b\s*\[\s*\d+\s*\]",
            re.IGNORECASE,
        ),
        "sized string types such as string[n] are not accepted by the reference grammar",
    ),
    Rule(
        "FP_OBJECT_PASCAL",
        re.compile(
            r"(?:(?<!:)=\s*(?:class|object)\b|\b(?:property|constructor|destructor|resourcestring|threadvar)\b|\boperator\s*(?:[+\-*/<>]|\w+\s*\())",
            re.IGNORECASE,
        ),
        "Object Pascal declarations are not ISO 7185 Pascal",
    ),
    Rule(
        "FP_EXCEPTION",
        re.compile(r"\b(?:try|except|finally|raise)\b", re.IGNORECASE),
        "exception handling is not ISO 7185 Pascal",
    ),
    Rule(
        "FP_INLINE_ASM",
        re.compile(r"\b(?:asm|assembler)\b", re.IGNORECASE),
        "inline assembly is not ISO 7185 Pascal",
    ),
    Rule(
        "FP_EXTENDED_PROC",
        re.compile(r"\b(?:overload|override|virtual|dynamic|external)\b", re.IGNORECASE),
        "extended procedure modifiers are not ISO 7185 Pascal",
    ),
]

DIRECTIVE_RE = re.compile(r"\{\$[^}\n]*\}|\(\*\$.*?\*\)", re.IGNORECASE | re.DOTALL)
BANG_RE = re.compile(r"!(?!=)")
FREEPASCAL_DIRECTIVE_RE = re.compile(
    r"\$\s*(?:mode|modeswitch|ifdef\s+(?:fpc|freepascal|objfpc|delphi)|ifndef\s+(?:fpc|freepascal|objfpc|delphi))\b",
    re.IGNORECASE,
)


def line_column(source: str, offset: int) -> tuple[int, int]:
    line = source.count("\n", 0, offset) + 1
    line_start = source.rfind("\n", 0, offset) + 1
    return line, offset - line_start + 1


def line_snippet(source: str, offset: int) -> str:
    line_start = source.rfind("\n", 0, offset) + 1
    line_end = source.find("\n", offset)
    if line_end == -1:
        line_end = len(source)
    return source[line_start:line_end].strip()


def make_violation(source: str, path: str, offset: int, rule_id: str, message: str) -> Violation:
    line, column = line_column(source, offset)
    return Violation(
        path=path,
        line=line,
        column=column,
        rule_id=rule_id,
        message=message,
        snippet=line_snippet(source, offset),
    )


def mask_range(chars: list[str], start: int, end: int) -> None:
    for index in range(start, end):
        if chars[index] != "\n":
            chars[index] = " "


def mask_pascal_source(source: str, *, mask_line_comments: bool = True) -> str:
    chars = list(source)
    index = 0
    while index < len(chars):
        char = chars[index]
        next_char = chars[index + 1] if index + 1 < len(chars) else ""

        if char == "'":
            start = index
            index += 1
            while index < len(chars):
                if chars[index] == "'":
                    if index + 1 < len(chars) and chars[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            mask_range(chars, start, index)
            continue

        if char == "{" and next_char != "$":
            start = index
            index += 1
            while index < len(chars) and chars[index] != "}":
                index += 1
            if index < len(chars):
                index += 1
            mask_range(chars, start, index)
            continue

        if char == "(" and next_char == "*" and index + 2 < len(chars) and chars[index + 2] != "$":
            start = index
            index += 2
            while index + 1 < len(chars) and not (chars[index] == "*" and chars[index + 1] == ")"):
                index += 1
            if index + 1 < len(chars):
                index += 2
            mask_range(chars, start, index)
            continue

        if mask_line_comments and char == "/" and next_char == "/":
            start = index
            index += 2
            while index < len(chars) and chars[index] != "\n":
                index += 1
            mask_range(chars, start, index)
            continue

        index += 1

    return "".join(chars)


def mask_preprocessor_lines(source: str) -> str:
    chars = list(source)
    line_start = 0
    while line_start < len(chars):
        line_end = source.find("\n", line_start)
        if line_end == -1:
            line_end = len(chars)
        if source[line_start:line_end].lstrip().startswith("#"):
            mask_range(chars, line_start, line_end)
        line_start = line_end + 1
    return "".join(chars)


def validate_source(source: str, path: str = "<string>") -> list[Violation]:
    masked = mask_preprocessor_lines(mask_pascal_source(source))
    violations: list[Violation] = []

    for match in DIRECTIVE_RE.finditer(masked):
        if not FREEPASCAL_DIRECTIVE_RE.search(match.group(0)):
            continue
        violations.append(
            make_violation(
                source,
                path,
                match.start(),
                "FP_DIRECTIVE",
                "FreePascal/Delphi mode directives are not accepted by the reference grammar",
            )
        )

    for rule in TOKEN_RULES:
        for match in rule.pattern.finditer(masked):
            violations.append(make_violation(source, path, match.start(), rule.rule_id, rule.message))

    for match in BANG_RE.finditer(masked):
        violations.append(
            make_violation(
                source,
                path,
                match.start(),
                "FP_BANG_NOT",
                "! boolean negation is not ISO 7185 Pascal; use not",
            )
        )

    violations.sort(key=lambda violation: (violation.path, violation.line, violation.column, violation.rule_id))
    return violations


def iter_pascal_files(paths: Iterable[Path | str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path)
        if path.is_dir():
            files.extend(
                candidate
                for candidate in sorted(path.rglob("*"))
                if candidate.is_file() and candidate.suffix.lower() == ".pas"
            )
        elif path.is_file():
            files.append(path)
    return files


def validate_paths(paths: Iterable[Path | str]) -> list[Violation]:
    violations: list[Violation] = []
    for path in iter_pascal_files(paths):
        source = path.read_text(encoding="utf-8", errors="replace")
        violations.extend(validate_source(source, path=str(path)))
    violations.sort(key=lambda violation: (violation.path, violation.line, violation.column, violation.rule_id))
    return violations


def format_text(violations: Sequence[Violation]) -> str:
    lines = []
    for violation in violations:
        lines.append(
            f"{violation.path}:{violation.line}:{violation.column}: "
            f"{violation.rule_id}: {violation.message}"
        )
        if violation.snippet:
            lines.append(f"  {violation.snippet}")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Flag likely FreePascal/Delphi extensions in Pascal source files."
    )
    parser.add_argument("paths", nargs="+", help="Pascal source files or directories to scan")
    parser.add_argument("--json", action="store_true", help="emit violations as JSON")
    args = parser.parse_args(argv)

    violations = validate_paths(args.paths)
    if args.json:
        print(json.dumps([asdict(violation) for violation in violations], indent=2))
    elif violations:
        print(format_text(violations))

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
