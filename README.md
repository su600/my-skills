# My Skills

A collection of user-created Pi-compatible agent skills.

## Skills

| Skill | Description |
|---|---|
| `aliyun-server-admin` | Security-conscious administration of an authorized Aliyun Linux server. |
| `bjtu-course-notes` | Turn a course recording into structured lecture notes and send them by email (credentials from env vars). |
| `chaoyang-school-district` | Look up Chaoyang District school enrollment service areas from public data. |
| `dsh-workspace-upload` | Upload files from DSH to a private WorkSpace Portal file drop via its authenticated upload API. |
| `github-commit-attribution` | Include accurate agent/model attribution in GitHub sync commits. |
| `gmail-smtp-send` | Send polished email through a privately configured Gmail SMTP account. |
| `openrouter-image-generator` | Generate images through an authorized OpenRouter account after user approval. |
| `outlook-inbox-cleanup` | Soft-delete low-value Outlook mail through a private rules file (example config provided). |
| `pi-web-customizations` | Safely port Pi Web theme and branding changes. |
| `pi-web-upgrade` | Upgrade pi and pi-web, re-apply the logo, and restart the pi-web service. |
| `travel-subsidy-calculator` | Calculate travel airfare subsidy from fare, discount, and rate. |
| `weekly-report` | Draft weekly reports from a user-provided template and work notes. |
| `workspace-pin` | Pin and unpin items in a privately configured Workspace portal. |

Each skill is in its own directory and contains a `SKILL.md` entry point. Keep personal configuration, credentials, customer data, and private infrastructure details outside this public repository.

## Security

Examples use placeholders or secure local configuration providers. Never commit passwords, API keys, tokens, account-specific addresses, private hostnames/IPs, or local configuration files. Review diffs before publishing changes.
