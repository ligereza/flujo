# Skill: Verify User Intent First

**Problem**: Implemented two features (`plano_demo.html`, `svg_visualizer.html`) based on incorrect assumptions about user requirements, treating an NGO (Reduciendo Daño) as an event organizer rather than an intervention provider.

**Root Cause**: 
- Read the brief superficially without verifying my interpretation
- Assumed "RD planning an event" → detailed volunteer role management
- Missed key signal: "brief says RD is an ONG" (NGO/non-profit intervention provider)
- Did NOT ask clarifying questions before implementing

**The Error**:
```
WRONG: Modeled RD as event planner with detailed role breakdowns (coordinators, educators, analysts counted by role)
RIGHT: RD is an NGO that sets up intervention stands (educational info, chemical testing, psychological support) 
       WITHIN external organizations' events
```

**User Correction Signal**: 
> "malinterpretaste totalmente el brief. Es rd una fiesta?"
(You totally misunderstood the brief. Is RD a party?)

**Solution Applied**:
1. Reverted to original code structure from `plano_demo_old.html` and `svg_visualizer_old.html`
2. Reinterpreted for correct RD model:
   - Stand Informativo (educational materials, prevention)
   - Stand Testeo (chemical analysis, if selected)
   - Zona Contención (low-stimulation support, if selected)
3. Simplified UI: checkboxes for services instead of detailed role counts
4. Updated rider/costs to reflect RD intervention pricing, not volunteer management

**Lesson Learned**:
- **Always verify user intent before heavy implementation**
- When brief is brief, ask clarifying questions:
  - "Is this organization [planning/participating in] events?"
  - "What's their primary role/function?"
  - "Can you describe a typical workflow?"
- Don't assume from partial context
- Read metadata carefully: "ONG" = non-profit intervention, not commercial event producer

**When to Use This Skill**:
- Multi-file implementations based on user requirements
- Building tools for unfamiliar domains (NGOs, services, workflows)
- Ambiguous briefs or domain-specific terminology
- Before generating UI/architecture from assumptions

**Prevention Checklist**:
- [ ] Is my interpretation explicit in the requirements?
- [ ] Did I ask 1-2 clarifying questions if brief is vague?
- [ ] Did I identify the user's role/context (NGO vs. company vs. individual)?
- [ ] Do my assumptions match stated facts in the brief?
- [ ] Could I explain my interpretation back to the user accurately?

**Token Cost of Error**: ~85K tokens (full implementation + redo)
**Prevention Cost**: ~5K tokens (clarifying questions before implementation)

**Ratio**: 17:1 — Always verify intent first.
