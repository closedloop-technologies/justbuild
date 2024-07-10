import re
from functools import lru_cache

from lfg.codediff.git_diff_calculations import CodeDiff


def is_likely_comment(line: str) -> bool:
    @lru_cache(maxsize=1)
    def get_compiled_patterns():
        patterns = [
            r"^\s*#",  # Python, Ruby, Perl, Shell, Makefile
            r"^\s*//",  # C, C++, Java, JavaScript, Go, Rust, Swift
            r"^\s*/\*",  # C, C++, Java, JavaScript, CSS (multi-line start)
            r"\*/\s*$",  # Multi-line comment end
            r"^\s*\{/\*",  # TypeScript, JavaScript (alternative multi-line)
            r"^\s*--",  # SQL, Lua, Haskell
            r"^\s*%",  # Matlab, LaTeX, Prolog
            r"^\s*;",  # Assembly, Lisp, Clojure
            r"^\s*<!--",  # HTML, XML, Markdown
            r"^\s*\(\*",  # OCaml, Pascal
            r"^\s*\{-",  # Haskell (multi-line start)
            r"^\s*'''",  # Python (multi-line string/comment)
            r'^\s*"""',  # Python (multi-line string/comment)
            r"^\s*REM\s",  # BASIC, batch files
            r"^\s*\/\/\/",  # Swift, Kotlin (documentation comments)
            r"^\s*<!",  # DTD
            r"^\s*--\[\[",  # Lua (multi-line start)
            r"^\s*=begin",  # Ruby (multi-line start)
        ]
        return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    # Get the compiled patterns (will be cached after first call)
    compiled_patterns = get_compiled_patterns()

    # Check if any pattern matches
    return any(pattern.match(line) for pattern in compiled_patterns)


def is_known_code_placeholder(line: str) -> bool:
    placeholders = [
        r"// ... \(rest of the previous code remains the same\)",
        r"// Code Was Here",
        r"# ... \(rest of the previous code remains the same\)",
        r"# Code Was Here",
    ]
    return any(re.search(pattern, line) for pattern in placeholders)


def keyword_based_detection(inserted_line: str) -> bool:
    keywords = [
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
                is_known_code_placeholder(line) for line in segment.content
            )
            # Ellipsis is a common placeholder for code
            segment.features["has_ellipsis"] = any(
                "..." in line for line in segment.content
            )
            segment.features["has_keyword"] = any(
                keyword_based_detection(line) for line in segment.content
            )
            #
            prev_segment = segment
