# Take-Home Exercise: Call Grading System

**Role:** Junior AI Engineer, Confie AI Engineering
**Time cap: 4 hours.** We mean it. We evaluate judgment per hour, not volume. Tell us where you stopped and what you would do next.
**AI tools:** Fully allowed and expected (Claude, Copilot, Cursor, whatever you use). We care about what you build and whether you can defend it, not how you typed it.

## Context

Our QA team listens to recorded sales and service calls (auto insurance) and grades each call against a rubric. Humans can only review a sample. Your job is to prototype an automated grader and, more importantly, to measure whether it can be trusted.

## What you get

- `transcripts/` : 30 synthetic call transcripts (`C001.txt` to `C030.txt`). Calls are in Spanish, English, or a mix. All data is synthetic, no real customers.
- `rubric.md` : 5 grading criteria, each scored 0, 5, or 10.
- `labels.csv` : human grades for calls C001 to C015 (the calibration set). C016 to C030 are unlabeled.

## What you build

1. **A grader.** Given a transcript, output a score (0/5/10) per criterion plus a one-line justification per criterion, as structured JSON. Any model/provider is fine; if you need an API key for a paid provider, use a free tier or mock the calls and say so.
2. **An evaluation.** Measure agreement between your grader and the human labels on C001 to C015. Choose and justify your metric(s). Exact-match per criterion, off-by-one tolerance, weighted agreement, whatever you can defend.
3. **A findings note (half a page, max one).** Where does your grader disagree with the humans? Which disagreements are your grader's fault, and which are not? Be specific, cite call IDs.

## Deliverable

A repo (GitHub link or zip) containing:

- Source code
- One-command run: `docker compose up` or a `make run` / single script that grades all 30 calls and prints the evaluation. A README with exact steps is acceptable if Docker is overkill for your setup.
- `results/grades.json` : your grader's output for all 30 calls
- `FINDINGS.md` : your half-page note
- A short note on what you would build next with one more day

## What happens after

A 30-minute live session where we review your work together and modify it in real time. You will run your own code on your own machine. No trick questions, but we will change something and ask you to adapt it.

## What we actually evaluate

In order of weight:

1. Your evaluation design and your findings. Can you tell us when the grader should NOT be trusted?
2. How you handle disagreement with the human labels.
3. The live session.
4. Code quality proportionate to a 4-hour prototype. Clean beats clever.

We do not evaluate: UI polish, exhaustive test coverage, prompt secrecy, or agreement percentage as a number by itself. A 95% agreement with no analysis loses to 80% with a sharp explanation of the 20%.

## Rules

- Do not spend more than 4 hours. Note your actual time in the README, honesty costs nothing.
- Do not use real customer data from any current or former employer.
- Questions during the exercise are welcome and cost you nothing: email them.
