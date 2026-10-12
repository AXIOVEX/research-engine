# Design Note 009 — Wireframe-Governed UI (owner ruling, 2026-10-12)

**Date:** 2026-10-12 · **Status:** Adopted — ratified by the owner's approval of the rendered Phase 6 wireframe package, 2026-10-12.
**Decision source:** Owner ruling during Spec 002 Phase 6: *"wireframes first, and the wireframes are constitutional. No changes to the actual UI without first updating the wireframes AND getting his approval on the RENDERED wireframes."*
**Ratified:** 2026-10-12 — the owner approved the rendered wireframe package ("Approve the wireframes — begin UI implementation", Glossa-Lab chat, ~08:25 EDT). Article XIV (constitution v1.2.0) is in force; gate T219-WF is cleared and T219 is unblocked.

## Decision

The UI's layout and appearance are governed by rendered wireframes, the way the record is governed by the constitution:

1. The wireframe package lives in `docs/wireframes/` (screens as HTML/CSS at full design fidelity, screenshots at desktop and mobile widths, tokens and component rules in `WIREFRAMES.md`).
2. No UI change ships without the wireframes being updated first and the **rendered** wireframes approved by the owner. Approval is of screenshots, not of source.
3. A shipped UI that differs from the approved wireframes is a defect against the wireframes.
4. Constitution Article XIV (draft, v1.2.0) carries this rule; the owner's approval of the Phase 6 wireframe package ratifies both the package and the article.

## Why

The same reason as Article XII (spec before code), applied to the surface: a UI built first and described later drifts into whatever the implementation found convenient — and for this product the surface is where the discipline is either visible or faked (an INVALID run softened into a dashboard, a dead claim quietly omitted, a metadata-only basis hidden behind an aggregate). The owner reviews what users will see, rendered, before it exists. The household rule from prior website work is the same lesson in another medium: source-level checks do not establish that a page renders true.

## Effect

- Spec 002 Phase 6 re-sequences: wireframe package → owner approval → T219 implementation. tasks.md records the gate as T219-WF (blocked on approval); no UI task is checked off by this note or the package.
- The Phase 6 AEE claims (CLM-002-31…40) were authored and assessed *before* the ruling and stand; their "supported" evidence is now, additionally, gated on the approved-wireframe implementation.
- The package's sample data is the Phase 5 demo study — the owner approves screens showing the record's real, unflattering states (INVALID run, metadata-only evidence, fabricated citation), not mock content.

## Falsifier for this decision

If an approved-wireframe workflow measurably slows UI iteration without catching divergence — e.g., two consecutive UI changes ship matching unapproved renderings anyway, or the approval screenshots repeatedly fail to represent the shipped result — the governance is ceremony, not control, and this note should be revisited.
