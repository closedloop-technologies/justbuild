import re
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class DiffSegment:
    type: str  # 'addition' or 'deletion'
    content: List[str]
    features: Dict[str, List[str]] = None


@dataclass
class CodeDiff:
    lineno: int
    raw_code_diff: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    segments: List[DiffSegment]


@dataclass
class CodeDiffs:
    old_file: str
    new_file: str
    changes: List[CodeDiff]


def parse_diff_header(header: str) -> Dict[str, int]:
    if match := re.match(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@", header):
        return {
            "old_start": int(match[1]),
            "old_count": int(match[2]),
            "new_start": int(match[3]),
            "new_count": int(match[4]),
        }
    return {}


def parse_git_diff(diff_output: str) -> CodeDiffs:
    lines = diff_output.split("\n")
    code_diffs = CodeDiffs(old_file="", new_file="", changes=[])
    current_diff = None
    current_segment = None
    for line in lines:
        if line.startswith("--- "):
            if code_diffs.old_file:
                raise ValueError("Multiple old files detected")
            code_diffs.old_file = line[4:].strip()
            continue
        if line.startswith("+++ "):
            if code_diffs.new_file:
                raise ValueError("Multiple new files detected")
            code_diffs.new_file = line[4:].strip()
            continue

        if line.startswith("@@"):
            if current_diff:
                if current_segment:
                    current_diff.segments.append(current_segment)
                code_diffs.changes.append(current_diff)
            header_info = parse_diff_header(line)
            current_diff = CodeDiff(
                lineno=header_info["new_start"],
                raw_code_diff="",
                old_start=header_info["old_start"],
                old_count=header_info["old_count"],
                new_start=header_info["new_start"],
                new_count=header_info["new_count"],
                segments=[],
            )
            current_segment = None
            continue

        if current_diff is None:
            raise ValueError("Diff header not found")

        if line.startswith("-"):
            if current_segment and current_segment.type != "deletion":
                current_diff.segments.append(current_segment)
                current_segment = None
            if not current_segment:
                current_segment = DiffSegment(type="deletion", content=[])
        elif line.startswith("+"):
            if current_segment and current_segment.type != "addition":
                current_diff.segments.append(current_segment)
                current_segment = None
            if not current_segment:
                current_segment = DiffSegment(type="addition", content=[])
        else:
            if current_segment and current_segment.type != "unchanged":
                current_diff.segments.append(current_segment)
                current_segment = None
            if not current_segment:
                current_segment = DiffSegment(type="unchanged", content=[])
        current_segment.content.append(line[1:])
        current_diff.raw_code_diff += line + "\n"

    if current_diff:
        if current_segment:
            current_diff.segments.append(current_segment)
        code_diffs.changes.append(current_diff)

    return code_diffs


def code_diff_around_segment(
    diffs: CodeDiffs, diff_index: int, segment_index: int
) -> str:
    """Returns a block of code from the diff that contains the current segment,
    the previous segment and any preceding or subsequent segments that are 'unchanged'
    """
    diff = diffs.changes[diff_index]
    segment = diff.segments[segment_index]
    # Find the start and end of the segment
    start = segment_index
    end = segment_index

    # First traverse back through the previous segments allowing for
    if segment.type == "addition":
        prior_segment_type = "deletion"
    elif segment.type == "deletion":
        prior_segment_type = "addition"
    else:
        prior_segment_type = "unchanged"
    while start > 0 and diff.segments[start - 1].type == prior_segment_type:
        start -= 1
    while start > 0 and diff.segments[start - 1].type == "unchanged":
        start -= 1
    while end + 1 < len(diff.segments) and diff.segments[end + 1].type == "unchanged":
        end += 1

    # Build the raw code diff
    raw_code_diff = []
    for k in range(start, end + 1):
        segment = diff.segments[k]
        if segment.type == "addition":
            raw_code_diff.append("+" + "\n+".join(segment.content))
        elif segment.type == "deletion":
            raw_code_diff.append("-" + "\n-".join(segment.content))
        else:
            raw_code_diff.append(" " + "\n ".join(segment.content))
    return "\n".join(raw_code_diff)
