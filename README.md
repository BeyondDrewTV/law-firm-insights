# Clarion — Law Firm Insights Platform

## Repo Structure

```
law-firm-insights-main/
│
├─ backend/                     ← Flask API + scoring engine
│   ├─ app.py                   ← Main application
│   ├─ services/                ← Core business logic (benchmark, scoring, etc.)
│   ├─ routes/                  ← API route handlers
│   ├─ scripts/                 ← Backend admin scripts (backup, lifecycle emails)
│   └─ tests/                   ← Backend test suite
│
├─ frontend/                    ← React SPA
│   └─ src/
│
├─ Clarion-Agency/              ← AI Agent Office (autonomous agent runner)
│   ├─ run_clarion_agent_office.py
│   ├─ agents/
│   ├─ data/
│   ├─ memory/
│   └─ execution/               ← Autonomous execution layer (L1/L2/L3)
│
├─ automation/
│   └─ calibration/             ← Benchmark calibration workflow
│       └─ README.md            ← How to run calibration
│
├─ data/
│   └─ calibration/
│       ├─ inputs/              ← Source review CSVs
│       ├─ synthetic/           ← Generated synthetic reviews
│       └─ runs/                ← Timestamped calibration run outputs
│
├─ docs/
│   ├─ active/                  ← Current operational docs (deployment, ops playbook, etc.)
│   └─ reference/               ← Reference docs (calibration workflow, etc.)
│
├─ tools/                       ← One-off maintenance scripts
│   └─ README.md
│
├─ archive/                     ← Non-deletable historical artifacts
│   ├─ legacy_outputs/          ← Old JSON/PDF results
│   └─ legacy_scripts/          ← Retired scripts
│
├─ logs/                        ← App logs
│
├─ run_calibration_workflow.bat ← Windows double-click calibration launcher
└─ code-analysis-progress.md   ← Active working doc for multi-chat continuity
```

## Quick Start

### Backend
```bash
cd backend
python app.py
```

### Frontend
```bash
cd frontend
npm install && npm run dev
```

### Calibration Workflow
```
run_calibration_workflow.bat
# Or: python automation/calibration/run_calibration_workflow.py --csv data/calibration/inputs/real_reviews.csv
```

### Agent Office
```bash
cd Clarion-Agency
python run_clarion_agent_office.py
```

### Operator Launchers (Repo Root, Windows)
```
START_CLARION.bat       # Starts backend and opens command center
OPEN_COMMAND_CENTER.bat # Opens http://localhost:5000/dashboard only
RUN_CALIBRATION.bat     # Runs calibration workflow (venv312-aware)
OPEN_ENGINE_TOOLS.bat   # Opens http://localhost:5000/internal/tools/
```
