---
name: agent-handoff-context
description: "Use when you need to contextualizar rápido a un agente nuevo, revisar si el agente anterior quedó con procesos sin terminar y verificar si el repo tiene cambios sin subir a Git."
---

# Agent Handoff Context

Use this skill when you need to hand off work to another agent quickly and make sure nothing was left unfinished.

## Goal

Produce a concise, reliable context packet for the next agent covering:
- what was already done,
- what is still pending,
- whether the repository has uncommitted or unpushed changes,
- and what the next agent should do first.

## Workflow

1. Start from the project entry point
   - Prefer the main workspace entry described in the repo instructions, usually the app hub or the documented daily start command.
   - If the repo has a main handoff file, read it first.

2. Check the current state of the work
   - Review the latest notes, handoff documents, and pending task summaries.
   - Identify what was completed, what is partially done, and what remains blocked or unclear.

3. Detect unfinished processes
   - Look for open TODOs, incomplete commands, interrupted steps, failed validations, or pending follow-up items.
   - Call out anything that should not be assumed finished.

4. Verify repository status
   - Check whether there are local modifications, untracked files, or Git state that may affect the next agent.
   - Report clearly if changes exist but were not pushed yet.

5. Build the handoff summary
   - Write a short summary with:
     - Current status
     - Pending actions
     - Risks or blockers
     - Git status
     - Recommended next step for the incoming agent

## Quality checklist

Before finishing, confirm that the handoff includes:
- a clear current state,
- explicit pending items,
- any unfinished or risky processes,
- Git status and push status,
- and a concrete first action for the next agent.

## Suggested prompt

Use this prompt with the skill:

"Contextualiza rápido a un agente para continuar este trabajo, revisa si el anterior quedó con procesos sin terminar y verifica si el repo tiene cambios sin hacer push."
