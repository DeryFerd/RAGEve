"""
HuggingFace Hub metadata helpers — card data and README fetching.

Provides:
  _fetch_hf_card_metadata() — full card metadata (tags, license, language, paper, leaderboard)
  _fetch_hf_readme_html()   — README.md rendered as escaped HTML
  _validate_dataset_id()    — validate dataset ID to prevent SSRF attacks
"""

from __future__ import annotations

import html as _html_module
import logging
import re
from typing import Any

from fastapi import HTTPException

_log = logging.getLogger("app")

# Pattern for valid HuggingFace dataset IDs: owner/dataset, dataset, or with config/split segments
# Each segment: alphanumeric, hyphens, underscores, dots (no spaces, no control chars)
# Typical examples: "squad", "microsoft/DIET", "microsoft/DIET/config_name", "owner/dataset/config/split"
_DATASET_ID_PATTERN = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?(/[a-zA-Z0-9]([a-zA-Z0-9._-]*[a-zA-Z0-9])?)*$")


def _validate_dataset_id(dataset_id: str) -> None:
    """
    Validate a HuggingFace dataset ID to prevent SSRF attacks.

    Raises:
        HTTPException: 400 if the dataset_id is invalid.
    """
    if not dataset_id:
        raise HTTPException(status_code=400, detail="Dataset ID cannot be empty")

    # Check total length (HuggingFace dataset IDs are typically < 255)
    if len(dataset_id) > 255:
        raise HTTPException(status_code=400, detail="Dataset ID too long")

    # Check for path traversal attempts
    if ".." in dataset_id:
        raise HTTPException(
            status_code=400, detail="Invalid dataset ID: path traversal not allowed"
        )

    # Check for double slashes (empty segments)
    if "//" in dataset_id:
        raise HTTPException(
            status_code=400, detail="Invalid dataset ID: empty segments not allowed"
        )

    # Check against allowed pattern
    if not _DATASET_ID_PATTERN.fullmatch(dataset_id):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid dataset ID format. Must be alphanumeric with hyphens/underscores/dots, "
                "optionally separated by slashes (e.g., 'owner/dataset')."
            ),
        )


def _fetch_hf_card_metadata(
    dataset_id: str, hf_token: str | None = None
) -> dict[str, Any]:
    """Fetch full dataset card metadata using huggingface_hub HfApi."""
    # Validate dataset_id to prevent SSRF attacks
    _validate_dataset_id(dataset_id)

    try:
        from huggingface_hub import HfApi  # type: ignore[import-untyped]

        api = HfApi()
        kwargs: dict[str, Any] = {}
        if hf_token:
            kwargs["token"] = hf_token
        info = api.dataset_info(dataset_id, files_metadata=False, **kwargs)

        tags: list[str] = list(info.tags) if info.tags else []
        license_str: str | None = info.license

        language: list[str] = []
        paper_url: str | None = None
        leaderboard: dict | None = None
        if info.card_data:
            lang = info.card_data.get("language") or info.card_data.get("languages", [])
            if isinstance(lang, list):
                language = [str(item) for item in lang]
            elif lang:
                language = [str(lang)]
            paper_url = (info.card_data.get("paper", {})).get(
                "url"
            ) or info.card_data.get("paperswithcode_id")
            leaderboard = info.card_data.get("leaderboard")

        # Convert card_data to dict if available
        card_data_dict = None
        if info.card_data:
            try:
                card_data_dict = info.card_data.to_dict()  # type: ignore[attr-defined]
            except Exception:
                try:
                    card_data_dict = dict(info.card_data)
                except Exception:
                    card_data_dict = info.card_data  # Pass through as-is

        return {
            "card_data": card_data_dict,
            "tags": tags,
            "language": language,
            "license": license_str,
            "paper_url": paper_url,
            "leaderboard": leaderboard,
        }
    except Exception as exc:  # noqa: BLE001
        _log.warning("Failed to fetch HF card metadata for '%s': %s", dataset_id, exc)
        return {
            "card_data": None,
            "tags": [],
            "language": [],
            "license": None,
            "paper_url": None,
            "leaderboard": None,
        }


def _fetch_hf_readme_html(dataset_id: str) -> str | None:
    """Fetch the dataset README.md from the HuggingFace Hub."""
    # Validate dataset_id to prevent SSRF attacks
    _validate_dataset_id(dataset_id)

    import httpx

    filenames = ["README.md", "README_fr.md", "README_de.md"]
    for fname in filenames:
        try:
            url = f"https://huggingface.co/datasets/{dataset_id}/raw/main/{fname}"
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code == 200:
                content = resp.text[:4000]
                escaped = _html_module.escape(content)
                return f"<pre style='font-size:12px;line-height:1.6;max-height:400px;overflow:auto'>{escaped}</pre>"
        except Exception as exc:  # noqa: BLE001
            _log.warning(
                "Failed to fetch README for '%s' (%s): %s", dataset_id, fname, exc
            )
            continue
    return None
