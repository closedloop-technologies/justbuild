def merge_code(original_code: str, new_code: str) -> str:
    original_lines = original_code.split("\n")
    new_lines = new_code.split("\n")
    merged_lines = []
    i, j = 0, 0

    while i < len(new_lines):
        if is_code_placeholder(new_lines[i]):
            # Find the corresponding section in the original code
            while j < len(original_lines) and not is_code_placeholder(
                original_lines[j]
            ):
                merged_lines.append(original_lines[j])
                j += 1
        else:
            merged_lines.append(new_lines[i])
            j += 1

        i += 1
    return "\n".join(merged_lines)


def create_git_conflict(
    original_code: str, detected_replacements: List[Dict[str, List[str]]]
) -> List[str]:
    conflicts = []
    for replacement in detected_replacements:
        conflict = f"<<<<<<< lfg-previous-code\n{''.join(replacement['deleted'])}\n=======\n{''.join(replacement['inserted'])}\n>>>>>>> lfg-newly-generated-code\n"
        conflicts.append(conflict)
    return conflicts


def llm_assisted_merge(conflict: str) -> str:
    # TODO: Improve prompt to get more reliable resolutions
    prompt = f"You are a coding assistant named 'lfg'.  Resolve the following merge conflict which may have been :\n\n{conflict}\n\nProvide only the resolved code without any explanations."
    response = openai.Completion.create(
        engine="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.0,
    )
    return response.choices[0].text.strip()


def user_prompted_merge(conflict: str) -> str:
    print(f"Merge conflict:\n{conflict}")
    choice = typer.prompt("How would you like to resolve this? (original/updated/both)")
    if choice == "original":
        return (
            conflict.split("=======")[0].split("<<<<<<< lfg-previous-code\n")[1].strip()
        )
    elif choice == "updated":
        return (
            conflict.split("=======")[1]
            .split(">>>>>>> lfg-newly-generated-code")[0]
            .strip()
        )
    else:
        return conflict


def llm_code_analysis(original_code: str, modified_code: str) -> str:
    # TODO: Improve prompt to get more structured and detailed analysis
    prompt = f"""
    Analyze the following original and modified code:

    Original:
    {original_code}

    Modified:
    {modified_code}

    Identify key features and explain the changes made.
    """
    response = openai.Completion.create(
        engine="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.0,
    )
    return response.choices[0].text.strip()
