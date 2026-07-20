# Task banks (`data/`)

Everything the bot asks students is stored here as plain YAML — **no code changes
needed to add material**. This is the "extensible materials" part of the project.

## Layout

```
data/
└── variants/
    └── <subject>/          # subject code, e.g. informatics, mathematics
        └── <slug>.yaml     # one exam variant, usually one per month
```

The folder name is cosmetic; the `subject:` field inside the file is the real key.
The `slug` is unique per subject (defaults to the file name without extension).

## File format

```yaml
subject: informatics            # stable code — the database key for the subject
subject_title: Информатика      # display name
slug: "2026-09"                 # optional (defaults to file name); unique per subject
month: Сентябрь 2026            # human-readable label shown in the menu
title: Информатика ОГЭ — сентябрь 2026
description: Короткое описание варианта.   # optional
published: true                 # set false to hide from students while editing
tasks:
  - number: 1                   # position in the variant (1..N, contiguous)
    statement: "Текст задания…"
    answer_type: number         # number | text | sequence
    answer: 60                  # a value, or a list of accepted values
    image_url: null             # optional link to a picture (storage/CDN)
    image_file_id: null         # optional cached Telegram file_id
    max_score: 1                # optional, default 1
    explanation: "Разбор…"      # optional, shown via the 💡 button
```

### `answer_type`

| Type       | Comparison                                                       | Example answer |
|------------|------------------------------------------------------------------|----------------|
| `number`   | numeric, tolerant to `.`/`,` and spaces (`0.4` == `0,4`)         | `13.7`         |
| `sequence` | exact ordered characters, separators ignored (`2 3 1` == `231`) | `"11011"`      |
| `text`     | case-insensitive, spacing-tolerant, `ё`≈`е`                      | `Москва`       |

Multiple accepted answers: pass a list — `answer: ["0.4", "2/5"]`.

### Images

Two officially supported ways to attach a picture to a task:

1. **`image_url`** — a link to external object storage (S3/MinIO, a CDN, GitHub raw,
   etc.). Telegram downloads it when the task is shown.
2. **`image_file_id`** — a Telegram `file_id`. After Telegram has the photo once, this
   is the fastest, most reliable option (no re-download). Get a `file_id` by sending
   the photo to your bot and reading it from the update, or from `@RawDataBot`.

If a URL cannot be fetched, the bot degrades gracefully to a text message with the link.

## Loading changes

After editing or adding files:

```bash
python scripts/seed.py          # re-reads every file (idempotent)
```

or, from Telegram as an admin: `/reload`.

Re-seeding **fully replaces** a variant's tasks, so the database always matches the files.
