# LFG! Tools for better Chat Assisted Programming

We all use ChatGPT, Claude, Copilot, or others to us all more productive programmers.  However, the workflow has a lot of jank&trade; doesn't it?  This little program tries to smooth the experience for all of us.

## Problem 1: Code Sections Missing in the chat
I hate it when we are writing code with ChatGPT or the Claude Artifacts and suddently we get the annoying

```
// Code remains the same
```
Suddenly we have either **beg** or __threaten__ the LLM to give us the full code `or else I'll lose my job!`.  This takes extra time and money and is not ideal; I like to code in a relaxed way and this sortof kills my vibe.  

Alternatively, we are manually copy-pasting blocks of code inside our several hundred line programs.  This breaks me out of the higher-level conversational state I was in when talking with the LLM, and now I am stuck in syntax hell as I jump around the file trying to make sure I didn't drop an import or miss a couple lines of code.  It honestly kills the magic of these LLMs and makes me feel like a junior dev again.

On the plus side, these comments make the LLM's responses faster and keeps the context windows smaller, thus keeping the accuracy high and costs lower.

So lets embrace the comments and solve this with a little tooling.  The solution:
```bash
# First, copy the new code to the clipboard (with the // Code remains the same blocks)
lfg paste ./dope_new_program.py
```
This will paste the new code into your file, and will try to keep as much of the old code as it can

Also if you copied the new code already into your file in your IDE, you and just run
```bash
lfg merge
```
This looks at `git diff` and reverts all code blocks where good code was replace with these ```// Code Was Here``` blocks


## Other Problems?
I'd love to know about them!  Raise an issue or DM me [@seankruzel](https://x.com/seankruzel)
Let's go make the Chat Assisted Programming experience better!


## So why is this needed?

Using Language Models to write code is pretty effective, but ultimately it not quite the right tool for the job. 
Since these models don't think about code the same way we do, or even the same way computers view code,

Take this python code example:
```python
TODO write a small two-function multi-step example with a loop 
```

If you're like me, you might read this code and view it in a functional way:

TODO insert flow chart

If you are the python compiler you might view it as an Abstract Syntax Tree

TODO insert tree viz

However if you are a language model, you view it as a linear set of tokens where every couple of characters is replaced by a different integer and stored as an array of numbers

TODO insert a token visualization of the code

So as a result we can have a lot of information lost in translation if we intuitively understand the task as a **Graph** and have to communicate it in words that are translated into an **Array** which are then copy-pasted into python code to be compiled into a **Tree**.  It's all quite messy.

In reality when we write code, we incrementally build out functionality so that the code slowly matches our mental model and implements the functions we desire.  
The compiler views our progress as us jumping around the AST and modifying edges, adding / removing nodes etc.

However there is another program on your computer that sees the world in a similar way to the LLM:  **`git`**

### Version Control to the Rescue
`git` and other version control systems just see line changes, they do not see syntax trees and so we can observe local changes to the file.  `git diff` just shows us what changed locally and we can reason whether we wanted to delete the code, or whether the code was omited for brevity by the LLM.

For now `lfg paste` and `lfg merge` are wrappers around this `git diff` view into the code to help us better manage the coding experience

## Other Projects

LFG is a sister project of (`autocomplete.sh`)[https://autocomplete.sh].  Definately check it out if you are new to linux and are learning the magic of the Terminal or if you are a DevOps professional and want to use `--help` less and get `more` done.

## License
(MIT License)[./LICENSE] - ClosedLoop Technologies, Copyright 2024 - All rights reserved
