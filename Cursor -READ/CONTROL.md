# CONTROL.md

Cursor, you must obey this file at all times.

You are required to:
1. **Read CONTROL.md, context.md, and DECISIONS.md at the start of every session.**
2. **Summarize the last 3–5 entries from DECISIONS.md** aloud before proposing anything new.
3. **Check context.md** before guessing project details.
4. **Append to DECISIONS.md** every time an issue is resolved or a choice is made.
5. **Use the correct date.** Always print today’s date in `YYYY-MM-DD` format and wait for my confirmation before logging.
6. **Follow all Commandments (below).**

---

## SECTION 1: COMMANDMENTS (rules.md)

1. **Read the docs.** Quote relevant sections before suggesting commands.
2. **Do not spin in circles.** If an attempt fails, explain *why* and wait.
3. **Output commands cleanly.** Show terminal commands only, in code blocks.
4. **Verify before improvising.** Summarize the plan in one sentence, wait for approval.
5. **Apologize only once.** Then move forward.
6. **Assume minimal context.** Restate what you know before guessing.
7. **Keep logs short.** Show only relevant output unless asked otherwise.
8. **Stop at errors.** Don’t blindly rerun variants.
9. **Confirm success criteria.** Define “what success looks like” before running.
10. **Follow my lead.** Drop ideas I reject; don’t sneak them back later.
11. **Do not delegate what you can do faster.** Run/fetch trivial tasks yourself.

---

## SECTION 2: LOGGING RULES (DECISIONS.md)

- **Autologging required:** After each resolved issue or decision, propose a new entry for DECISIONS.md and wait for approval. Then append.
- **Date rule:** Always print today’s date (YYYY-MM-DD) and wait for my confirmation before logging.
- **Never overwrite.** Only append new entries. Preserve history.

### Entry Template
```markdown
## YYYY-MM-DD
**Issue:** [short description]
**Decision:** [what was done/decided]
**Status:** [Success / Pending / Blocked]
```

---

## SECTION 3: CONTEXT (context.md)

Cursor must consult `context.md` before making assumptions. Keep it current.

# Project Context

Project: Prep101 (Child Actor 101)  
Goal: Convert PDF sides + metadata (role, genre, type, etc.) into a styled HTML audition prep guide email.

## Pipelines
- Airtable → (record with PDF + fields) → n8n worker → OpenAI Assistant → HTML guide → Gmail/Airtable Automations.

## Constraints
- HTML-only emails, inlined styles; no external CSS.
- Guides must include Uta Hagen 9Q + genre-aware sections (comedy beats, etc.).
- Depth must match "Henry" example.

## Open Issues (update daily)
- [ ] Retry policy for Assistant timeouts
- [ ] HTML template unit tests (schema & critical sections)

---

# Current Implementation Context (2025-01-27)
**Note: Current codebase differs from intended architecture**

## What's Actually Built
- React frontend (not Next.js 14)
- Express.js backend with PostgreSQL (not Airtable + Supabase)
- Direct PDF processing with OCR (not n8n worker pipeline)
- Web-based guide generation and viewing (not email-only output)
- User authentication and account management system
- Guide storage and retrieval from database

## Key Components Working
- PDF upload and text extraction
- Guide generation with RAG methodology
- User authentication and authorization
- Guide persistence in PostgreSQL
- Account management interface

## Recent Fixes Applied
- Fixed authentication token passing in FileUpload
- Resolved guide database saving issues
- Updated Account page to show real guides
- Enhanced error handling and user feedback

## Architecture Decision Needed
- Migrate to intended Next.js + Airtable architecture?
- Or update project rules to reflect current working implementation?
- Current system is functional but doesn't match documented architecture


### Legacy environment notes (confirm/adjust)
- Node: v18 (confirm)
- NPM: v9 (confirm)
- Environment files (confirm paths):
  - /prep101/prep101-app/prep101-backend/server/.env
  - /prep101/prep101-app/prep101-backend/.env
  - /prep101/prep101-app/prep101-backend/client/.env
- Hosting: Netlify SPA redirects (legacy). Current: React+Express stack with PostgreSQL (confirm).

### Known resolution to reference
- ECONNRESET during npm install → solved previously by pinning Node v18 + NPM v9 (legacy build path).

---

## SECTION 4: EMERGENCY BRAKES

- **Spiral reset:** `STOP. Summarize plan in one sentence. Wait for my approval.`
- **Doc reminder:** `Check CONTROL.md, DECISIONS.md, and context.md. Don’t repeat solved issues.`
- **Lazy delegation check:** `Run it yourself. Do not hand back trivial steps.`
