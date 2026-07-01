# Creative Ops Project — Learnings Log

## What We're Building
A Creative Approval tool — an AI-assisted system that approves or rejects display ad creatives (300x250) against brand policy guidelines. Replaces a manual 1-week review process at a publisher. Part of a larger Creative Ops platform (MVP = approval only).

---

## Architecture Learnings

### 1. AI Systems Are Fundamentally Different From Regular Apps
A regular app has deterministic behavior — define inputs, build logic, ship. An AI system has probabilistic behavior. You have to think about:
- What happens when the AI is wrong?
- How wrong, how often, in what direction?
- Who is accountable for each decision?
- How do you even know if it's working?

That's why you need guardrails, evals, observability, confidence thresholds, hard stops, and feedback loops — none of which exist in a normal product.

### 2. The Harness Pattern
The harness is the orchestration spine that connects every component. It doesn't do the work — it coordinates who does what, in what order, with what inputs, and catches failures.

**Four jobs of a harness:**
- **Receive** — accept input, validate, route to the right pipeline
- **Execute** — call each component in sequence, pass outputs as inputs
- **Decide** — apply confidence logic and routing rules
- **Record** — log every step for observability and evals

### 3. Two LLM Calls Are Better Than One (Then We Removed One)
Originally designed with two LLM calls:
- **LLM Call #1** — Extraction: "What is in this creative?" Returns structured JSON only, no judgment
- **LLM Call #2** — Policy Reasoning: "Does this meet guidelines?"

**Then we removed LLM Call #2.** Every meaningful failure mode ("misleading creative") reduces to a deterministic rule — wrong brand, wrong image, wrong category. If all rules pass, the creative is fine. Adding an LLM judgment layer introduced cost and latency with no additional signal.

**Key lesson:** Knowing when NOT to use AI is as important as knowing when to use it.

### 4. Hard Stops vs Soft Rules
Not all rule failures are equal. This distinction is critical:

**Hard stops** — binary, deterministic, no AI override possible:
- Logo not detected → hard reject
- Restricted category detected → hard reject
- Wrong file dimensions → reject before pipeline even starts
- Competitor brand detected → hard reject

**Soft rules** — failure adds to score, routes to human review:
- Urgency/pricing language detected → flag + score penalty
- Safe zone violation → flag + score penalty
- Content risk (pixelation, distortion) → flag + score penalty

### 5. Rules Config File > Guidelines Doc
Originally planned to have an LLM read a brand guidelines document. Evolved to a structured `rules.json` config file that the rules engine reads at runtime.

**Why this is better:**
- Rules live outside the code — no code changes when policy updates
- Versioned and auditable — rules file has a version number, harness logs which version ran
- Cheaper — no LLM needed to interpret a doc, deterministic checks only
- Portable — any publisher can provide their own rules file

```json
{
  "version": "1.2",
  "hard_stops": [
    {"rule": "no_black_border", "check": "border_color != black"},
    {"rule": "logo_present", "check": "logo_detected == true"}
  ],
  "soft_rules": [
    {"rule": "no_urgency_language", "check": "urgency_detected == false"}
  ]
}
```

---

## Product Thinking Learnings

### 6. Guardrails vs Failure Modes vs Routing Logic — They Are Not The Same Thing

| Concept | Definition | Example |
|---|---|---|
| Guardrail | A constraint on what AI is never allowed to do | Never auto-approve if logo missing, regardless of confidence |
| Failure mode | Something that can go wrong in the system | File upload times out |
| Routing logic | What path to take based on scores | If confidence <95% → human review |

Test: "Could this go wrong even without AI?" → Yes = failure mode. Only exists because AI is making a judgment → guardrail.

### 7. Observability Is Not Just Logging
Three distinct types:
- **System observability** — is the pipeline running? Latency, error rates, API failures
- **Model/AI observability** — is the model reasoning correctly? Consistency, confidence calibration
- **Product/business observability** — is it delivering value? Reviewer override rate, time-to-decision, adoption

Most PMs only build the third. Signal is that you designed all three intentionally.

### 8. Every Metric Needs an Action
Before defining any metric, ask: "If this metric does X, what do I do?" If you can't answer that, it's a vanity metric. Metrics that don't trigger decisions just create noise.

### 9. The Primary User Question
Every PRD must answer "who is this for" before anything else. Having five personas is not the same as having a primary user. For this product: **LG HQ** is the primary user. Everything else — the UI, the confidence threshold, the review queue — was designed around their workflow.

### 10. Definition of Done Must Be Measurable
"Workflow works end to end" is not a definition of done. Correct format:
> The MVP is done when [persona] can [action] and the system produces [measurable outcome] with [threshold] accuracy, reviewed by [who], within [time].

---

## Technical Learnings

### 11. Streamlit vs Lovable vs Replit
- **Lovable** — great for pure frontend/React. Wrong tool when you have a Python backend with LLM calls and file processing
- **Replit** — a cloud IDE, not a framework. Doesn't help you decide what to build
- **Streamlit** — Python-native. UI and backend live in the same language and file. Right choice for AI/data tools

### 12. Claude Code Is Not Connected to Your App
Claude Code writes code files. Streamlit runs those files. They don't talk to each other at runtime.

```
You describe what you want
      ↓
Claude Code writes app.py
      ↓
You run: streamlit run app.py
      ↓
Streamlit reads app.py and serves it in browser
```

Claude Code's job ends when it writes the file.

### 13. MCP Is Not How App Components Talk to Each Other
MCP (Model Context Protocol) is how Claude connects to external tools like Notion, Excalidraw, Google Drive. Your app components connect to each other through normal Python function calls. Nothing more.

### 14. Git = Checkpointing
Every time something works, commit it. If you break something later, you can rewind to the last working state instead of manually undoing changes and guessing.

```bash
git init
git add .
git commit -m "feat: input layer complete"
```

### 15. Pillow Is For Image Processing
Pillow is a Python library for reading and manipulating images. Used here to check uploaded image dimensions (is this actually 300x250?) before it enters the pipeline.

---

## Design Decisions Made

| Decision | Rationale |
|---|---|
| Remove LLM Call #2 | Every failure mode is expressible as a deterministic rule. No LLM judgment adds signal |
| Rules config file over guidelines doc | Versioned, auditable, cheaper, no code changes needed for policy updates |
| 95% confidence threshold for auto-approve | False approvals on premium inventory carry brand-safety risk. Precision over recall |
| HITL always in loop for MVP | Build trust with LG HQ before removing them. Zero false positives is the bar |
| Streamlit for MVP UI | Python-native, fastest path to working product, deploy to Streamlit Cloud in one command |
| Email field kept in form | Audit trail tied to submitter — every submission traceable to a person |
| JPG/PNG only | Scoped for MVP. GIF/HTML deferred |

---

## What's Built

- [x] Streamlit upload UI — file upload, validation (150KB, 300x250, JPG/PNG), metadata form, success state
- [x] PRD in Notion — business problem, personas, system design, guardrails, observability, eval framework, definition of done
- [x] Excalidraw system design — four-lane harness diagram with observability layer

## What's Next

- [ ] Update PRD to reflect removal of LLM Call #2 and rules config file decision
- [ ] Update Excalidraw diagram to reflect simplified architecture
- [ ] Build harness.py — orchestration spine with logging
- [ ] Build extraction.py — LLM Call #1, structured JSON output
- [ ] Build rules.py + rules.json — deterministic checks
- [ ] Build score aggregator + router
- [ ] Build reviewer UI
- [ ] Build eval store
