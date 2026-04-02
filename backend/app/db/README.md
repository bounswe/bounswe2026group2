# Database Models

SQLAlchemy table models live in this package.

## Implemented schema

- `users`: authentication and profile fields
- `stories`: story content plus publication metadata
- `media_files`: object-storage-backed media linked to stories

## Design notes

- All primary keys use UUIDs so rows can be created safely across environments.
- `created_at` and `updated_at` are included on every table for auditability.
- `users.username` and `users.email` are unique.
- `users.password_hash` stores only a hash, never a raw password.
- `users.role` and `users.is_active` are included now so auth and authorization can grow without reshaping the table immediately.
- `stories` belongs to `users` through `user_id`.
- `stories.status` and `stories.visibility` are explicit enums so draft/publication flow can evolve cleanly.
- `media_files` belongs to `stories` through `story_id`.
- `media_files` stores storage location as `bucket_name + storage_key`, which keeps the schema compatible with MinIO locally and S3-compatible storage in production.
- `media_files.alt_text` and `media_files.caption` are optional initial metadata fields for accessibility and presentation.
