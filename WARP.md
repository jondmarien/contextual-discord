# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

# Project Overview
**Contextual Discord** is an AI-powered natural language GIF picker for Discord, implemented as a Vencord plugin with a Python backend.

- **Frontend (Plugin)**: TypeScript, React (Vencord User Plugin)
- **Backend**: Python, FastAPI, Sentence Transformers, Qdrant
- **Docs**: See `contextual_ai_gif_picker_discord_plugin_plan.md` for architectural details and roadmap.

# Environment & Tools
- **OS**: Windows 11 (Project default)
- **Shell**: PowerShell (`pwsh`)
- **Package Managers**:
    - Python: `uv` (Project uses `uv.lock`)
    - Node: `pnpm` (Required by Vencord)

# Backend (`/backend`)
Located in the `backend` directory.

## Setup & Run
1.  **Install Dependencies**:
    ```powershell
    cd backend
    uv sync
    ```
2.  **Run Dev Server**:
    ```powershell
    uv run uvicorn main:app --reload
    ```
3.  **Environment Variables**:
    - Check `config.py` for required variables (e.g., `TENOR_API_KEY`).
    - Create a `.env` file in `backend/` if necessary.

## Architecture
- **Framework**: FastAPI
- **Entry Point**: `main.py`
- **Structure**:
    - `models/`: Data models and embedding logic.
    - `routes/`: API endpoints (`search`, `health`, etc.).
    - `services/`: Business logic (Tenor API, Qdrant, Indexing).
    - `utils/`: Helper functions.

# Plugin (`/plugin`)
Located in the `plugin` directory. This is a **Vencord User Plugin**.

## Setup & Development
1.  **Vencord Installation**:
    - You must have a local clone of the [Vencord](https://github.com/Vendicated/Vencord) repository.
    - This project's `plugin` folder is meant to be integrated into that Vencord clone.

2.  **Linking**:
    - Copy or symlink `plugin/src/userplugins/contextual` to `path/to/Vencord/src/userplugins/contextual`.
    - *Example (PowerShell)*:
      ```powershell
      New-Item -ItemType Junction -Path "C:\path\to\Vencord\src\userplugins\contextual" -Target ".\plugin\src\userplugins\contextual"
      ```

3.  **Build & Inject**:
    - Run these commands **inside the Vencord repository**:
      ```powershell
      pnpm build
      pnpm inject
      ```

## Structure
- `src/userplugins/contextual/index.tsx`: Main plugin entry point.
- The plugin intercepts Discord's GIF picker to inject AI search capabilities.

# Common Tasks

## Linting & Formatting
- **Backend**: Check `pyproject.toml` for tools (likely `ruff` or `black` if configured, otherwise standard Python tooling).
- **Plugin**: Follow Vencord's linting rules (usually ESLint/Prettier).

## Testing
- **Backend**:
    ```powershell
    uv run pytest
    ```
    *(Note: Check if tests directory exists first)*

# Troubleshooting
- **Backend Issues**: Check `uvicorn` logs in the terminal. Ensure Qdrant and Tenor API keys are valid.
- **Plugin Issues**: Check Discord's Console (Ctrl+Shift+I). Ensure the plugin is enabled in Vencord settings.
