"""CUI marking records (Spec 005 T551; CLM-005-28).

A marking is a *recorded field set*, nothing more: category,
controlling authority, dissemination controls — as recorded by the
study or the tenant that owns the artifact. The platform records
markings and carries them into the artifacts it produces (bundle
manifests, HUMAN-README banner/footer, audit exports); it does not
adjudicate them — whether a marking is *correct* for a body of
information is the marking organization's determination, not a
platform verdict.

An artifact with no recorded marking says so explicitly: the
marking block is always present, and its unmarked state is stated,
never left ambiguous by absence.
"""

from __future__ import annotations

from typing import Any, Optional

MARKING_FIELDS = ("category", "authority", "dissemination")


def normalize_marking(marking: Optional[dict[str, Any]]) -> dict[str, Any]:
    """The canonical marking block carried in manifests. `status`
    is "marked" only when a category is recorded; anything else is
    an explicitly unmarked artifact."""
    if not marking or not marking.get("category"):
        return {
            "status": "unmarked",
            "category": None,
            "authority": None,
            "dissemination": None,
            "note": "No CUI marking is recorded for this artifact. "
                    "The absence of a marking is stated, not implied: "
                    "this block is present in every manifest.",
        }
    block = {
        "status": "marked",
        "category": marking.get("category"),
        "authority": marking.get("authority"),
        "dissemination": marking.get("dissemination"),
        "note": "Marking recorded from the owning study/tenant's "
                "recorded fields. The platform records markings; "
                "it does not adjudicate them.",
    }
    return block


def banner_lines(block: dict[str, Any]) -> list[str]:
    """The banner/footer lines a human-readable artifact carries —
    the same lines at the top and the bottom, per marking practice.
    For an unmarked artifact the line states that state."""
    if block.get("status") == "marked":
        parts = [f"CUI marking (recorded): {block['category']}"]
        if block.get("authority"):
            parts.append(f"Controlling authority: {block['authority']}")
        if block.get("dissemination"):
            parts.append(f"Dissemination: {block['dissemination']}")
        return [" | ".join(parts)]
    return ["CUI marking: none recorded — this artifact is UNMARKED."]
