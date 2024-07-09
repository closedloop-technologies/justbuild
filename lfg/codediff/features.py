import re

from lfg.codediff.git_diff_calculations import CodeDiff


def is_likely_comment(line: str) -> bool:
    comment_patterns = [
        r"^\s*#",  # Python, Ruby, Perl, Shell
        r"^\s*//",  # C, C++, Java, JavaScript
        r"^\s*/\*",  # C, C++, Java, JavaScript (multi-line start)
        r"^\s*--",  # SQL, Lua
        r"^\s*%",  # Matlab, LaTeX
        r"^\s*;",  # Assembly, Lisp
        r"^\s*<!--",  # HTML, XML
        r"^\s*\(\*",  # OCaml
        r"^\s*\{-",  # Haskell
    ]
    return any(re.match(pattern, line) for pattern in comment_patterns)


def is_code_placeholder(line: str) -> bool:
    placeholders = [
        r"// ... \(rest of the previous code remains the same\)",
        r"// Code Was Here",
        r"# ... \(rest of the previous code remains the same\)",
        r"# Code Was Here",
    ]
    return any(re.search(pattern, line) for pattern in placeholders)


def keyword_based_detection(inserted_line: str) -> bool:
    keywords = [
        r"\.\.\.",
        r"rest of the previous code remains the same",
        r"Code Was Here",
    ]
    return any(keyword in inserted_line for keyword in keywords)


def build_features(code_diff: CodeDiff):
    for diff in code_diff.changes:
        prev_segment = None
        for segment in diff.segments:
            if segment.features is None:
                segment.features = {}
            # Segment Features
            if prev_segment:
                if prev_segment.type == segment.type:
                    raise ValueError("Consecutive segments of the same type")
                elif segment.type == "addition" and prev_segment.type == "deletion":
                    segment.features["change_sequence_type"] = "replaced_previous"
                elif segment.type == "deletion" and prev_segment.type == "addition":
                    segment.features["change_sequence_type"] = "removed_previous"
                elif prev_segment.type == "unchanged":
                    segment.features["change_sequence_type"] = segment.type
                elif segment.type == "unchanged":
                    segment.features["change_sequence_type"] = "unchanged"
                else:
                    raise ValueError("Unknown segment sequence")
            else:
                segment.features["change_sequence_type"] = segment.type

            segment.features["segment_size"] = len(segment.content)
            segment.features["prev_segment_size"] = (
                len(prev_segment.content) if prev_segment else 0
            )

            # Line Features
            segment.features["has_comment"] = any(
                is_likely_comment(line) for line in segment.content
            )
            segment.features["has_placeholder_word"] = any(
                is_code_placeholder(line) for line in segment.content
            )
            segment.features["has_keyword"] = any(
                keyword_based_detection(line) for line in segment.content
            )
            #
            prev_segment = segment
