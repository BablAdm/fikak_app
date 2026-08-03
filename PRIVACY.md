# Privacy & Data Protection (GDPR / CCPA)

This document describes the personal data handled by the FastAPI backend and
how data-subject rights are supported. It is intentionally proportionate to
the current scope of the project (a test/integration backend); if the project
grows a formal privacy program (deletion queues, retention automation), this
document should be replaced by that program's playbook.

## Personal data inventory

| Field | Model / table | Classification | Purpose | Retention |
|---|---|---|---|---|
| `email` | `User` / `users` | PII (contact) | Account identity, login | Until account deletion |
| `username` | `User` / `users` | PII (identifier) | Display name, login | Until account deletion |
| `hashed_password` | `User` / `users` | Secret (bcrypt hash) | Authentication | Until account deletion |
| `filename`, `file_key` | `FileUpload` / `file_uploads` | Potentially PII (user-supplied) | File storage bookkeeping | Until file or account deletion |
| Post `title` / `content` | `Post` / `posts` | User content (potentially PII) | Application content | Until post or account deletion |

No data-classification metadata is stored at the column level; the table
above is the authoritative registry for this codebase.

## Data-subject rights

- **Access / portability** — `GET /api/auth/me/export` returns all personal
  data held for the authenticated user (account fields, posts, file
  metadata) in a machine-readable JSON format.
- **Erasure** — `DELETE /api/auth/me` synchronously deletes the user's S3
  objects, then their file records, posts, and account. S3 deletions are
  independent operations and are not transactional with the database: if a
  later S3 delete fails, the request returns HTTP 503 and **no database
  changes are committed**, but S3 objects already removed in that attempt
  stay removed. The operation is idempotent — retrying skips already-deleted
  objects and completes the erasure. A non-PII audit line (internal user id
  and object counts) is logged on completion.

## Scope and why no deletion queue / retention automation

**This document covers the FastAPI backend only** — its relational database
(PostgreSQL) and its S3 bucket, both fully owned by the application. Erasure
within that scope has no cross-system fan-out that would require queuing, and
no FastAPI-stack data is retained after account deletion that would require
retention-period tracking. Server logs contain internal ids only, not email
addresses or usernames.

**Out of scope:** the unified Frappe/MariaDB stack stores its own user and
business data with separate deletion tooling (Frappe's "Personal Data
Deletion" feature), and any site backups created via `bench backup` retain
copies of data until the backup files themselves are deleted. Operators must
manage Frappe-side erasure and backup retention separately.
