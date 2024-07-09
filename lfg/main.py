import os
import re
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import openai
import pyperclip
import tqdm
import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from lfg.code_diffs import CodeDiffs, code_diff_around_segment, parse_git_diff
from lfg.config import Config, load_config
from lfg.find_sections import build_features, run_git_diff
from lfg.helpers import (
    get_changed_files,
    get_file_content,
    get_staged_changes,
    is_git_repo,
)

config = load_config()
app = typer.Typer(name="lfg", help="Chat Assisted Programming Tools")


class GreedyModel:
    """Heuristic-based model to revert code sections that are likely to be omitted"""

    def __init__(self, **kwargs):
        self.params = kwargs

    def fit(self, features: List[dict]) -> None:
        pass  # no training required

    def _formula(self, features: dict) -> dict:
        if features.get("change_sequence_type") != "replaced_previous":
            return {"is_code_omission": False, "confidence": 0.95}

        fcast = (
            features.get("segment_size") == 1 and features.get("prev_segment_size") > 10
        )
        return {
            "is_code_omission": fcast,
            "confidence": 0.3 + 0.6 * float(fcast),
        }

    def predict(self, features: List[dict]) -> List[dict]:
        return [
            {
                "_id": d["_id"],
                "omitted_code": d["_prev_segment"],
                "replaced_code": d["_curr_segment"],
                **self._formula(d),
            }
            for d in features
        ]


class LLMModel:

    def __init__(self, config: Config, **kwargs):
        self.config = config
        self.params = kwargs

    def fit(self, *args) -> None:  # noqa
        pass

    def _request(self, feature: dict, code_diffs: CodeDiffs) -> dict:
        system_prompt = """Analyze the following `git diff` output to determine if the original code was replaced with a "Placeholder Comment":

### Definition of a Placeholder Comment
A placeholder comment is a descriptive note within the code that indicates a section of the code is intentionally omitted or remains unchanged, often represented by ellipsis or specific text.

### Checklist to Identify Placeholder Comments in a `git diff`

1. **Ellipsis (`...`) Usage**:
   - Look for ellipsis within the comment, which often signifies omitted code.

2. **Descriptive Text**:
   - Check if the comment contains text that describes the omitted code or indicates that the content remains unchanged (e.g., "form content remains the same").

3. **Contextual Placement**:
   - Ensure the comment is placed in a logical location where significant code blocks would typically exist (e.g., within a form, function, or component).

4. **Consistency with Surrounding Code**:
   - Verify that the comment is consistent with the surrounding code structure, suggesting it is a placeholder for more detailed implementations.

5. **Purpose Indication**:
   - Determine if the comment clearly indicates its purpose, such as explaining the functionality or section of the code that is not shown.

### Example of a Placeholder Comment in a `git diff`
```diff
-                <div className="flex items-center border-2 border-gray-300 rounded-lg p-2">
-                    <input
-                        ref={inputRef}
-                        name="input"
-                        type="text"
-                        value={input}
-                        onChange={(e) => setInput(e.target.value)}
-                        className="flex-grow outline-none"
-                        placeholder="What should we brainstorm today?"
-                    />
-                    <button
-                        type="button"
-                        onClick={handleVoiceInput}
-                        className={`mx-2 ${isRecording ? "text-red-500" : "text-gray-500"}`}
-                    >
-                        <MicIcon size={20} />
-                    </button>
-                    <button
-                        type="button"
-                        onClick={handleAttachment}
-                        className="mx-2 text-gray-500"
-                    >
-                        <PaperclipIcon size={20} />
-                    </button>
-                    <button
-                        type="submit"
-                        className="text-blue-500"
-                        disabled={fetcher.state === "submitting"}
-                    >
-                        <SendIcon size={20} />
-                    </button>
-                </div>
+                {/* ... (form content remains the same) ... */}
```

By following this checklist, you can effectively identify placeholder comments in a `git diff` and understand their purpose within the code.

Think step by step about the context of the code and the purpose of the diff to determine if the new code is a placeholder for the original code.

Your answer must end with 'yes' or 'no' to indicate whether the new code is a placeholder comment for the original code."""

        user_message = f"""```diff
{feature['_diff']}
```
Is the following line a placeholder comment for the original code? (yes/no)
```
{feature.get("_curr_segment","")}
```
"""
        # if "loader implementation remains the same" in feature.get("_curr_segment", ""):
        #     return {"confidence": 0.95, "is_code_omission": True}
        result = self.config.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            model=config.model_name,
            max_tokens=500,
            n=1,
            stop=None,
            temperature=config.model_temperature,
        )
        if len(result.choices) == 0 or result.choices[0].finish_reason != "stop":
            raise RuntimeError("OpenAI API did not return a response")

        if len(result.choices):
            response = result.choices[0].message.content.lower().split()[::-1]
            for w in response:
                # remove punctuation
                w = re.sub(r"[^\w\s]", "", w)
                if w == "yes":
                    return {"confidence": 0.95, "is_code_omission": True}
                elif w == "no":
                    return {"confidence": 0.95, "is_code_omission": False}
        return {"confidence": 0.95, "is_code_omission": False}

    def predict(self, features: List[dict], code_diffs: CodeDiffs) -> List[dict]:
        # TODO parallelize
        results = []
        for f in tqdm.tqdm(features):
            if f is None:
                results.append(
                    {"confidence": None, "is_code_omission": False, "_id": f["_id"]}
                )
            else:
                results.append(
                    {"_id": f["_id"], **self._request(f, code_diffs=code_diffs)}
                )
        return results


def human_in_the_loop_labeling(
    samples: List[Dict], label="label", default_confidence=0.99
) -> List[Dict]:
    """
    Allow the user to review and label code diffs for placeholder comments.
    """
    console = Console()
    labeled_inputs = []

    def _show_title(console):
        console.print(
            Panel(
                "[bold]Placeholder Comment Definition[/bold]\n\n"
                "A placeholder comment is a descriptive note within the code that indicates "
                "a section of the code is intentionally omitted or remains unchanged, often "
                "represented by ellipsis or specific text.",
                title="Information",
                expand=False,
            )
        )

    for index, input_dict in enumerate(samples, start=1):
        _show_title(console)
        console.print(f"\n[bold]Reviewing diff {index} of {len(samples)}[/bold]\n")

        # Display the diff using rich's Syntax highlighting
        diff_syntax = Syntax(
            input_dict["_diff"], "diff", theme="monokai", line_numbers=True
        )
        console.print(diff_syntax)

        # Ask the user for input
        contains_placeholder = typer.confirm(
            "Does this diff contain a Placeholder Comment to be reverted?",
            default=False,
        )

        # Add the user's label to the dictionary
        input_dict[label] = contains_placeholder
        input_dict["confidence"] = default_confidence
        labeled_inputs.append(input_dict)

        # Clear the screen for the next diff
        console.clear()

    return labeled_inputs


def merge_code(
    old_file: Optional[Path] = None,
    new_file: Optional[Path] = None,
    target_file: Optional[Path] = None,
    config: Optional[Config] = None,
    **kwargs,
) -> dict:
    """Combine code into target_file from new_file and old_file
    Particularly focusing on LLM-related code section ommissions

    We can do greedy merging of code sections
    We can use LLM to assist in merging code sections
    We can prompt the user to resolve code sections
    """
    if config is None:
        config = Config.create()

    if new_file is None:
        raise ValueError("new_file must be provided")

    if target_file is None:
        target_file = new_file

    # Step 1: Find Likely Section Omissions
    ## Most Granular - Look at all diffs to approve and reject
    all_diffs = run_git_diff(old_file, new_file)
    diffs = parse_git_diff(all_diffs)

    # Model Creation
    build_features(diffs)

    # Run Models
    # The goal of this model is to identify code sections were
    # likely omitted from the new code and replaced with a placeholder comment

    # The input is a list of code DiffSegments with dictionaries of features
    # The output is a dictionary list with keys:
    # label='code_omission', 'confidence'=0.9, 'omitted_code'=List[str], segment=DiffSegment
    inputs = [
        {
            "_id": None,  # Counter to be added later
            "_diff": i,
            "_segment": j,
            "_prev_segment": "\n".join(diffs.changes[i].segments[j - 1].content),
            "_curr_segment": "\n".join(diffs.changes[i].segments[j].content),
            "_diff": code_diff_around_segment(diffs, i, j),
            **(segment.features or {}),
        }
        for i, diff in enumerate(diffs.changes)
        for j, segment in enumerate(diff.segments)
        if j > 0
    ]
    for counter, i in enumerate(inputs):
        i["_id"] = counter

    ## Less Granular - Only likely omitted code sections
    ## Least Granular - Only look at known code placeholders

    # Step 2: Merge Code
    ## Greedy - Merge all code sections
    predictions = GreedyModel().predict(inputs)

    ## LLM - Use LLM to merge code sections
    llm_filtered_inputs = [
        i
        for i, d in zip(inputs, predictions)
        if (not d["is_code_omission"] and d["confidence"] < 0.9)
        or (d["is_code_omission"] and d["confidence"] > 0.1)
    ]
    llm_filtered_predictions = LLMModel(config=config).predict(
        llm_filtered_inputs, code_diffs=diffs
    )

    # import pandas as pd

    # aggregating results

    outputs = defaultdict(dict)
    for pred in llm_filtered_predictions:
        outputs[pred["_id"]]["llm"] = {
            k: v for k, v in pred.items() if k in ["is_code_omission", "confidence"]
        }
    for pred in predictions:
        outputs[pred["_id"]]["naive"] = {
            k: v for k, v in pred.items() if k in ["is_code_omission", "confidence"]
        }

    disagreements = [
        i
        for i, output in outputs.items()
        if (
            "llm" in output
            and "naive" in output
            and output["llm"]["is_code_omission"] != output["naive"]["is_code_omission"]
        )
    ]
    # Create a user prompt for each code section in llm_filtered_inputs to manually y/n
    # for each code section

    # Options:
    # Broad: Loop only where confidence is low (llm_filtered_inputs)
    broad_samples = [
        {"_id": i, "_diff": sample["_diff"]}
        for i, sample in enumerate(llm_filtered_inputs)
        if sample is not None
    ]
    # Narrow: Loop only where disagreement between greedy and llm
    narrow_samples = [{"_id": i, "_diff": inputs[i]["_diff"]} for i in disagreements]

    human_labels = human_in_the_loop_labeling(
        narrow_samples, label="is_code_omission", default_confidence=0.99
    )
    for pred in human_labels:
        outputs[pred["_id"]]["human"] = {
            k: v for k, v in pred.items() if k in ["is_code_omission", "confidence"]
        }

    # Merge Outputs - this is a naive way that ignores confidence
    for i, output in outputs.items():
        if "human" in output:
            outputs[i]["final"] = output["human"]
        elif "llm" in output:
            outputs[i]["final"] = output["llm"]
        else:
            outputs[i]["final"] = output["naive"]

    # Where 'final' outputs are True, replace the code with the omitted code
    merged_code = get_file_content(new_file)
    {k: v["final"] for k, v in outputs.items() if v["final"]["is_code_omission"]}

    change_log = []
    for i, output in outputs.items():
        if output["final"]["is_code_omission"]:
            if merged_code.count(inputs[i]["_curr_segment"]) != 1:
                raise ValueError("Code segment occurs more than once in the code")

            merged_code = merged_code.replace(
                inputs[i]["_curr_segment"], inputs[i]["_prev_segment"]
            )
            change_log.append(
                {
                    "confidence": output["final"].get("confidence"),
                    "git_diff": inputs[i]["_diff"],
                    "omitted_code": inputs[i]["_curr_segment"],
                    "replaced_code": inputs[i]["_prev_segment"],
                }
            )
    # all_replacements = feature_replacements + llm_replacements
    # unique_replacements = [
    #     dict(t) for t in {tuple(sorted(d.items())) for d in all_replacements}
    # ]
    target_file.write_text(merged_code)
    typer.echo(f"LFG 🚀! {len(change_log)} Code Omissions Corrected: {target_file}")
    return {
        "old_file": old_file,
        "new_file": new_file,
        "target_file": target_file,
        "changes": change_log,
        "labels": human_labels,
    }


def merge_all(
    config: Optional[Config] = None,
    **kwargs,
) -> dict:
    if config is None:
        config = Config.create()

    # Assert that git is installed and that we are inside a git repo
    if not config.git_installed:
        raise RuntimeError("Git is not installed on this system")
    if not is_git_repo():
        raise RuntimeError("Not inside a git repository")

    # Get list of changed files
    changed_files = get_changed_files()

    results = {}
    for file in changed_files:
        try:
            results[file] = merge_code(
                old_file=None, new_file=file, target_file=file, config=config, **kwargs
            )
        except Exception as e:
            results[file] = {"error": str(e)}
    return results


@app.command()
def paste(file_path: str = typer.Argument(...)):
    """
    Paste new code from clipboard into the specified file, preserving existing code where indicated.
    """
    file_path = Path(file_path)
    file_type_suffix = str(file_path).split(".")[-1]

    tempfilename = Path(tempfile.mkstemp(prefix="lfg-", suffix=file_type_suffix)[1])
    new_code = pyperclip.paste()
    if not new_code:
        typer.echo("No code found in clipboard")
        raise typer.Exit()
    with open(tempfilename, "w") as file:
        file.write(new_code)

    if not file_path.exists():
        file_path.mkdir(parents=True, exist_ok=True)
        Path(file_path).touch()

    updates = merge_code(
        old_file=file_path, new_file=tempfilename, target_file=file_path
    )
    typer.echo(f"Code pasted and merged into {file_path} with updates:\n{updates}")


@app.command()
def merge(
    updated_file: str = typer.Argument(..., help="Path to the modified file"),
    old_file: str = typer.Option(..., help="Path to the original file"),
    target_file: str = typer.Option(
        ..., help="Path to the output file, defaults to `new_file`"
    ),
    auto_resolve: bool = typer.Option(
        False, "--auto-resolve", "-a", help="Automatically resolve conflicts using LLM"
    ),
):
    """
    Merge changes from new_file into old_file, or merge changes in the entire repo if no files are specified.
    """
    if not old_file and not updated_file and not target_file:
        typer.echo("No files specified to merge")
        merge_all()
        raise typer.Exit()

    old_file = Path(old_file) if old_file else None
    updated_file = Path(updated_file)
    target_file = Path(target_file) if target_file else updated_file

    updates = merge_code(
        old_file=old_file, new_file=updated_file, target_file=target_file
    )
    typer.echo(f"Code pasted and merged into {target_file} with updates:\n{updates}")


# Entry point for the CLI is the `app` object loaded from __main__.py
