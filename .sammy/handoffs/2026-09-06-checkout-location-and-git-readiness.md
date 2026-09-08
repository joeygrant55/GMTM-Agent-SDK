# Checkout location and Git readiness

September 6, 2026. Joey asked whether the Higgsfield-named task folder is an optimal development location and whether normal Git work remains available. This was a bounded diagnostic and relocation proposal, not authorization to move, commit, push or deploy.

## Verified

- The owned `work/sparq-agent-review` directory is the Git top level, with its own nonsymlink `.git` directory. The enclosing task workspace is not a Git repository; SPARQ is not mixed into a Higgsfield Git history.
- Branch: `codex/athlete-home-first-value`; HEAD: `6c7e649ce5154f211401ed2e4af03d9691366194`; origin: `https://github.com/joeygrant55/GMTM-Agent-SDK.git`.
- `git fsck --connectivity-only --no-dangling` passed. Author and committer identities were configured, OS permissions indicate writable Git metadata, and no index lock was present. No test commit was made.
- Before this documentation addition, status contained 17 modified tracked files, 48 untracked files and no staged files. These include the prior verified implementation and handoffs; none was discarded or committed.
- The branch has no configured upstream. That does not prevent local commits; a deliberate first branch push can establish tracking when sharing is requested.
- A read-only authenticated GitHub metadata request confirmed the current account has push/admin access and that the repository is public. This is not a test push or a check of every branch-protection rule. Review source, internal documents and generated artifacts for appropriate inclusion before any public push.

## Recommendation

Use `~/Companies/GMTM/sparq-agent` as the proposed permanent MacBook project root. The registry prefers `~/Companies/<Company>/<repo>` and explicitly recognizes the current task checkout as an active exception. A bounded immediate directory inventory found no existing GMTM destination. The current path is organizational debt, not a broken repository.

1. Review and checkpoint the current implementation in coherent commits; preserve untracked and ignored material separately where appropriate. Committing locally does not publish to GitHub.
2. Transfer the complete owned checkout/branch at a coordinated writer handoff. Do not overwrite the home SDK clone, its ws2 worktree or another machine's lane.
3. Preserve this task's sibling `work/` verification receipts and `outputs/` previews, which are outside the Git repository. Account for absolute documentation paths and dependency/environment references.
4. Update the saved Codex project, Fable handoff and Control Tower registry; verify Git status/history and relevant checks at the destination before retiring the old path.

The setup-audit lane can coordinate that bounded relocation. Fable should use the existing provided path until the destination is verified. No move, symlink, configuration change, commit, push, external message or production action was performed here. Only this handoff and current-state routing text were added/updated; all application code remains as at the last verified checkpoint.
