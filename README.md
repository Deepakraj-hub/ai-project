# Lily AI

Lily is a desktop AI assistant with a Python brain, Flask API, PySide6 desktop UI, and embedded 3D avatar.

## Current Architecture

- `jarvis.py` keeps the existing chat brain, memory, voice, camera, smart search, location, and Ollama/Gemma integration.
- `app.py` exposes the Flask API for chat and the autonomous agent.
- `lily_desktop.py` launches the PySide6 desktop app.
- `ai-avatar/` contains the Vite/React/Three.js avatar that is embedded in the desktop app.
- `lily/` contains the new autonomous agent engine inspired by Atomic Hermes concepts.

## Autonomous Agent Engine

The new `lily/` package is additive. It does not replace Lily or fork Hermes.

Pipeline:

1. Planner decomposes the user goal.
2. Reasoner chooses the next action and tool.
3. Permission layer blocks risky actions until approved.
4. Executor runs tools and captures observations.
5. Workspace manager stores `workspace/<task_id>/notes.md`, `plan.json`, logs, generated files, and results.
6. Memory stores tasks, steps, project facts, skills, and reflections.
7. Reflection records mistakes and future improvements.

Agent API:

- `GET /api/agent/tools`
- `POST /api/agent/run`

Example:

```json
{
  "goal": "Analyze this project and report the main modules",
  "max_steps": 5
}
```

If Lily needs approval, the response includes `requires_permission` with an `approval_key`. Re-run the same task with:

```json
{
  "task_id": "existing_task_id",
  "goal": "Analyze this project and report the main modules",
  "approvals": {
    "tool:risk:action": {
      "approved": true,
      "always_allow": false,
      "reason": "Approved by user"
    }
  }
}
```

## Development

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Run Flask API:

```bash
python app.py
```

Build avatar for desktop embedding:

```bash
cd ai-avatar
npm install
npm run build
```

Run desktop app:

```bash
python lily_desktop.py
```
