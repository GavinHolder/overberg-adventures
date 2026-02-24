<!-- AI Engineer Toolkit -->

# overberg adventures - Claude Code Guide

**Generated:** 2026-02-24 08:40:49 UTC | **Toolkit:** AI Engineer by GavinHolder
**Max size:** Keep this file under 40,000 characters. Move details to `.claude/memory/` files.

---

## Communication Rules

- **No fluff.** No "Great question", "Good job", "Sure thing", or filler phrases. Get straight to work.
- **No summaries unless asked.** Do not summarize what you just did after completing a task. The user can see the output. Only summarize if the user explicitly asks.
- **Optimize token usage.** Every token costs money. Be concise. Say what's needed, nothing more.
- **No unnecessary confirmations.** Don't say "I'll do X" then do X. Just do X.
- **Speak through actions.** Let your code, edits, and tool calls be the response. Text is for decisions, questions, and blockers only.

---

## Non-Negotiable Rules

These apply to EVERY session, EVERY task. No exceptions.

1. **Tasks for everything.** Create a task list BEFORE writing any code. Every task gets subtasks if multi-step.
2. **Never skip steps.** Mark tasks in_progress before starting, completed when done. Remaining tasks stay in queue untouched.
3. **Debug tasks for bugs.** When something breaks mid-step, create a `debug` child task. Fix in place, resume parent. Do NOT skip ahead.
4. **Amendment tasks for revisions.** When a completed step needs changes, create an `amend` task. Do NOT redo the entire step.
5. **Checkpoints every 5-10 tasks.** Pause, update session files, extract learnings, report summary.
6. **Learn after every task list.** After completing a set of tasks, extract non-obvious knowledge to the relevant skill's `learned/` folder. One topic per file, max 30 lines each. No monolithic learning files.
7. **Verify before claiming done.** Run tests, check output, confirm visually if UI work.
8. **Visual debugging for UI.** Use Playwright (`visual-debugging` skill) to screenshot and inspect when code-level debugging isn't enough.

---

## Session Protocol

### Start
1. Read `.claude/memory/SESSION_CONTEXT.md` (active tasks)
2. Read `.claude/memory/SESSION_CHANGELOG.md` (last session)
3. Scan `learned/` folders in relevant skills for recent learnings
4. Resume from "Next Action" or create new task list

### During Work
- Log progress in `SESSION_CONTEXT.md`
- At checkpoints: update changelog, extract learnings, report to user

### End
- Update `SESSION_CONTEXT.md` with next action
- Log session summary in `SESSION_CHANGELOG.md`
- Extract any remaining learnings

---

## Task Protocol

### Hierarchy (5 levels max)
```
1. Main Task
   1.1 Subtask
       1.1.1 Sub-subtask
```

### Task Types
```
[>] IN PROGRESS    [x] COMPLETE       [ ] NOT STARTED
[D] DEBUG          [A] AMENDMENT      [!] DEVIATION
[-] BLOCKED        [X] FAILED         [#] CHECKPOINT
```

### Debug Tasks (fix bugs without losing the plan)
```
1.1 Create layout [IN PROGRESS]
1.1.debug.a: Grid not rendering
    1.1.debug.a.1 Investigate
    1.1.debug.a.2 Fix
1.1 [RESUMED]
1.2 Add widgets (NEXT - unchanged)
```

### Amendment Tasks (revise completed steps)
```
1.2 Create POST /users [COMPLETE]
1.2.amend.a: Add email validation
    1.2.amend.a.1 Add logic
    1.2.amend.a.2 Update tests
1.3 Create DELETE /users (NEXT - unchanged)
```

Full protocol: `.claude/memory/TASK_PROTOCOL.md`

---

## Risk Classification

| Level | Risk | Workflow |
|-------|------|----------|
| **4 CRITICAL** | Data, security, money | Plan -> Adversarial review -> TDD -> Security review -> Code review |
| **3 HIGH** | Breaking changes, integrations | Plan -> Adversarial review -> TDD -> Code review |
| **2 MEDIUM** | Standard features | Plan -> Code -> Code review |
| **1 LOW** | Docs, tests, formatting | Code -> Optional review |

---

## Continuous Learning

Knowledge is stored as **individual files** in each skill's `learned/` folder:
```
~/.claude/skills/react-19/learned/hook-ordering-strict-mode.md
~/.claude/skills/bootstrap-5/learned/modal-z-index-conflict.md
```

- One topic per file, max 30 lines, kebab-case filenames
- Only extract non-obvious, reusable, verified knowledge
- See `continuous-learning` skill for full workflow

---

## Development Workflow

0. **Create tasks** - Always first
1. **Classify risk** (1-4)
2. **Plan** - `/brainstorming` or `/writing-plans` for Level 2+
3. **Visual reference** - `/playground` or `visual-debugging` for UI work
4. **Test first** - TDD for Level 2+
5. **Implement** - Create debug/amendment tasks for issues
6. **Verify** - Tests, lint, typecheck
7. **Review** - `/requesting-code-review` for Level 2+
8. **Learn** - Extract patterns to skill learned/ folders

### Code Style
- Max 500 lines/file, 20 lines/function, 3 params, 2 nesting levels
- No dead code, no magic numbers, no silent failures

### Deployment
Docker + Portainer + Traefik. Each app is its own stack.

---

## Skill Quick Reference

### Workflow
```
/brainstorming            /writing-plans           /test-driven-development
/systematic-debugging     /verification-before-completion
/requesting-code-review   /revise-claude-md
```

### Frontend
```
/frontend-design          /frontend-aesthetics     /bootstrap-5
/playground               /web-artifacts-builder   visual-debugging
```

### Development
```
/feature-dev              /Django Framework
/claude-bootstrap-base    /claude-bootstrap-react-web
```

---

## CLAUDE.md Size Management

This file MUST stay under 40,000 characters. If it grows too large:
1. Move verbose content to `.claude/memory/` files
2. Keep only rules, quick references, and concise protocols here
3. Reference external files for full details
4. Run `/revise-claude-md` to audit and trim

---

**Generated by:** scripts/install-skills.py
