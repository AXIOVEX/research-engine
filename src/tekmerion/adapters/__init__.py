"""Domain evidence adapters (Specs 006–008; survey shortlist, owner
gate passed 2026-10-12).

An adapter = (artifact type, independent checker, registered scope
claim stating what the check does NOT establish) — DN-010, Spec 004 §2.
Adapters supply lane-1 evidence only: they never issue verdicts, and
an adapter result can never settle a claim alone. Every adapter output
carries the artifact hash, checker identity + version, the invocation
honesty state, the raw-output hash, and the id of the adapter's
registered blind-spot scope claim (CLM-006-02 / CLM-007-02 /
CLM-008-02). The shared seam lives in `tekmerion.adapters.core`.
"""
