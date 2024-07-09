# Methodology notes

When we compare the two files, we have to do two steps

1. Detect areas where the code was replaced with placeholder comments
2. Merge the new code into the old code

What methods are sufficient for this?
1. Features
    - multiline deletion directly before an insertion
    - insertion is a single line comment
    - other features from `git diff` that could be useful
2. Certain keywords present in the comments
    - `// ...` or `// ... (rest of the previous code remains the same)`
    - `// Code Was Here`
3. LLM solution - use the LLM to detect the code that was replaced
    - This is a bit of a hack, but it could work
    - The LLM could be used to detect the code that was replaced
    - This would be a bit of a hack, but it could work
4. Use git diff
    - This can be used to bootstrap a basic categorization of the changes

To merge the code, we can use the following methods:

1. Greedy Merge
1. Create a git conflict
   a. Have the LLM decide how to merge
   b. Prompt users to merge (y/N, both, etc.)

I would like to also send the code to the LLM to see if it can detect features in the code that would be useful to understand the changes.


# Code Replacement Detection and Merging Methodology

## Detection Methods

### 1. Feature-based Detection
- Identify multiline deletions directly before an insertion
- Check if the insertion is a single line comment
- Utilize other useful features from `git diff` output

Implementation:
```python
def detect_replacements(diff_output):
    replacements = []
    current_deletion = []
    for line in diff_output.split('\n'):
        if line.startswith('-'):
            current_deletion.append(line[1:])
        elif line.startswith('+'):
            if current_deletion and is_likely_comment(line[1:]):
                replacements.append({
                    'deleted': current_deletion,
                    'inserted': line[1:]
                })
            current_deletion = []
        else:
            current_deletion = []
    return replacements

def is_likely_comment(line):
    comment_patterns = [r'^\s*#', r'^\s*//', r'^\s*/\*', r'^\s*--', r'^\s*%', r'^\s*;', r'^\s*<!--']
    return any(re.match(pattern, line) for pattern in comment_patterns)
```

### 2. Keyword-based Detection
- Look for specific phrases in comments like `// ...` or `// ... (rest of the previous code remains the same)`
- Search for placeholders like `// Code Was Here`

Implementation:
```python
def keyword_based_detection(inserted_line):
    keywords = [
        r'\.\.\.',
        r'rest of the previous code remains the same',
        r'Code Was Here'
    ]
    return any(keyword in inserted_line for keyword in keywords)
```

### 3. LLM-based Detection
- Use an LLM to analyze the diff and identify potential code replacements
- This method could be particularly useful for complex or ambiguous cases

Implementation:
```python
def llm_based_detection(diff_output):
    # This is a placeholder for the LLM-based detection logic
    # In practice, this would involve calling an LLM API
    prompt = f"Analyze the following git diff and identify potential code replacements:\n\n{diff_output}"
    # llm_response = call_llm_api(prompt)
    # return parse_llm_response(llm_response)
    pass
```

### 4. Git Diff Bootstrapping
- Use `git diff` output to categorize changes and identify potential replacements

Implementation:
```python
def git_diff_bootstrapping(file1, file2):
    diff_output = subprocess.run(['git', 'diff', '--no-index', file1, file2],
                                 capture_output=True, text=True).stdout
    return detect_replacements(diff_output)
```

## Merging Methods

### 1. Greedy Merge
- Automatically merge changes based on predefined rules

Implementation:
```python
def greedy_merge(original_code, detected_replacements):
    merged_code = original_code
    for replacement in detected_replacements:
        merged_code = merged_code.replace(
            ''.join(replacement['deleted']),
            replacement['inserted']
        )
    return merged_code
```

### 2. Git Conflict Creation
a. LLM-assisted merging
```python
def llm_assisted_merge(conflict):
    prompt = f"Resolve the following merge conflict:\n\n{conflict}"
    # resolution = call_llm_api(prompt)
    # return resolution
    pass
```

b. User-prompted merging
```python
def user_prompted_merge(conflict):
    print(f"Merge conflict:\n{conflict}")
    choice = input("How would you like to resolve this? (original/updated/both): ")
    if choice == 'original':
        return conflict.split('=======')[0].strip()
    elif choice == 'updated':
        return conflict.split('=======')[1].split('>>>>>>>')[0].strip()
    else:
        return conflict
```

## LLM Code Analysis
- Send the original and modified code to an LLM for feature detection and change understanding

Implementation:
```python
def llm_code_analysis(original_code, modified_code):
    prompt = f"""
    Analyze the following original and modified code:

    Original:
    {original_code}

    Modified:
    {modified_code}

    Identify key features and explain the changes made.
    """
    # analysis = call_llm_api(prompt)
    # return analysis
    pass
```

## Integrated Approach
To leverage all these methods, we can create a pipeline that:
1. Uses git diff for initial change detection
2. Applies feature-based and keyword-based detection
3. Uses LLM for ambiguous cases and deeper analysis
4. Merges changes using a combination of greedy merge and conflict resolution
5. Provides LLM-based insights on the changes

This approach allows for a robust, multi-faceted analysis of code replacements while providing flexibility in how to handle different scenarios.