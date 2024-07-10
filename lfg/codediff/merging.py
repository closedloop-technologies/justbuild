import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Optional, Tuple

import typer

from lfg.codediff.features import build_features
from lfg.codediff.git_diff_calculations import code_diff_around_segment, parse_git_diff
from lfg.codediff.git_wrappers import get_changed_files, is_git_repo, run_git_diff
from lfg.codediff.human_in_the_loop import labeling
from lfg.codediff.models import GreedyModel
from lfg.codediff.models_llm import LLMModel
from lfg.config import Config


def merge(
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
            "_diff_index": i,
            "_segment_index": j,
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

    # print(code_diff_around_segment(diffs, 2, 4))

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

    human_labels = labeling(
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
    merged_code = new_file.read_text()
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

    target_file.write_text(merged_code)
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
            results[file] = merge(
                old_file=None, new_file=file, target_file=file, config=config, **kwargs
            )
        except Exception as e:
            results[file] = {"error": str(e)}
    return results


def merge_code(
    old_code: str,
    new_code: str,
    file_type_suffix: Optional[str] = None,
    config: Optional[Config] = None,
    **kwargs,
) -> Tuple[str, dict]:
    if config is None:
        config = Config.create()

    if not old_code or not new_code:
        raise ValueError("Both old_code and new_code must be provided")

    file_type_suffix = file_type_suffix or None

    new_file = Path(tempfile.mkstemp(prefix="lfg-", suffix=file_type_suffix)[1])
    old_file = Path(tempfile.mkstemp(prefix="lfg-", suffix=file_type_suffix)[1])
    target_file = Path(tempfile.mkstemp(prefix="lfg-", suffix=file_type_suffix)[1])

    with open(new_file, "w") as file:
        file.write(new_code)
    with open(old_file, "w") as file:
        file.write(old_code)

    updates = merge(old_file, new_file, target_file, config=config, **kwargs)
    output = target_file.read_text()
    target_file.unlink()
    new_file.unlink()
    old_file.unlink()
    return output, {
        "changes": updates["changes"],
        "labels": updates["labels"],
    }
