"""Skeleton parser for building YAML task banks from an external source.

This is intentionally a *starting point*, not a finished scraper. Public exam
banks (e.g. the FIPI Open Bank, https://oge.fipi.ru) render tasks with
JavaScript and have their own terms of use — always check what you are allowed
to download and how. The function below shows the shape of the pipeline:

    fetch HTML  ->  extract tasks  ->  write a data/variants/<subject>/<slug>.yaml

Install the optional dependencies first::

    pip install -e ".[parse]"

Then adapt ``extract_tasks`` to the structure of your source.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

# Optional imports guarded so the module can be imported without the extras.
try:
    import httpx
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - only needed when actually scraping
    httpx = None  # type: ignore[assignment]
    BeautifulSoup = None  # type: ignore[assignment]


def fetch_html(url: str, timeout: float = 30.0) -> str:
    if httpx is None:
        raise RuntimeError('Install parse extras: pip install -e ".[parse]"')
    resp = httpx.get(url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def extract_tasks(html: str) -> list[dict]:
    """Return a list of task dicts. **Adapt selectors to your source.**

    Each dict should match the YAML task schema, e.g.::

        {"number": 1, "statement": "...", "answer_type": "number",
         "answer": "42", "explanation": "..."}
    """
    if BeautifulSoup is None:
        raise RuntimeError('Install parse extras: pip install -e ".[parse]"')
    soup = BeautifulSoup(html, "html.parser")
    tasks: list[dict] = []
    # --- Example placeholder logic (replace with real selectors) ---
    for index, node in enumerate(soup.select(".task"), start=1):
        statement = node.get_text(strip=True)
        answer = node.get("data-answer", "")
        tasks.append(
            {
                "number": index,
                "statement": statement,
                "answer_type": "text",
                "answer": answer,
            }
        )
    return tasks


def build_variant(
    subject: str, subject_title: str, slug: str, month: str, tasks: list[dict]
) -> dict:
    return {
        "subject": subject,
        "subject_title": subject_title,
        "slug": slug,
        "month": month,
        "title": f"{subject_title} — {month}",
        "description": "Импортировано скриптом parse_fipi.py (проверьте и отредактируйте).",
        "published": True,
        "tasks": tasks,
    }


def write_yaml(variant: dict, out_dir: Path) -> Path:
    subject_dir = out_dir / variant["subject"]
    subject_dir.mkdir(parents=True, exist_ok=True)
    out_path = subject_dir / f"{variant['slug']}.yaml"
    out_path.write_text(
        yaml.safe_dump(variant, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse an exam source into a YAML variant.")
    parser.add_argument("url", help="Page URL to fetch")
    parser.add_argument("--subject", default="informatics")
    parser.add_argument("--subject-title", default="Информатика")
    parser.add_argument("--slug", required=True, help="e.g. 2026-09")
    parser.add_argument("--month", required=True, help="e.g. 'Сентябрь 2026'")
    parser.add_argument("--out", default="data/variants", type=Path)
    args = parser.parse_args()

    html = fetch_html(args.url)
    tasks = extract_tasks(html)
    if not tasks:
        raise SystemExit("No tasks extracted — adapt extract_tasks() to your source.")
    variant = build_variant(args.subject, args.subject_title, args.slug, args.month, tasks)
    out_path = write_yaml(variant, args.out)
    print(f"✓ Wrote {len(tasks)} tasks to {out_path}")


if __name__ == "__main__":
    main()
