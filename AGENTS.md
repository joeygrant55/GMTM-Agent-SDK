# SPARQ Agent working context

This repository is `joeygrant55/GMTM-Agent-SDK`, the SPARQ Agent implementation.

Start with [current work](docs/state/current-state.md), then read the linked Control Tower operating contract and registry. Before meaningful changes, inspect the actual branch, remote, latest commit and working tree, and read any current repo handoff.

Keep the existing writer and checkout for an active task. The project registry records observed paths; it does not assign a task or transfer a worktree. Preserve unrelated local changes and separate SPARQ implementation lanes until their owners hand off.

The September 5 current-work document distinguishes today's combine-completion direction from earlier pricing, demo and post-results-only proposals. Older specs remain context; they are not evidence of current implementation or permission to ship.

Local startup must explicitly target an isolated backend and data environment. The README documents a live backend fallback when `NEXT_PUBLIC_BACKEND_URL` is absent. Use the current task's verification and authorization boundaries before running mutation-capable flows.

Close meaningful work with a dated `.sammy/handoffs/` note, relevant verification, and an accurate list of uncommitted changes. Update current state when the implementation status or next action changes. Share or deploy only within Joey's explicit authorization for the active task.
