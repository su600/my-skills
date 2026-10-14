---
disable-model-invocation: true
name: pi-web-customizations
description: Add or port a custom theme and replace Pi Web branding/logo assets. Trigger when the user asks to customize themes, logos, icons, favicon/PWA branding, or preserve such changes while upgrading Pi Web. Inspect the target version and source first; back up before editing.
compatibility: Pi Web source repository, Node.js, and npm. If only a published global package is installed, obtain or prepare matching source/build rather than blindly editing compiled output.
metadata:
  author: user
  version: "1.0"
---

# Pi Web theme and branding customization

Port custom themes and logo/branding changes onto the *currently installed target version*. Changes may span theme state, CSS, UI branding, and static assets; do not assume an old patch applies unchanged.

## Safety and initial inspection

1. Establish which deployment the user means: local checkout, globally installed package, or remotely running service. Report target version and path before editing.
2. Inspect git status and preserve unrelated modifications. Never reset, clean, overwrite, or replace the checkout wholesale.
3. For server upgrades, inspect the service unit, environment, working directory, service user, `HOME`, port, and agent-data directory. Preserve configuration and sessions. Back up the service definition and relevant configuration/sessions before changes.
4. Look for an approved customization backup configured by the user. Treat it only as reference material: verify its base commit and inspect each patch against the target version.
5. Never print or copy credentials from environment files, auth files, or settings. Retain existing authentication intact.

## Theme implementation map

Inspect the target version and follow its current APIs. A theme may require:

- Theme preference registration and dark/light classification in the shared theme module, including any pre-hydration initialization logic.
- Theme CSS variables, palette, and backdrop in the global stylesheet. Check current layout class names before using selectors.
- A theme selector glyph where the UI uses per-theme icons.
- A label for every supported locale following the current translation structure.
- Tests for theme registration, initial dark-mode behavior, translations, and relevant settings UI.

Check whether reference changes also broaden typography (global body, chat, or settings sizes). Decide explicitly; do not silently treat typography changes as required for a color theme.

## Logo and branding implementation map

First clarify whether “logo” means sidebar, empty/new-session screen, browser favicon, PWA/home-screen icons, mobile launcher icon, or all. Do not replace unrelated provider/file/theme icons.

Inspect relevant current assets and components, which may include:

- A shared logo image and sidebar rendering.
- The empty/new-session mark.
- Browser favicon, PWA icons, Apple touch icon, and manifest references.
- Mobile launcher resources, only if requested.
- Service-worker precache entries/cache version for changed assets.

Use a user-provided or specifically approved asset. Do not invent a brand design or fetch a logo without approval. Preserve accessibility alt text, readability at small sizes, and binary asset rollback copies.

## Port and validation workflow

1. Read repository instructions (`AGENTS.md` and area notes). Record base version/commit, worktree state, and requested branding surfaces.
2. Compare reference changes to target code and port only applicable hunks. Preserve unrelated work.
3. Make small changes and update relevant tests.
4. Run focused tests, then available typecheck/lint/build checks, observing project-specific limitations.
5. For production edits, keep a rollback copy; validate service configuration before restart, then verify service health, HTTP response, authentication, and session listing.
6. Confirm agent data and sessions remain unchanged; UI session counts may differ from files on disk because some entries are filtered.
7. Report exact paths changed, tests/results, unchanged scope, deployment/version status, and rollback location.

## Packaging limitation

Pi Web plugins/extensions may not support replacing global frontend CSS, favicon, or message-row UI. These can require frontend source customizations. For a global package install, avoid patching compiled bundles as the default; use a versioned source checkout and the user's chosen deployment workflow. Later upstream updates may require re-porting.
