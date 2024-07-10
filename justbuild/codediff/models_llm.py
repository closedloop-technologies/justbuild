import concurrent.futures
import re
from typing import List

import tqdm

from justbuild.codediff.git_diff_calculations import CodeDiffs
from justbuild.config import Config

SYSTEM_PROMPT = """Analyze the following `git diff` output to determine if the original code was replaced with a "Placeholder Comment":

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

6. **Length Differences**:
   - There are a significant number of lines in the original code that are missing in the new code, indicating a placeholder comment.
   - The new code is much shorter than the original code, suggesting omitted content.

7. **Code Omission Indicators**:
    - Look for specific phrases like "Code Was Here" or "rest of the previous code remains the same" that are commonly used as placeholders.

8. **Code Comments**:
    - The majority of the new code in the diff is comments or placeholder text.

### Samples of Placeholder Comments

 - `# ... (SYSTEM_PROMPT remains unchanged)`
 - `# ... (This method remains unchanged)`
 - `// ... (previous handler functions remain the same)`
 - `// ... (previous hotkey handlers remain the same)`
 - `// ... (rest of the previous code remains the same)`
 - `// ... (previous state and handlers remain the same)`
 - `// ... (previous imports and code remain the same)`
 - `{/* ... (previous content remains the same) */}`

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
Response: yes

### Negative Example: Not a Placeholder Comment in a `git diff`
```diff
 } from "~/models/brainstorm.server";
 import invariant from "tiny-invariant";

-import DynamicComponent from '~/components/DynamicComponent';
+import DynamicComponent from "~/components/DynamicComponent";
+import { Button } from "~/components/ui/button";
+import {
+    DropdownMenu,
+    DropdownMenuContent,
+    DropdownMenuItem,
+    DropdownMenuTrigger,
+} from "~/components/ui/dropdown-menu";
+import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "~/components/ui/dialog";

 interface BrainstormingBotPageProps {
     currentBrainstorm: BrainstormSession;
```
Response: no

### Negative Example: Not a Placeholder Comment in a `git diff`
```
     return (
-        <div className="flex flex-col h-screen p-4">
+        <div className="flex flex-col p-4">
+            {/* Header */}
             <h1 className="text-2xl font-bold mb-4">
                 Task: {currentBrainstorm.title}
             </h1>
```
Response: no

### Negative Example: Not a Placeholder Comment in a `git diff`
```diff
             </div>

-            {/* Display brainstorming results here */}
-            <div className="border-2 border-gray-300 rounded-lg p-2 flex-grow overflow-y-auto">
-                {samples &&
-                    samples?.map((input: any, index: number) => (
-                        <DynamicComponent
-                            componentName={activeDataView}
-                            key_name={index}
-                            props={{
-                                data: input
-                            }}
-                        />
-                    ))}
+            {/* Scrollable results area */}
+            <div className="flex-grow overflow-y-auto">
+                <div className="border-2 border-gray-300 rounded-lg p-2 mb-4">
+                    {samples &&
+                        samples?.map((input: any, index: number) => (
+                            <DynamicComponent
+                                componentName={activeDataView}
+                                key_name={index}
+                                props={{
+                                    data: input,
+                                }}
+                            />
+                        ))}
+                </div>
             </div>
```
Response: no

By following this checklist, you can effectively identify placeholder comments in a `git diff` and understand their purpose within the code.

Think step by step about the context of the code and the purpose of the diff to determine if the new code is a placeholder for the original code.

Start your response with a list of the features you identified in the diff, followed by your answer to the question below.

Your answer must end with 'yes' or 'no' to indicate whether the new code is a placeholder comment for the original code."""


class LLMModel:

    def __init__(self, config: Config, **kwargs):
        self.config = config
        self.params = kwargs

    def fit(self, *args) -> None:  # noqa
        pass

    def _request(self, feature: dict, code_diffs: CodeDiffs) -> dict:

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
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            model=self.config.model_name,
            max_tokens=1000,
            n=1,
            stop=None,
            temperature=self.config.model_temperature,
        )
        if len(result.choices) == 0 or result.choices[0].finish_reason != "stop":
            raise RuntimeError("OpenAI API did not return a response")

        if len(result.choices):
            content = result.choices[0].message.content
            response = content.lower().split()[::-1]
            for w in response:
                # remove punctuation
                w = re.sub(r"[^\w\s]", "", w)
                if w == "yes":
                    return {
                        "confidence": 0.95,
                        "is_code_omission": True,
                        "response": content,
                    }
                elif w == "no":
                    return {
                        "confidence": 0.95,
                        "is_code_omission": False,
                        "response": content,
                    }
        return {"confidence": 0.95, "is_code_omission": False}

    def predict(self, features: List[dict], code_diffs: CodeDiffs) -> List[dict]:
        features = [f for f in features if f is not None]
        return [
            {"_id": f["_id"], **self._request(f, code_diffs=code_diffs)}
            for f in tqdm.tqdm(features)
        ]

    def predict(self, features: List[dict], code_diffs: CodeDiffs) -> List[dict]:
        features = [f for f in features if f is not None]

        def process_feature(feature):
            return {
                "_id": feature["_id"],
                **self._request(feature, code_diffs=code_diffs),
            }

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_feature = {
                executor.submit(process_feature, feature): feature
                for feature in features
            }
            results = []
            for future in tqdm.tqdm(
                concurrent.futures.as_completed(future_to_feature),
                total=len(features),
                desc="LFG - LLM Code Omission Detection",
            ):
                results.append(future.result())

        return results
