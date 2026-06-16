#!/usr/bin/env bash
# =============================================================================
# organize_repo.sh
# Reorganises the flat medication-companion files into the correct repo structure.
#
# Run from the repo root:
#   cd ~/dev/github/medication-companion
#   bash organize_repo.sh
#
# Safe to review before running — it only moves/creates, never deletes.
# After running, verify with: find . -type f | sort
# =============================================================================
set -euo pipefail

REPO_ROOT="$(pwd)"
echo "▶ Organising repo at: $REPO_ROOT"
echo ""

# ── 1. Create all directories ─────────────────────────────────────────────────
echo "▶ Creating directory structure..."

mkdir -p backend/agents
mkdir -p backend/tools
mkdir -p backend/memory
mkdir -p backend/evaluation
mkdir -p backend/tests
mkdir -p deploy
mkdir -p scripts
mkdir -p .cursor/rules
mkdir -p .github/workflows
mkdir -p .github/ISSUE_TEMPLATE
mkdir -p docs
mkdir -p data
mkdir -p notebooks
mkdir -p frontend/lib/auth
mkdir -p frontend/lib/screens
mkdir -p frontend/lib/services
mkdir -p frontend/lib/models
mkdir -p frontend/web

echo "  ✓ Directories created"
echo ""

# ── 2. Move files into correct locations ──────────────────────────────────────
echo "▶ Moving files..."

move_file() {
  local SRC="$1"
  local DEST="$2"
  if [[ -f "$SRC" ]]; then
    mv "$SRC" "$DEST"
    echo "  ✓ $SRC → $DEST"
  else
    echo "  ⚠ SKIPPED (not found): $SRC"
  fi
}

# Root-level files
move_file "README.md"              "README.md"          # already in root, no-op needed
move_file "AGENTS.md"              "AGENTS.md"

# Backend — agents
move_file "agent1_reader.py"       "backend/agents/agent1_reader.py"
move_file "agent2_resolver.py"     "backend/agents/agent2_resolver.py"
move_file "agent3_safety.py"       "backend/agents/agent3_safety.py"
move_file "agent4_education.py"    "backend/agents/agent4_education.py"

# Backend — top-level
move_file "main.py"                "backend/main.py"
move_file "a2a_server.py"          "backend/a2a_server.py"

# Backend — tools
move_file "guardrails.py"          "backend/tools/guardrails.py"

# Backend — evaluation
move_file "llm_judge.py"           "backend/evaluation/llm_judge.py"

# Deploy
move_file "deploy.sh"              "deploy/deploy.sh"

# Scripts
move_file "setup_gcp.sh"           "scripts/setup_gcp.sh"

# Cursor rules
move_file "medication-companion.mdc" ".cursor/rules/medication-companion.mdc"

# GitHub Actions workflows
move_file "ci.yml"                 ".github/workflows/ci.yml"
move_file "deploy.yml"             ".github/workflows/deploy.yml"

# Docs — move any files already in a docs/ subfolder too
move_file "architecture.md"        "docs/architecture.md"
move_file "out_of_scope.md"        "docs/out_of_scope.md"

echo ""

# ── 3. Move anything already inside docs/ if it landed there ─────────────────
# (handles the case where docs/ already existed with files inside)
if [[ -f "docs/architecture.md" ]] && [[ ! -f "docs/architecture.md" ]]; then
  : # already handled above
fi

# ── 4. Make shell scripts executable ─────────────────────────────────────────
echo "▶ Setting execute permissions on shell scripts..."
[[ -f "deploy/deploy.sh"        ]] && chmod +x deploy/deploy.sh        && echo "  ✓ deploy/deploy.sh"
[[ -f "scripts/setup_gcp.sh"    ]] && chmod +x scripts/setup_gcp.sh    && echo "  ✓ scripts/setup_gcp.sh"
[[ -f "scripts/teardown_gcp.sh" ]] && chmod +x scripts/teardown_gcp.sh && echo "  ✓ scripts/teardown_gcp.sh"

echo ""

# ── 5. Create placeholder __init__.py files for Python packages ───────────────
echo "▶ Creating Python package __init__.py files..."

for PKG in backend backend/agents backend/tools backend/memory backend/evaluation backend/tests; do
  INIT="$PKG/__init__.py"
  if [[ ! -f "$INIT" ]]; then
    touch "$INIT"
    echo "  ✓ $INIT"
  fi
done

echo ""

# ── 6. Create stub placeholder files for things not yet built ────────────────
echo "▶ Creating stub files for components not yet implemented..."

create_stub() {
  local FILE="$1"
  local COMMENT="$2"
  if [[ ! -f "$FILE" ]]; then
    echo "# TODO: $COMMENT" > "$FILE"
    echo "  ✓ stub: $FILE"
  else
    echo "  – exists: $FILE (skipped)"
  fi
}

seed_india_brands_csv() {
  local FILE="data/india_brands.csv"
  if [[ -f "$FILE" ]]; then
    echo "  – exists: $FILE (skipped)"
    return
  fi
  cat > "$FILE" << 'EOF'
brand_name,generic_name,components,drug_class
Azee,azithromycin,,Antibiotic/Macrolide
Augmentin,amoxicillin+clavulanate,amoxicillin 500mg|clavulanate 125mg,Antibiotic/Penicillin+BLI
Pantocid DSR,pantoprazole+domperidone,pantoprazole 40mg|domperidone 10mg,PPI+Prokinetic
Combiflam,ibuprofen+paracetamol,ibuprofen 400mg|paracetamol 325mg,NSAID+Analgesic
Cheston Cold,cetirizine+paracetamol+pseudoephedrine,cetirizine 5mg|paracetamol 500mg|pseudoephedrine 30mg,Antihistamine+Analgesic+Decongestant
Akurit 4,isoniazid+rifampicin+pyrazinamide+ethambutol,isoniazid 75mg|rifampicin 150mg|pyrazinamide 400mg|ethambutol 275mg,Antitubercular FDC
Glycomet,metformin,,Antidiabetic/Biguanide
Ecosprin,aspirin,,Antiplatelet
Deplatt,clopidogrel,,Antiplatelet
EOF
  echo "  ✓ seed: $FILE (minimal test data)"
}

# Backend stubs
create_stub "backend/tools/drug_lookup.py"     "FunctionTool: RxNav API + India CSV brand→generic lookup"
create_stub "backend/tools/combo_splitter.py"  "FunctionTool: split fixed-dose combination drugs"
create_stub "backend/tools/tts.py"             "FunctionTool: GCP Text-to-Speech → GCS MP3"
create_stub "backend/memory/session_service.py"  "VertexAiSessionService / InMemorySessionService factory"
create_stub "backend/memory/memory_service.py"   "VertexAiMemoryBankService / InMemoryMemoryService factory"
create_stub "backend/agents/agent5_localisation.py" "Agent 5: Localisation + Audio (used by a2a_server.py)"
create_stub "backend/requirements.txt"         "Python dependencies — fill in"
create_stub "backend/Dockerfile"               "Main service Dockerfile"
create_stub "backend/Dockerfile.a2a"           "Agent 5 A2A service Dockerfile"

# Data stubs
seed_india_brands_csv

# Teardown stub
create_stub "scripts/teardown_gcp.sh"          "Remove all GCP resources created by setup_gcp.sh"

# Frontend stubs
create_stub "frontend/lib/main.dart"           "Flutter app entry point"
create_stub "frontend/pubspec.yaml"            "Flutter dependencies"
create_stub "frontend/web/index.html"          "PWA manifest + service worker"

# OSS files
create_stub "CONTRIBUTING.md"                  "Contributor guide"
create_stub "SECURITY.md"                      "Security policy"
create_stub "CODE_OF_CONDUCT.md"               "Contributor Covenant"
create_stub "LICENSE"                          "MIT License"
create_stub ".env.example"                     "All required env vars with safe placeholder values"
create_stub ".gitignore"                       "Python, Flutter, GCP, secrets"

# Notebook stub
create_stub "notebooks/medication_companion_demo.ipynb" "Kaggle submission notebook (InMemorySessionService)"

# Deploy stub
create_stub "deploy/firestore.rules"           "Firestore security rules"

echo ""

# ── 7. Final summary ──────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  Done. Final repo structure:                             ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
find . -not -path './.git/*' -type f | sort
echo ""
echo "Next steps:"
echo "  git add ."
echo "  git status   # review before committing"
