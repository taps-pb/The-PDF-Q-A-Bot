# Local setup

## Requirements

Python 3.12, uv, Ollama, and Tesseract with English language data. On macOS:

```sh
brew install uv python@3.12 ollama tesseract
```

Clone this repository, enter its root, and install the locked dependencies:

```sh
uv sync --locked --python python3.12
```

Model downloads need roughly 6 GB of disk space; leave additional room for dependencies, PDFs, and indexes. The verified development machine is an Apple M5 Pro with 24 GB memory. CPU-only machines will be slower.

## Start local inference

Run Ollama in a separate terminal. For this workspace, store weights outside the repository:

```sh
export OLLAMA_MODELS="$PWD/../data/models"
OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NO_CLOUD=1 ollama serve
```

For a different checkout, choose any local model directory outside Git, or omit OLLAMA_MODELS to use Ollama's default. If Ollama is already serving, use that instance only after confirming cloud features are disabled. Pull the models once:

```sh
ollama pull qwen3:8b
ollama pull qwen3-embedding:0.6b
ollama list
tesseract --list-langs
```

Both models must be available locally, and `eng` must appear in the language list. The application does not download models or install OCR automatically. After setup, inference and document processing need no external network connection.

## Start the app

From the repository root:

```sh
export PDF_QA_DATA_DIR="$PWD/../data/app"
uv run streamlit run app.py
```

Open http://127.0.0.1:8501. In other checkouts, set PDF_QA_DATA_DIR to your own private local directory. Without it, the app uses `data/` in the current working directory, which is ignored by Git. Uploaded PDF text and indexes persist there unencrypted; use an appropriate local account and filesystem permissions.

Upload a PDF, select automatic extraction or forced OCR, then build/load its index. You can reopen saved indexes after restarting. Questions do not rebuild document embeddings. Changing OCR mode or chunk size requires indexing that configuration once.

Automatic OCR applies to pages with fewer than 40 non-whitespace extracted characters. For pages that contain both native text and text within images, select forced OCR. Photos and diagrams without readable text are not interpreted. Citations use physical PDF page numbers, not the numbers printed in the document.

## Reproduce the evaluation

Download the public-domain handbook outside Git:

```sh
mkdir -p ../data
curl -fL https://stacks.cdc.gov/view/cdc/148137/cdc_148137_DS1.pdf -o ../data/osha-small-business.pdf
shasum -a 256 ../data/osha-small-business.pdf
```

Expected SHA-256: `afd26f4680071738e85730f398e4fa8d17b560aac042492938b9ec49fd7defa0`. It is the January 2024 OSHA/NIOSH Small Business Safety and Health Handbook, with 98 physical PDF pages. The reference questions are frozen in `evals/questions.json`.

Run unit tests with `uv run pytest`, lint with `uv run ruff check .`, and real local model/OCR checks with `uv run pytest -m integration`. Evaluation commands and grading details are in `docs/EVALUATION.md`.

## Workspace and skills

In the original workspace, the parent directory is not a Git repository. Only `code/` is tracked. Sibling `worktrees/` checkouts refer to branches of this repository; their contents do not become nested folders on GitHub.

Caveman ultra and Ponytail full are developer skills installed in the parent `.agents/skills/`. Ignored links expose them inside each checkout. They are not runtime dependencies, do not alter the bot's answers, and are not required for someone cloning this public repository.

New local worktrees should receive those ignored links and the PDF_QA_DATA_DIR environment variable. Never commit absolute machine paths as application defaults, documents, model weights, secrets, or generated indexes. Use `git status` and `git diff --cached --stat` before pushing.
