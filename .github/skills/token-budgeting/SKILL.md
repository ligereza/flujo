---
name: token-budgeting
description: "Use when you need to manage work under a token budget, estimate progress against a threshold, and shift from exploration to concrete execution as the budget approaches the limit."
---

# Token Budgeting

Use this skill when the task should be guided by a token budget rather than by unlimited exploration.

## Goal

Help the agent behave efficiently by:
- estimating how much of the available budget has been used,
- recognizing when the work is at roughly 50% of the budget,
- and switching from experimentation to concrete execution before the budget reaches the danger zone.

## Core behavior

1. Start in exploration mode
   - In the first phase, the agent may experiment, gather context, try options, and test directions.
   - The goal is to learn fast, not to overcommit.

2. Monitor the budget carefully
   - If the user says the work is at about 50% of the token budget, the agent should interpret that as a transition point.
   - At that point, the agent should stop broad exploration and begin converging on the best path.

3. Shift to concrete execution after 50%
   - Once the budget is around 50%, the agent should favor:
     - shorter plans,
     - fewer experiments,
     - more direct implementation,
     - clearer decisions,
     - and faster validation.

4. Prepare for the 90% zone
   - When the work is approaching roughly 90% of the budget, the agent should assume the session is near its limit.
   - At that point, it should stop opening new branches of work and focus on finishing the most important deliverable.

5. Close decisively near the limit
   - Near 90%, the agent should prioritize:
     - finishing the current task,
     - summarizing what is done,
     - surfacing remaining blockers,
     - and avoiding new speculative work.

## Operating rules

- Early phase: explore and test.
- Around 50%: concretar and commit to one path.
- Around 90%: close, finish, and summarize.
- Do not burn the budget on low-value detours.
- Prefer the shortest path that produces a reliable result.

## Suggested prompt

Use this prompt with the skill:

"Gestiona este trabajo por presupuesto de tokens: empieza explorando, avisa cuando lleguemos al 50% para concretar, y cuando estemos cerca del 90% prioriza cerrar y entregar lo esencial."
