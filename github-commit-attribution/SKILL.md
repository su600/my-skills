---
name: github-commit-attribution
description: Whenever implementing, fixing, or updating a program and syncing the change to GitHub, automatically include the responsible agent and actual model in the commit message. Trigger for GitHub commits, pushes, releases, or requests to sync code changes, even when the user does not explicitly repeat the attribution requirement.
---

# GitHub commit attribution

When committing program changes that will be pushed or otherwise synchronized to GitHub, include both the agent and model attribution in the commit message by default. Do this even if the user does not repeat the instruction.

## Required attribution

Append commit-message trailers on separate lines:

```text
Agent: <actual agent identity>
Model: <actual model identity>
```

Use the identities available in the current session/runtime metadata. Never guess, infer from an earlier session, or copy an identity from a previous commit. If the model or agent identity cannot be determined, ask before committing rather than inventing it.

## Workflow

1. Before committing, confirm the intended repository, files, and target branch. Do not include secrets, generated binaries, local configuration, or unrelated user changes.
2. Create a concise subject/body describing the code change.
3. Add the `Agent:` and `Model:` trailers after a blank line. Example:

   ```text
   feat: add pin API

   Agent: Pi coding agent
   Model: <actual runtime model name>
   ```

4. Verify the final commit body contains both trailers before pushing.
5. Push only the intended branch and confirm the resulting GitHub commit URL/SHA.

## Scope

This applies to source-code/program changes synchronized to GitHub. Do not add attribution to ordinary non-code commits unless the user asks. Do not amend or rewrite an already-pushed commit merely to add attribution unless the user explicitly requests that correction; use a follow-up commit if attribution must be added after the fact.
