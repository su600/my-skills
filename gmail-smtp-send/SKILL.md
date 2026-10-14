---
name: gmail-smtp-send
description: Use when the user asks to send email from Gmail, especially with a file or previously prepared document. Use Gmail SMTP and a securely configured app password, apply user-confirmed account defaults, write a polished context-specific message, and identify the actual sending agent and model.
compatibility: Requires Python 3, outbound SMTP SSL, a secure credential provider, and the requested content or attachment.
---

# Send email with Gmail SMTP

Use Gmail SMTP with an app password held by a secure credential provider. Do not put personal account addresses or machine-specific credential paths in a public skill; configure sender, recipient, and credential source privately.

## Before sending

1. Resolve the subject, recipient, body purpose, and attachments from the current request and conversation. For references like “this document,” verify the most recently edited relevant file exists.
2. Sending is an external side effect. Ensure the user explicitly asked to send the identified content to the resolved recipient. Ask if recipient or payload is unclear.
3. Read the app password only inside the sending process through a secure credential provider. Never print, quote, log, or put it in arguments, shell history, email, reports, or generated files. If unavailable, stop and ask for secure setup; do not fall back to another service without approval.
4. Ensure credential files are owner-only before use.
5. Inspect attachments and confirm the intended final version. Attach the requested file, not a summary in its place.
6. Identify the real agent and model using current runtime/session metadata. Never guess; use “unknown” if unavailable.

## Compose a professional message

Write for the actual recipient and purpose. Use the user's configured salutation preference when known. For document attachments, identify the title or filename, concisely explain contents and purpose, and close courteously. Match the user's language. Avoid casual filler, unexplained shorthand, unsupported claims, and irrelevant boilerplate.

### Visual presentation

- Prefer a clean HTML email with a complete plain-text alternative. Use semantic markup and inline CSS for email-client compatibility.
- Use comfortable body text (typically 16–18px) with readable line spacing. Make greeting/headings modestly larger (typically 20–24px); do not make the entire email oversized.
- Bold important identifiers, dates, actions, and attachment names. Use short paragraphs, bullets for related items, and headings for longer messages.
- Add only a few relevant emoji (usually 1–3) as visual signposts; keep a professional tone.
- Ensure the plain-text alternative retains the full message and any sender/model attribution.
- Keep the subject concise; add emoji to it only when genuinely suitable.

Include attribution in the body when requested or configured:

> Sent by: {actual agent} · Model: {actual model}

Never confuse sender attribution with an author credit inside an attachment.

## Send

Use Python `smtplib.SMTP_SSL` with `ssl.create_default_context()` and a reasonable timeout. Construct messages with `email.message.EmailMessage`; call `set_content()` with the full plain-text message, then `add_alternative(html, subtype='html')`, and attach files after the alternatives. Read the password only inside the Python process. Do not include credentials in exception output; report a safe error category.

Use the actual filename and suitable MIME type. After sending, report sender, recipient, subject, and attachments without revealing credentials. Do not claim delivery unless SMTP submission succeeded.
