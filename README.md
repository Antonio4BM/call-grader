# Call Grader

## Overview

This project grades synthetic auto-insurance sales and service call transcripts against a five-criterion QA rubric. Each call may be in Spanish, English, or mixed language. Language does not affect scoring.

A LangChain pipeline retrieves the rubric, sends each transcript to an OpenRouter chat model, and returns a structured JSON grade: a score of **0**, **5**, or **10** per criterion plus a one-line justification. After grading, it compares results for calls **C001–C015** against human labels and writes agreement metrics.

The five criteria are:

1. Greeting and identification
2. Needs discovery
3. Compliance and disclosures
4. Resolution and next steps
5. Professionalism and call control

The total per call is **0–50**.

## Project structure

```text
├── app/
│   ├── main.py            # Load transcripts, grade them, dump results, evaluate
│   ├── pipeline.py        # LangChain retrieve-augment-generate chain
│   ├── models.py          # OpenRouter LLM client
│   ├── prompts.py         # System and human prompts
│   ├── documents.py       # Rubric retrieval into the prompt
│   ├── schemas.py         # Pydantic models for grades and the evaluation report
│   └── evaluation.py      # Agreement metrics vs labels.csv
├── data/
│   ├── transcripts/       # C001.txt … C030.txt
│   └── labels.csv         # Human grades for C001–C015
├── results/
│   ├── grades.json        # Grader output for all scored calls
│   └── report.json        # Accuracy report vs the calibration set
├── tests/                 # pytest coverage of evaluation helpers
├── rubric.md              # Scoring rules
├── FINDINGS.md            # Disagreement analysis vs human labels
├── docker-compose.yaml
├── Dockerfile
├── pytest.ini
└── requirements.txt
```

Python **3.12** is required. Dependencies are listed in `requirements.txt`.

## Usage

Set an OpenRouter API key before running. Optional variables override the model and retry count:

```bash
export OPENROUTER_API_KEY=your_key
export OPENROUTER_MODEL=openai/gpt-4o-mini          # default
export OPENROUTER_MAX_ATTEMPTS=6                     # default
```

You can put the same keys in a `.env` file at the repo root. Docker Compose reads that file.

### Docker (recommended)

```bash
docker compose up --build
```

The container runs `python -m app.main`, grades every transcript under `data/transcripts/`, and mounts `./results` so `grades.json` and `report.json` appear on the host.

### Local

```bash
python -m venv grader_env
source grader_env/bin/activate
pip install -r requirements.txt
python -m app.main
```

### What the run does

1. Reads `rubric.md` and builds a LangChain chain with structured `CallGrade` output.
2. Grades each `C*.txt` file in filename order. Transient OpenRouter errors (rate limits, overload, 5xx) are retried. Partial grades are written if a later call fails.
3. Writes `results/grades.json`.
4. Compares labeled calls **C001–C015** in `data/labels.csv` to those grades.
5. Prints and writes `results/report.json` with exact-match accuracy, within-one-level accuracy (one rubric step of 5 points), per-criterion rates, and disagreements.
