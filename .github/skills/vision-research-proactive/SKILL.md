---
name: vision-research-proactive
description: "Use when you need to find the shortest path to the real issue, avoid getting trapped in loops, and choose the most direct next step before solving the first visible problem."
---

# Shortest Path Reasoning

Use this skill when the task is being slowed down by reacting too quickly to the first visible symptom instead of identifying the fastest route to the real cause.

## Goal

Prioritize the most direct path to understanding and resolving the issue, while avoiding circular retries, premature fixes, and repeated dead ends.

## Workflow

1. Identify the real objective
   - Clarify what success actually means.
   - Separate the symptom from the underlying problem.

2. Find the shortest path to evidence
   - Look for the smallest check that can confirm or reject the most likely hypothesis.
   - Prefer a high-signal action over a broad or noisy investigation.

3. Decide whether delegation is the fastest route
   - If a part of the task is better handled by a specialized agent, consider creating or requesting a subagent.
   - If the user provides a clear prompt for another agent, use that as a direct handoff instead of trying to do everything in one pass.
   - Delegation is appropriate when it reduces friction, isolates context, or accelerates a parallel subtask.

4. Avoid premature resolution
   - Do not solve the first obvious problem unless it is clearly the root cause.
   - Question whether the current approach is creating a loop.

5. Break loops early
   - If the same hypothesis is being repeated without new evidence, stop and change strategy.
   - Recognize when the task is circling instead of progressing.

6. Choose the next best move
   - Select the single most informative next step.
   - Prefer the action that removes uncertainty fastest.

7. Verify before expanding scope
   - Confirm whether the chosen path actually moved the situation forward.
   - Only then continue to a broader or deeper investigation.

## Priority rules

- The shortest path is usually the one that tests the most likely root cause with the least effort.
- Do not get trapped in repeated attempts that add noise without evidence.
- If a path is not producing new information, abandon it quickly.
- Favor clarity and progress over reaction.
- When delegation is faster than doing everything yourself, create a subagent or hand off the work with a precise prompt.

## Quality checklist

Before finishing, confirm that:
- the real problem was separated from the visible symptom,
- the chosen path was the most direct available,
- the process avoided unnecessary loops,
- and the next step is clear and minimal.

## Suggested prompt

Use this prompt with the skill:

"Encuentra el camino más corto para resolver esto, evita caer en bucles, y considera crear un subagente o delegar a otro agente cuando eso acelere la resolución con un prompt claro."
