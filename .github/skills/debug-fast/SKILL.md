---
name: debug-fast
description: "Use when debugging a failing run, especially when a syntax error or small configuration issue is blocking execution and you need a fast triage path before deeper analysis."
---

# Debug Fast

Use this skill when a task is blocked by an error and the first instinct is to overthink the problem instead of checking the obvious failure point.

## Goal

Resolve blockers quickly by identifying the smallest likely root cause first, especially when the issue is a syntax error, import problem, bad config, or simple typo.

## Workflow

1. Reproduce the problem
   - Run the smallest command or test that shows the failure.
   - Capture the exact error line, file, and message.

2. Check the simplest failure first
   - If the error is a syntax error, parse error, or broken import, stop and fix that before continuing.
   - Do not jump into architecture or logic debugging until the file is valid.

3. Isolate the failing file or step
   - Identify the narrowest scope: one file, one function, one command, or one config section.
   - Avoid changing multiple areas at once.

4. Fix one root cause at a time
   - Prefer the minimal change that addresses the reported error.
   - Re-test immediately after each change.

5. Verify before expanding scope
   - Re-run the minimal reproduction.
   - Only then continue to deeper debugging if the error persists.

6. Escalate only if necessary
   - If the issue is not obvious after a quick pass, summarize the evidence and move to a broader investigation.

## Priority rules

- Syntax errors and broken imports come first.
- Missing quotes, braces, commas, indentation, or bad references are often the true blocker.
- A simple typo can freeze the whole flow; check it before assuming a larger bug.
- Prefer fast validation over speculative fixes.

## Quality checklist

Before finishing, confirm that:
- the actual error was reproduced,
- the most obvious root cause was checked first,
- the fix was minimal and targeted,
- and the issue was verified with a fresh run.

## Suggested prompt

Use this prompt with the skill:

"Depura esto rápido, prioriza errores de sintaxis o bloqueos simples, identifica la causa más probable y verifica el fix con el menor comando posible."
