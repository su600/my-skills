---
disable-model-invocation: true
name: dsh-workspace-upload
description: Upload files the user asks to send, transfer, or save from DSH to their WorkSpace Portal phone file drop. Trigger whenever the user asks to send a file to their phone, upload a file to “文件中转站”, or transfer a file through DSH to <your-portal-host>. Uses the portal upload API and confirms success from its HTTP response.
---

# DSH → WorkSpace 文件中转站

Use the WorkSpace Portal upload API when the user asks DSH to deliver a file to their phone or save it in the portal's `文件中转站` folder.

## Endpoint

- URL: `https://<your-portal-host>/api/upload`
- Method: `POST`
- Body: `multipart/form-data`
- File field: `file`
- Destination: server-fixed workspace folder `文件中转站`; never send or request a destination path.
- Limit: one file per request, maximum 100 MiB.
- Authentication: HTTP Basic Auth using the portal's existing `PORTAL_USER` and `PORTAL_PASS` credentials. Credentials must come from DSH's configured secret store/environment, never from user-facing chat, source code, or logs. Do not assume or expose default credentials.

## Procedure

1. Resolve which file the user means. If ambiguous, ask which file; do not upload unrelated files.
2. Check the file exists and is within the 100 MiB limit. Keep its original filename unless the user requests a different name. Never include a client-provided path in the API body.
3. Retrieve the username/password from the approved secure configuration. Never ask the user to paste a password into chat if secure configuration can be used; if credentials are unavailable, explain that DSH needs the portal credentials configured securely.
4. Send the file bytes as multipart field `file` to the endpoint over HTTPS. Do not JSON-encode or Base64-encode the file.
5. Inspect the HTTP status and JSON response before reporting success:
   - `201 Created`: report the returned `path` and `size` as uploaded.
   - `401 Unauthorized`: report that the configured portal credentials need checking; never print credentials.
   - `409 Conflict`: a file with that name already exists and was not overwritten. Ask the user whether to rename and retry.
   - `413 Request Entity Too Large`: explain the 100 MiB limit.
   - Other failures or network errors: report failure accurately; do not claim upload succeeded.
6. Do not retry a `409` under the same name. Do not delete, replace, or overwrite files in the portal.

## curl reference

For manual troubleshooting only; do not put actual credentials in this command or chat. `--user USERNAME` prompts for the password interactively. In DSH automation, use its secure credential facility to supply Basic Auth without logging the secret.

```bash
curl --fail-with-body \
  --user 'USERNAME' \
  -F 'file=@/path/to/file' \
  'https://<your-portal-host>/api/upload'
```

A successful response is HTTP `201` and looks like:

```json
{"ok":true,"filename":"photo.jpg","path":"文件中转站/photo.jpg","size":12345}
```

> Security: Basic Auth is the same credential used to sign in to WorkSpace Portal. Always use the HTTPS URL above; never send these credentials over plain HTTP, expose them in logs, or repeat them in the final reply.

---

> 由 **Pi coding agent** 使用 **openai/gpt-6-luna** 生成 · 2026-10-14 11:49 CST
