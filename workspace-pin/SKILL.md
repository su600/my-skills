---
name: workspace-pin
description: Pin or unpin files and directories in an authorized Workspace portal. Trigger when the user asks to pin, unpin, add an item to a homepage, or remove a pinned item. Resolve references from recent file work and verify the target exists under the configured workspace before calling the API.
---

# Workspace pin API

Configure the Workspace base URL, API credential provider, and workspace root privately for the deployment. Do not publish personal tokens, private IP addresses, local filesystem paths, or account-specific configuration. Use HTTPS for non-local network access.

API operations (confirm exact paths and schema against the deployment's API documentation):

- Pin: `POST /pin`, JSON `{"action":"pin","path":"workspace-relative/path"}`
- Unpin: `POST /pin`, JSON `{"action":"unpin","path":"workspace-relative/path"}`
- List pinned paths: `GET /api/pins`

Authenticate with an authorization bearer token loaded from a secure credential provider at request time. Never print, paste into chat, or log the token. Treat paths as relative to the configured workspace root and do not pin outside it. Ask a clarifying question if the requested file cannot be resolved unambiguously. Report API success/failure without revealing credentials.

Example pattern (replace placeholders from private deployment configuration; do not commit actual values; never enable shell tracing):

```bash
set +x
TOKEN="$(secure-credential-helper workspace-pin-token)"
BASE_URL="$(secure-config-helper workspace-base-url)"
curl --fail-with-body --silent --show-error \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"action":"pin","path":"relative/path"}' \
  "$BASE_URL/pin"
unset TOKEN BASE_URL
```
