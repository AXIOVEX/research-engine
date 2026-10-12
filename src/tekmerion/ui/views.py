"""HTML rendering for the register-first workspace (T219).

The markup mirrors the approved wireframes screen for screen
(`docs/wireframes/*.html`; constitution Article XIV): same shell,
same components, same classes — the wireframe files are the
requirements, this module is their production rendering against
live records. Every value rendered comes from the study's ledger
projections (`tekmerion.ui.state`); nothing here invents a state.

Text the wireframes carry as sample prose is rendered from the
record where the record speaks (engine reasons verbatim, in mono,
inside refusal/INVALID banners — WIREFRAMES.md §4) and kept generic
where it is explanation, citing its authority inline (§5).
"""

from __future__ import annotations

import html
from typing import Any, Optional

from . import state as st


def e(x: Any) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def short_hash(h: Optional[str]) -> str:
    if not h:
        return "—"
    return f"{h[:8]}…{h[-5:]}" if len(h) > 14 else h


def chip(text: str, cls: str = "") -> str:
    return f'<span class="chip {e(cls)}">{e(text)}</span>'


def verdict_chip(verdict: str) -> str:
    return chip(verdict.upper(), verdict)


def meter(checked: int, total: int, *, label: str = "groups content-checked") -> str:
    pct = int(100 * checked / total) if total else 0  # never rounds up
    return (f'<span class="meter"><span style="width:{pct}%"></span></span> '
            f"{checked} of {total} {label} ({pct}%)")


def banner_refusal(heading: str, message: str, note: str = "") -> str:
    note_html = (f'<div class="small" style="margin-top:4px">{e(note)}</div>'
                 if note else "")
    return (f'<div class="banner-refusal"><strong>{e(heading)}</strong> '
            f'<span class="mono">{e(message)}</span>{note_html}</div>')


def role_links(base_path: str, actor: str) -> dict[str, str]:
    return {r: f"{base_path}?role={r}&actor={e(actor)}" for r in st.ROLES}


_SIDEBAR_CHIP_STYLE = "background:#274B74;border-color:#4A6E99;color:#DCE6F2"


def shell(*, page_title: str, study: Optional[dict[str, Any]], active: str,
          actor: str, role: str, links: dict[str, str], body: str,
          actor_note: str, pending_count: Optional[int] = None,
          sidebar_variant: str = "study") -> str:
    if sidebar_variant == "specimens":
        study_block = (
            '<div class="study-block"><div class="study-label">Wireframe package</div>'
            '<div class="study-name">Component specimens</div></div>')
        nav_items = [
            ("register", "Claim register", None), ("queue", "Adjudication queue", None),
            ("freeze", "Freeze &amp; verdicts", None), ("export", "Export &amp; anchor", None),
        ]
        nav = '<nav class="nav">' + "".join(
            f'<a href="{e(links.get("picker", "/"))}">{label}</a>'
            for _key, label, _c in nav_items) + "</nav>"
        actor_block = (
            '<div class="actor-block"><div class="study-label">About this page</div>'
            '<p class="micro" style="color:#C9D8E8">States the demo study\'s record does '
            "not contain (a dead claim, a pending adjudication, verdict badges on claims) "
            "are specified here as specimens — clearly not study data.</p></div>")
    elif study is not None:
        sid = study["id"]
        chips = ""
        if study.get("frozen"):
            chips += f'<span class="chip" style="{_SIDEBAR_CHIP_STYLE}">Frozen</span> '
        if study.get("anchored_mechanism"):
            mech = study["anchored_mechanism"]
            label = "Zenodo" if mech == "zenodo" else mech
            chips += (f'<span class="chip" style="{_SIDEBAR_CHIP_STYLE}">'
                      f"Anchored · {e(label)}</span>")
        study_block = (
            '<div class="study-block"><div class="study-label">Study</div>'
            f'<div class="study-name">{e(study["title"])}</div>{chips}</div>')
        count = (f' <span class="count">{pending_count} pending</span>'
                 if pending_count is not None else "")
        nav = (
            '<nav class="nav">'
            f'<a href="/studies/{e(sid)}/" class="{_act(active, "register")}">Claim register</a>'
            f'<a href="/studies/{e(sid)}/queue" class="{_act(active, "queue")}">Adjudication queue{count}</a>'
            f'<a href="/studies/{e(sid)}/freeze" class="{_act(active, "freeze")}">Freeze &amp; verdicts</a>'
            f'<a href="/studies/{e(sid)}/export" class="{_act(active, "export")}">Export &amp; anchor</a>'
            "</nav>")
        spans = "".join(
            f'<a href="{e(links[r])}"><span class="{"on" if r == role else ""}">'
            f"{st.ROLE_LABELS[r]}</span></a>"
            for r in st.ROLES)
        actor_block = (
            '<div class="actor-block"><div class="study-label">Acting as</div>'
            f'<div class="who">{e(actor)}</div>'
            f'<div class="role-switch">{spans}</div>'
            f'<p class="micro" style="color:#9FB6CE">{e(actor_note)}</p></div>')
    else:
        study_block = (
            '<div class="study-block"><div class="study-label">Workspace</div>'
            '<div class="study-name">Register-first study workspace</div></div>')
        nav = ""
        actor_block = (
            '<div class="actor-block"><div class="study-label">Acting as</div>'
            f'<div class="who">{e(actor)}</div>'
            f'<p class="micro" style="color:#9FB6CE">{e(actor_note)}</p></div>')

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(page_title)} — Tekmerion</title>
<link rel="stylesheet" href="/static/style.css">
</head>
<body>
<div class="shell">
  <aside class="side">
    <div>
      <div class="brand-name">TEKMERION</div>
      <div class="brand-tag">Defensible research records</div>
    </div>
    {study_block}
    {nav}
    <div class="spacer"></div>
    {actor_block}
  </aside>
  <main class="main">
    <div class="wrap">
{body}
    </div>
  </main>
</div>
</body>
</html>"""


def _act(active: str, key: str) -> str:
    return "active" if active == key else ""


def refusal_page(*, page_title: str, study: Optional[dict[str, Any]], active: str,
                 actor: str, role: str, links: dict[str, str], heading: str,
                 message: str, actor_note: str,
                 pending_count: Optional[int] = None) -> str:
    body = banner_refusal(heading, message)
    return shell(page_title=page_title, study=study, active=active, actor=actor,
                 role=role, links=links, body=body, actor_note=actor_note,
                 pending_count=pending_count)


# ------------------------------------------------------------------ picker

def render_picker(ctx: dict[str, Any]) -> str:
    rows = ""
    for s in ctx["studies"]:
        chips = ""
        if s["frozen"]:
            chips += chip("Frozen", "brand") + " "
        if s["anchored"]:
            chips += chip("Anchored", "brand")
        rows += (
            f'<div class="card"><h3><a href="/studies/{e(s["id"])}/">{e(s["title"])}</a> '
            f'{chips}</h3><p class="muted" style="margin:0">'
            f'<span class="mono">{e(s["id"])}</span> · {s["claims"]} claims registered · '
            f'{s["events"]} ledger events</p></div>')
    if not ctx["studies"]:
        rows = ('<div class="card empty">No studies in this workspace yet. '
                "Create one below — its first screen is its claim register.</div>")
    create = ""
    if ctx["can_create"]:
        create = f"""
      <h2>New study</h2>
      <div class="card">
        <form method="post" action="/studies">
          <div class="grid2">
            <div class="field">
              <label for="sid">Study ID</label>
              <input id="sid" name="study_id" type="text" placeholder="e.g. sleep-replication-2026">
              <div class="help">Lowercase letters, digits, hyphens. The study's directory and ledger take this name.</div>
            </div>
            <div class="field">
              <label for="title">Title</label>
              <input id="title" name="title" type="text" placeholder="What the study is called">
            </div>
          </div>
          <div class="row-actions">
            <button class="btn primary" type="submit">Create study</button>
            <span class="muted small">Creating a study creates its append-only ledger. Registration comes next, inside the study.</span>
          </div>
        </form>
      </div>"""
    body = f"""
      <div class="crumb">Workspace</div>
      <h1>Studies</h1>
      <p class="page-sub">The register is the study: opening a study presents its claim register first (CLM-002-31). No landing page stands in front of it but this index.</p>
      {banner_refusal('Refused.', ctx['refusal']) if ctx.get('refusal') else ''}
      {rows}
      {create}"""
    return shell(page_title="Studies", study=None, active="", actor=ctx["actor"],
                 role=ctx["role"], links=ctx["links"], body=body,
                 actor_note=ctx["actor_note"])


# ------------------------------------------------------------------ (a) register

def _claim_status_chip(claim: Any, dead: Optional[dict], frozen_claims: list[str]) -> str:
    if dead is not None:
        return chip("DEAD", "dead")
    if claim.status == "superseded":
        return chip("Superseded", "dead")
    if claim.claim_id in frozen_claims:
        return chip("Registered · frozen", "brand")
    return chip(claim.status.replace("-", " ").capitalize(), "brand")


def render_register(ctx: dict[str, Any]) -> str:
    study = ctx["study"]
    run = ctx["run"]
    banner = ""
    if run["state"] == "invalid":
        reasons = "; ".join(run["reasons"])
        banner = f"""
      <div class="banner-invalid">
        <strong>Latest run: INVALID.</strong> No claim verdicts were issued for this run.
        <span class="why">{e(reasons)} (WS3 §1) — the register shows that, not a softened version of it.</span>
        <a href="/studies/{e(study['id'])}/freeze">See the run →</a>
      </div>"""
    elif run["state"] == "valid":
        banner = """
      <div class="banner-valid">
        <strong>Latest run: valid.</strong> Claim verdicts were issued and are recorded in the register.
      </div>"""
    reg_line = "not frozen"
    if ctx["registration_hash"]:
        reg_line = f'Registration hash <span class="mono">{e(short_hash(ctx["registration_hash"]))}</span>'
    freeze_line = ""
    if ctx["freeze_root"]:
        freeze_line = (f' · freeze checkpoint root <span class="mono">'
                       f'{e(short_hash(ctx["freeze_root"]))}</span>')
    ledger_line = ('<strong style="color:var(--ok)">intact</strong>' if ctx["ledger_ok"]
                   else '<strong style="color:var(--contradicted)">FAILED</strong>')
    stats = ctx["stats"]
    rows = ""
    for row in ctx["rows"]:
        claim, dead = row["claim"], row["dead"]
        groups = row["groups"]
        meta = any(g.get("metadata_only") for g in groups)
        ev_cell = f'{len(groups)} origin group{"s" if len(groups) != 1 else ""}'
        if meta:
            ev_cell += '<br><span class="chip metaonly">metadata-only</span>'
        if dead is not None:
            rows += f"""
            <tr class="dead-row">
              <td data-h="Claim" class="mono"><a href="/studies/{e(study['id'])}/claims/{e(claim.claim_id)}">{e(claim.claim_id)}</a> {chip('DEAD', 'dead')}</td>
              <td data-h="Statement" class="statement"><span class="dead-statement">{e(claim.statement)}</span></td>
              <td data-h="Falsifier" class="muted">{e(claim.falsifier)}</td>
              <td data-h="Status">dead · reason: “{e(dead['reason'])}”</td>
              <td data-h="Evidence">{ev_cell}</td>
              <td data-h="Verdict" class="mono">{e(dead['score'] if dead['score'] is not None else 0.0)}</td>
            </tr>"""
            continue
        verdict = row["verdict"]
        if verdict:
            v_cell = verdict_chip(verdict["verdict"])
        elif run["state"] == "invalid":
            v_cell = '— none<br><span class="small">run invalid</span>'
        else:
            v_cell = '<span class="muted">— none</span>'
        rows += f"""
            <tr>
              <td data-h="Claim" class="mono"><a href="/studies/{e(study['id'])}/claims/{e(claim.claim_id)}">{e(claim.claim_id)}</a></td>
              <td data-h="Statement" class="statement">{e(claim.statement)}</td>
              <td data-h="Falsifier" class="muted">{e(claim.falsifier)}</td>
              <td data-h="Status">{_claim_status_chip(claim, dead, ctx['frozen_claims'])}</td>
              <td data-h="Evidence">{ev_cell}</td>
              <td data-h="Verdict">{v_cell}</td>
            </tr>"""
    if not ctx["rows"]:
        rows = ('<tr><td colspan="6" class="empty">No claims registered yet. '
                "Registration is the study's first act.</td></tr>")
    register_btn = ""
    if ctx["can_register"]:
        register_btn = (f'<a class="btn primary" href="/studies/{e(study["id"])}/register">'
                        "Register a claim</a>")
    body = f"""
      <div class="crumb">Study · {e(study['id'])}</div>
      <h1>Claim register</h1>
      <p class="page-sub">The register is the study. {reg_line}{freeze_line} · ledger verification: {ledger_line}</p>
      {banner}
      <div class="stats">
        <div class="stat"><div class="num">{stats['claims']}</div><div class="lab">Claims registered</div></div>
        <div class="stat"><div class="num">{stats['citations']}</div><div class="lab">Citations checked</div></div>
        <div class="stat"><div class="num">{stats['resolved']} / {stats['citations']}</div><div class="lab">Citations resolved</div></div>
        <div class="stat"><div class="num">{stats['cov_pct']}%</div><div class="lab">Evidence content-checked</div></div>
      </div>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:11%">Claim</th><th style="width:31%">Statement</th><th style="width:26%">Falsifier</th><th style="width:11%">Status</th><th style="width:12%">Evidence</th><th style="width:9%">Verdict</th></tr>
          </thead>
          <tbody>{rows}
          </tbody>
        </table>
      </div>
      <div class="row-actions">
        {register_btn}
        <span class="muted small">Registration is an append. There is no edit and no delete — a changed statement is a new claim that supersedes the old one.</span>
      </div>"""
    return shell(page_title="Claim register", study=study, active="register",
                 actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                 actor_note=ctx["actor_note"], pending_count=ctx["pending_count"])


# ------------------------------------------------------------------ (b) registration form

def render_register_form(ctx: dict[str, Any]) -> str:
    study = ctx["study"]
    v = ctx["values"]
    if not ctx["can_register"]:
        body = f"""
      <div class="crumb"><a href="/studies/{e(study['id'])}/">Claim register</a> · New claim</div>
      <h1>Register a claim</h1>
      <div class="card empty">Registration is a researcher / adjudicator action (WS6 §1). This view — {e(st.ROLE_LABELS[ctx['role']])} — offers no registration form.</div>"""
        return shell(page_title="Register a claim", study=study, active="register",
                     actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                     actor_note=ctx["actor_note"], pending_count=ctx["pending_count"])
    banner = ""
    fals_missing = False
    if ctx.get("refusal"):
        fals_missing = not (v.get("falsifier") or "").strip()
        banner = banner_refusal(
            "Registration refused.", ctx["refusal"],
            "The engine refused this submission and nothing was written to the ledger. "
            "The state shown below is that refusal: the form exactly as submitted.")
    kind_options = "".join(
        f'<option value="{k}"{" selected" if v.get("kind") == k else ""}>{k}</option>'
        for k in ("data", "interpretation"))
    body = f"""
      <div class="crumb"><a href="/studies/{e(study['id'])}/">Claim register</a> · New claim</div>
      <h1>Register a claim</h1>
      <p class="page-sub">A registration is a signed snapshot appended to the study ledger. The statement is immutable from this moment; a change is a new claim that supersedes this one.</p>
      {banner}
      <div class="card">
        <form method="post" action="/studies/{e(study['id'])}/claims">
          <div class="grid2">
            <div class="field">
              <label for="cid">Claim ID</label>
              <input id="cid" name="claim_id" type="text" value="{e(v.get('claim_id', ''))}">
              <div class="help">CLM-&lt;study&gt;-&lt;number&gt;. Assigned once, never reused.</div>
            </div>
            <div class="field">
              <label for="kind">Kind</label>
              <select id="kind" name="kind">{kind_options}</select>
              <div class="help">Kind decides how evidence origins are grouped (WS2 §2).</div>
            </div>
          </div>
          <div class="field">
            <label for="stmt">Statement</label>
            <textarea id="stmt" name="statement" rows="3" placeholder="The claim, stated so that evidence could in principle refute it…">{e(v.get('statement', ''))}</textarea>
          </div>
          <div class="field{' required-missing' if fals_missing else ''}">
            <label for="fals">Falsifier <span class="req-chip">Required · Article II</span></label>
            <textarea id="fals" name="falsifier" rows="2" placeholder="The observation that would refute this claim…">{e(v.get('falsifier', ''))}</textarea>
            <div class="help"><strong>No falsifier, no registration.</strong> State what the source of record would have to show for this claim to be wrong. The register enforces this itself — this form cannot waive it, and neither can an adjudicator.</div>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="margin">Margin</label>
              <input id="margin" name="margin" type="text" value="{e(v.get('margin', ''))}" placeholder="e.g. 0.1">
              <div class="help">The verdict test's registered margin (WS3). Required before freeze.</div>
            </div>
            <div class="field">
              <label for="floor">Sufficiency floor</label>
              <input id="floor" name="sufficiency_floor" type="text" value="{e(v.get('sufficiency_floor', ''))}" placeholder="e.g. 1">
              <div class="help">Minimum independent origin groups. Required before freeze.</div>
            </div>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="deps">Dependencies</label>
              <input id="deps" name="dependencies" type="text" value="{e(v.get('dependencies', ''))}" placeholder="CLM-… , EVG-…">
              <div class="help">Claims or evidence groups this claim rests on. Circular support is rejected.</div>
            </div>
            <div class="field">
              <label for="sup">Supersedes</label>
              <input id="sup" name="supersedes" type="text" value="{e(v.get('supersedes', ''))}" placeholder="—">
              <div class="help">If this claim replaces an earlier one, name it; the link is recorded both ways.</div>
            </div>
          </div>
          <div class="row-actions">
            <button class="btn primary" type="submit">Register claim</button>
            <a class="btn" href="/studies/{e(study['id'])}/">Cancel</a>
            <span class="muted small">Submitting appends the claim under your name: <strong>{e(ctx['actor'])}</strong>.</span>
          </div>
        </form>
      </div>"""
    return shell(page_title="Register a claim", study=study, active="register",
                 actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                 actor_note=ctx["actor_note"], pending_count=ctx["pending_count"])


# ------------------------------------------------------------------ (c) claim detail

def _stage_cell(kind: str, payload: dict[str, Any]) -> str:
    if kind == "resolution":
        res = payload.get("resolution")
        if res == "resolved":
            detail = f'{e(payload.get("source") or "")} · {e(payload.get("source_id") or "")}'
            return f'<span class="chip stage-ok">resolved</span><br><span class="small muted">{detail}</span>'
        if res == "not_found":
            return '<span class="chip stage-bad">not found</span>'
        return '<span class="chip stage-bad">error</span>'
    if kind == "agreement":
        ag = payload.get("agreement")
        if ag == "agree":
            return '<span class="chip stage-ok">agree</span>'
        if ag == "disagree":
            miss = ", ".join(payload.get("mismatches") or [])
            return (f'<span class="chip stage-bad">disagree</span><br>'
                    f'<span class="small muted">mismatch: {e(miss)}</span>')
        return '<span class="muted">—</span>'
    content = payload.get("content")
    if content == "supports":
        return '<span class="chip stage-ok">supports</span>'
    if content == "contradicts":
        return '<span class="chip stage-bad">contradicts</span>'
    if content == "contextual":
        return '<span class="chip">contextual</span>'
    if content == "metadata_only":
        return '<span class="chip metaonly">metadata-only</span>'
    return '<span class="muted">—</span>'


def render_claim(ctx: dict[str, Any]) -> str:
    study = ctx["study"]
    claim = ctx["claim"]
    dead = ctx["dead"]
    sid = study["id"]
    status = _claim_status_chip(claim, dead, ctx["frozen_claims"])
    verdict = ctx["verdict"]
    if verdict:
        verdict_line = (f'{verdict_chip(verdict["verdict"])} '
                        f'<span class="muted">{e(verdict["reason"])}</span>')
    elif ctx["run_state"] == "invalid":
        verdict_line = ('<span class="muted">none — the study\'s run was INVALID '
                        "and issued no claim verdicts</span>")
    else:
        verdict_line = '<span class="muted">none — no verdict recorded for this claim</span>'
    deps = "none"
    if claim.dependencies:
        deps = ", ".join(
            f'<a href="/studies/{e(sid)}/claims/{e(d)}">{e(d)}</a>'
            if d.startswith("CLM-") else f'<span class="mono">{e(d)}</span>'
            for d in claim.dependencies)
    floor = claim.sufficiency_floor
    floor_text = ("not set" if floor is None else
                  f'{floor} independent origin group{"s" if floor != 1 else ""}')
    reg_hash = (f'<span class="mono">{e(ctx["registration_hash"])}</span>'
                if ctx["registration_hash"] else "not frozen")

    group_cards = ""
    for g in ctx["groups"]:
        items = g["items"]
        stances = ", ".join(sorted({it.stance for it in items})) or "—"
        meta_note = ""
        if g["metadata_only"]:
            meta_note = (' This group\'s content was never checked, so it contributes '
                         "<strong>no support mass and no falsifier exposure</strong> (RT-5). "
                         "A claim resting only on metadata-only groups is capped at INCONCLUSIVE.")
        group_cards += f"""
      <div class="card">
        <h3>{e(g['origin_group'])} {'<span class="chip metaonly">metadata-only</span>' if g['metadata_only'] else ''}</h3>
        <p class="muted" style="margin:0 0 10px">{len(items)} item{"s" if len(items) != 1 else ""} · stance: {e(stances)}.{meta_note}</p>
        <dl class="kv">
          <dt>Support mass</dt><dd>{g['support_mass']:.2f} (folded)</dd>
          <dt>Contradiction mass</dt><dd>{g['contradiction_mass']:.2f} (folded)</dd>
          <dt>Content coverage</dt><dd>{meter(ctx['cov_checked'], ctx['cov_groups'])}</dd>
        </dl>
      </div>"""
    if not ctx["groups"]:
        group_cards = ('<div class="card empty">No evidence groups yet. Attach a '
                       "citation below — it is checked by the pipeline and folded "
                       "to its origin group.</div>")

    cit_rows = ""
    for row in ctx["citations"]:
        p = row["payload"]
        cited = row["cited"]
        cited_line = ""
        if cited:
            bits = []
            if cited.get("title"):
                bits.append(f'“{e(cited["title"])}”')
            authors = cited.get("authors") or []
            if authors:
                bits.append(e(authors[0].split()[-1] if authors[0] else ""))
            if cited.get("year"):
                bits.append(str(cited["year"]))
            cited_line = f'<br><span class="small muted">cited as {", ".join(bits)}</span>'
        elif p.get("source_id"):
            cited_line = f'<br><span class="small muted mono">{e(p["source_id"])}</span>'
        cit_rows += f"""
            <tr>
              <td data-h="Citation"><span class="mono">{e(p['citation_id'])}</span>{cited_line}</td>
              <td data-h="Stage 1 · Resolution">{_stage_cell('resolution', p)}</td>
              <td data-h="Stage 2 · Agreement">{_stage_cell('agreement', p)}</td>
              <td data-h="Stage 3 · Content">{_stage_cell('content', p)}</td>
              <td data-h="Group" class="mono" style="white-space:nowrap">{e(p.get('origin_group') or '—')}</td>
              <td data-h="Disposition">{row['disposition']}</td>
            </tr>"""
    if not ctx["citations"]:
        cit_rows = ('<tr><td colspan="6" class="empty">No citations checked for '
                    "this claim yet.</td></tr>")

    retrieved_cards = ""
    for rec in ctx["retrieved"]:
        p = rec["payload"]
        r = rec["record"]
        authors = ", ".join(r.get("authors") or [])
        avy = " · ".join(x for x in [authors, r.get("venue") or "",
                                     str(r.get("year") or "")] if x)
        if r.get("content_included"):
            content_line = ("included — its licence basis permits redistribution (WS5 §4)")
        else:
            content_line = ("not included — licence permits no redistribution (WS5 §4); "
                            "the retrieved record above states the licence basis instead")
        retrieved_cards += f"""
      <div class="card">
        <h3>Retrieved record — {e(p['citation_id'])} ({e((p.get('source') or '').capitalize())}, source of record)</h3>
        <dl class="kv">
          <dt>Title</dt><dd class="serif">{e(r.get('title') or '—')}</dd>
          <dt>Author / venue / year</dt><dd>{e(avy or '—')}</dd>
          <dt>Licence basis</dt><dd class="mono">{e(r.get('license_basis') or '—')}</dd>
          <dt>Content in bundle</dt><dd>{content_line}</dd>
          <dt>Extractor</dt><dd class="mono">{e(p.get('extractor') or '—')}</dd>
        </dl>
      </div>"""

    actions = ""
    if ctx["can_mutate"] and dead is None:
        actions = f"""
      <div class="row-actions">
        <a class="btn" href="#attach">Attach a citation</a>
        <a class="btn danger" href="#withdraw">Withdraw claim (marks it dead)</a>
        <span class="muted small">Withdrawal is a dead snapshot with a mandatory reason — the claim stays in the register, shown dead. There is no delete.</span>
      </div>
      <div class="card" id="attach">
        <h3>Attach a citation</h3>
        <form method="post" action="/studies/{e(sid)}/claims/{e(claim.claim_id)}/citations">
          <div class="grid2">
            <div class="field">
              <label for="cit-id">Citation ID</label>
              <input id="cit-id" name="citation_id" type="text" placeholder="CIT-…">
            </div>
            <div class="field">
              <label for="cit-doi">DOI</label>
              <input id="cit-doi" name="doi" type="text" placeholder="10.…">
              <div class="help">Resolved against the source of record (Crossref). No DOI: matched on title + authors + venue + year (WS5 §1.1).</div>
            </div>
          </div>
          <div class="field">
            <label for="cit-prop">Proposition</label>
            <textarea id="cit-prop" name="proposition" rows="2" placeholder="The finding this citation is cited for…"></textarea>
            <div class="help">Stage 3 checks the retrieved content against this proposition — never against a model's memory of the paper.</div>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="cit-title">Cited title</label>
              <input id="cit-title" name="title" type="text">
            </div>
            <div class="field">
              <label for="cit-authors">Cited authors</label>
              <input id="cit-authors" name="authors" type="text" placeholder="Surname, …">
            </div>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="cit-year">Cited year</label>
              <input id="cit-year" name="year" type="text">
            </div>
            <div class="field">
              <label for="cit-venue">Cited venue</label>
              <input id="cit-venue" name="venue" type="text">
            </div>
          </div>
          <div class="grid2">
            <div class="field">
              <label for="cit-dataset">Dataset / registration ID</label>
              <input id="cit-dataset" name="dataset_id" type="text">
              <div class="help">WS2 grouping key 2: two papers from one dataset are one origin for data claims.</div>
            </div>
            <div class="field">
              <label for="cit-derived">Derived from</label>
              <input id="cit-derived" name="derived_from" type="text" placeholder="CIT-…">
              <div class="help">WS2 grouping key 3: an explicit derivation link to another citation.</div>
            </div>
          </div>
          <div class="row-actions">
            <button class="btn primary" type="submit">Check citation</button>
            <span class="muted small">The outcome — resolved, not found, or error — is appended to the ledger either way (K1 accounting). A mismatch quarantines the citation for adjudication.</span>
          </div>
        </form>
      </div>
      <div class="card" id="withdraw">
        <h3>Withdraw this claim</h3>
        <form method="post" action="/studies/{e(sid)}/claims/{e(claim.claim_id)}/withdraw">
          <div class="field">
            <label for="wd-reason">Reason <span class="req-chip">Required · DN-005</span></label>
            <input id="wd-reason" name="reason" type="text" placeholder="Why this claim is withdrawn — recorded verbatim">
            <div class="help">Withdrawal appends a dead snapshot: status dead, this reason, score 0.0. The claim remains in the register, shown dead. History is not rewritten.</div>
          </div>
          <div class="row-actions">
            <button class="btn danger" type="submit">Withdraw claim (marks it dead)</button>
          </div>
        </form>
      </div>"""
    dead_panel = ""
    if dead is not None:
        dead_panel = f"""
      <div class="card">
        <h3>{chip('DEAD', 'dead')} Withdrawn</h3>
        <dl class="kv">
          <dt>Reason</dt><dd>“{e(dead['reason'])}”</dd>
          <dt>Score</dt><dd class="mono">{e(dead['score'] if dead['score'] is not None else 0.0)}</dd>
        </dl>
        <p class="muted small" style="margin:10px 0 0">A dead record stays in the register, shown dead (DN-005). It takes no verdict and no new evidence.</p>
      </div>"""

    body = f"""
      <div class="crumb"><a href="/studies/{e(sid)}/">Claim register</a> · {e(claim.claim_id)}</div>
      <h1>{e(claim.claim_id)} {status} {chip('kind: ' + claim.kind)}</h1>
      <p class="page-sub serif" style="font-size:17px;color:var(--ink)">“{e(claim.statement)}”</p>
      {banner_refusal('Refused.', ctx['refusal']) if ctx.get('refusal') else ''}
      <div class="card">
        <h3>Falsifier</h3>
        <p style="margin:0">{e(claim.falsifier)}</p>
        <hr style="border:none;border-top:1px solid var(--line);margin:14px 0">
        <dl class="kv">
          <dt>Margin</dt><dd>{e(claim.margin if claim.margin is not None else 'not set')}</dd>
          <dt>Sufficiency floor</dt><dd>{e(floor_text)}</dd>
          <dt>Dependencies</dt><dd>{deps}</dd>
          <dt>Registration hash</dt><dd>{reg_hash}</dd>
          <dt>Verdict</dt><dd>{verdict_line}</dd>
        </dl>
      </div>
      {dead_panel}
      <h2>Evidence — origin groups</h2>
      {group_cards}
      <h2>Citations — pipeline outcomes</h2>
      <div class="card flush">
        <table>
          <thead>
            <tr><th>Citation</th><th>Stage 1 · Resolution</th><th>Stage 2 · Agreement</th><th>Stage 3 · Content</th><th>Group</th><th>Disposition</th></tr>
          </thead>
          <tbody>{cit_rows}
          </tbody>
        </table>
      </div>
      {retrieved_cards}
      {actions}"""
    return shell(page_title=claim.claim_id, study=study, active="register",
                 actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                 actor_note=ctx["actor_note"], pending_count=ctx["pending_count"])


# ------------------------------------------------------------------ (d) queue

def _stage_outcomes_text(item: dict[str, Any]) -> str:
    res = item.get("result") or {}
    if not res:
        ids = item.get("citation_ids") or []
        return f'citations <span class="mono">{e(", ".join(ids))}</span>'
    parts = [f'resolution <strong>{e(res.get("resolution") or "—")}</strong>']
    if res.get("agreement"):
        miss = f' ({e(", ".join(res.get("mismatches") or []))})' if res.get("mismatches") else ""
        parts.append(f'agreement <strong>{e(res["agreement"])}</strong>{miss}')
    else:
        parts.append("agreement —")
    if res.get("content") == "metadata_only":
        parts.append('content <span class="chip metaonly">metadata-only</span>')
    elif res.get("content"):
        parts.append(f'content <strong>{e(res["content"])}</strong>')
    else:
        parts.append("content —")
    return " · ".join(parts)


def _queue_item_head(item: dict[str, Any], *, pending: bool) -> str:
    kind = item.get("kind", "")
    kind_chip = chip(kind, "inconclusive" if kind == "quarantine" else "brand")
    head = f'<span class="mono">{e(item["queue_id"])}</span> {kind_chip}'
    if pending:
        head += ' <span class="chip invalid">PENDING</span>'
    else:
        dec = item.get("decision") or ""
        dec_cls = "contradicted" if dec == "exclude" else "brand"
        head += f' {chip("decision: " + dec.replace("_", " "), dec_cls)}'
        reviews = item.get("second_reviews") or []
        if reviews:
            last = reviews[-1]
            head += (' <span class="chip stage-ok">2nd review: agreed</span>'
                     if last["agrees"] else
                     ' <span class="chip contradicted">2nd review: disagreed</span>')
    return head


def render_queue(ctx: dict[str, Any]) -> str:
    study = ctx["study"]
    sid = study["id"]
    q = ctx["queue"]
    pending_cards = ""
    for item in q["pending"]:
        form = ""
        if ctx["can_decide"]:
            buttons = "".join(
                f'<button class="btn" type="submit" name="decision" value="{d}">'
                f'{d.replace("_", " ").capitalize()}</button>'
                for d in ("exclude", "variant", "same_origin", "separate_origin"))
            form = f"""
        <form method="post" action="/studies/{e(sid)}/queue/{e(item['queue_id'])}/decide">
          <div class="field">
            <label>Rationale</label>
            <textarea name="rationale" rows="2" placeholder="Why — recorded verbatim with the decision, under your name…"></textarea>
            <div class="help">A decision is an appended event. Deciding twice is refused by the engine: a changed decision is a new adjudication, not an edit.</div>
          </div>
          <div class="field">
            <label>Decision</label>
            <div class="row-actions" style="margin:0">{buttons}</div>
          </div>
        </form>"""
        pending_cards += f"""
      <div class="card">
        <h3>{_queue_item_head(item, pending=True)}</h3>
        <dl class="kv">
          <dt>Reason queued</dt><dd>{e(item.get('reason', ''))}</dd>
          <dt>Citation</dt><dd>{_queue_citation_ref(item, sid)}</dd>
          <dt>Stage outcomes</dt><dd>{_stage_outcomes_text(item)}</dd>
        </dl>{form}
      </div>"""
    if not q["pending"]:
        pending_cards = ('<div class="card empty">No pending items. New quarantines '
                         "(unresolved or disagreeing citations) and grouping suspects "
                         "will appear here.</div>")

    decided_cards = ""
    for item in q["decided"]:
        reviews = item.get("second_reviews") or []
        if reviews:
            last = reviews[-1]
            review_line = (f'sampled under RT-4 · reviewer <strong>{e(last["reviewer"])}</strong> · '
                           f'<strong>{"agrees" if last["agrees"] else "disagrees"}</strong>')
        elif item["queue_id"] in ctx["sampled_unreviewed"]:
            review_line = "sampled under RT-4 · awaiting second review"
            if ctx["can_review"]:
                review_line += f"""
        <form method="post" action="/studies/{e(sid)}/queue/{e(item['queue_id'])}/second-review" style="margin-top:8px">
          <div class="row-actions" style="margin:0">
            <button class="btn" type="submit" name="agrees" value="yes">Agrees</button>
            <button class="btn" type="submit" name="agrees" value="no">Disagrees</button>
            <span class="muted small">Recorded under your name: {e(ctx['actor'])}.</span>
          </div>
        </form>"""
        else:
            review_line = "not sampled"
        decided_cards += f"""
      <div class="card">
        <h3>{_queue_item_head(item, pending=False)}</h3>
        <dl class="kv">
          <dt>Reason queued</dt><dd>{e(item.get('reason', ''))}</dd>
          <dt>Citation</dt><dd>{_queue_citation_ref(item, sid)}</dd>
          <dt>Stage outcomes</dt><dd>{_stage_outcomes_text(item)}</dd>
          <dt>Decided by</dt><dd>{e(item.get('decided_by', ''))}</dd>
          <dt>Rationale</dt><dd class="serif">“{e(item.get('rationale', ''))}”</dd>
          <dt>Second review</dt><dd>{review_line}</dd>
        </dl>
      </div>"""
    if not q["decided"]:
        decided_cards = ('<div class="card empty">No decisions yet. Decided items, '
                         "their rationales, and their second reviews appear here.</div>")

    rep = q["report"]
    if rep["anomaly"]:
        anomaly_line = f'<strong>{e(rep["anomaly_reason"])}</strong>'
    elif rep["second_reviews"] < 5:
        anomaly_line = (f'<strong>Anomaly: none</strong> (window below the minimum '
                        f'of 5)')
    else:
        anomaly_line = "<strong>Anomaly: none</strong>"
    sampling_card = f"""
      <div class="card">
        <h3>Second-review sampling (RT-4)</h3>
        <p style="margin:0" class="muted">Decisions are sampled deterministically (registered fraction {int(ctx['fraction'] * 100)}%, seeded) for independent second review. Current window: <strong>{rep['second_reviews']} review{"s" if rep['second_reviews'] != 1 else ""}, {rep['disagreements']} disagreement{"s" if rep['disagreements'] != 1 else ""}</strong>. A reviewed window of 5+ with zero disagreements is flagged as a rubber-stamp anomaly — a queue that never disagrees is treated like a control that never fails. {anomaly_line}.</p>
      </div>"""

    body = f"""
      <div class="crumb">Study · {e(sid)}</div>
      <h1>Adjudication queue</h1>
      <p class="page-sub">Quarantined citations and grouping suspects wait here for a named human decision. Quarantined items contribute no evidence until decided.</p>
      {banner_refusal('Decision refused.', ctx['refusal']) if ctx.get('refusal') else ''}
      <div class="stats">
        <div class="stat"><div class="num">{len(q['pending'])}</div><div class="lab">Pending</div></div>
        <div class="stat"><div class="num">{len(q['decided'])}</div><div class="lab">Decided</div></div>
        <div class="stat"><div class="num">{q['reviews']}</div><div class="lab">Second reviews (RT-4)</div></div>
        <div class="stat"><div class="num">{q['disagreements']}</div><div class="lab">Disagreements</div></div>
      </div>
      <h2>Pending</h2>
      {pending_cards}
      <h2>Decided</h2>
      {decided_cards}
      {sampling_card}"""
    return shell(page_title="Adjudication queue", study=study, active="queue",
                 actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                 actor_note=ctx["actor_note"], pending_count=len(q["pending"]))


def _queue_citation_ref(item: dict[str, Any], sid: str) -> str:
    if item.get("citation_id"):
        ref = f'<span class="mono">{e(item["citation_id"])}</span>'
        if item.get("claim_id"):
            ref += (f' · claim <a href="/studies/{e(sid)}/claims/{e(item["claim_id"])}">'
                    f'{e(item["claim_id"])}</a>')
        return ref
    ids = item.get("citation_ids") or []
    return ", ".join(f'<span class="mono">{e(i)}</span>' for i in ids) or "—"


# ------------------------------------------------------------------ (e) freeze & verdicts

_CONTROL_KIND_HELP = {
    "positive": "Known-true claim in the study's domain; the run must support it.",
    "negative": "False claim; the run must contradict it.",
    "swap": "Provenance swap; the ledger verifier must detect it (RT-1).",
}


def _fmt_interval(interval: Any) -> str:
    if not interval:
        return "—"
    return f"[{interval[0]:.2f}, {interval[1]:.2f}]"


def _controls_cards(fields: list[dict[str, Any]], *, doc_present: bool) -> str:
    cards = ""
    for f in fields:
        expected = f.get("expected")
        expected_txt = (f'designed to be judged <strong>{e(expected.upper())}</strong>'
                        if expected else
                        "must be <strong>detected</strong> by production verification")
        has_fixture = "fixture" in f
        cards += f"""
      <div class="card">
        <h3>{chip(f.get('kind', ''))} {e(f.get('failure_mode', ''))}</h3>
        <p class="muted" style="margin:0 0 10px">{e(_CONTROL_KIND_HELP.get(f.get('kind', ''), ''))} This control is {expected_txt}.</p>
        <dl class="kv">
          <dt>Rationale (registered)</dt><dd class="serif">“{e(f.get('representative_rationale', ''))}”</dd>
          <dt>Run fixture</dt><dd>{'held by the workspace — the run executes this control' if has_fixture else 'none held — the run executes the swap control and any fixture-backed control only'}</dd>
        </dl>
      </div>"""
    if not fields:
        cards = ('<div class="card empty">The workspace holds no copy of the frozen '
                 "registration document for this study, so its registered controls "
                 "cannot be listed here. The engine still enforces the frozen "
                 "document by hash at export; the swap control still runs.</div>"
                 if doc_present else
                 '<div class="card empty">No controls registered yet — the freeze '
                 "form below registers them.</div>")
    return cards


def _verdict_rows(ctx: dict[str, Any]) -> str:
    rows = ""
    for v in ctx["verdict_rows"]:
        rows += f"""
            <tr>
              <td data-h="Claim" class="mono"><a href="/studies/{e(ctx['study']['id'])}/claims/{e(v['claim_id'])}">{e(v['claim_id'])}</a></td>
              <td data-h="Verdict">{verdict_chip(v['verdict'])}</td>
              <td data-h="Reason">{e(v['reason'])}</td>
              <td data-h="Interval" class="mono">{e(_fmt_interval(v.get('interval')))}</td>
            </tr>"""
    if not rows:
        rows = ('<tr><td colspan="4" class="empty">No claim verdicts — if the latest '
                "run was INVALID, none can exist for it (WS3 §1).</td></tr>")
    return rows


def render_freeze(ctx: dict[str, Any]) -> str:
    study = ctx["study"]
    sid = study["id"]
    run = ctx["run"]
    invalid_block = ""
    if run["state"] == "invalid":
        reasons = "; ".join(run["reasons"])
        invalid_block = f"""
      <div class="run-invalid">
        <div class="run-head">RUN VERDICT: INVALID</div>
        <p style="margin:0">The run-level checks returned these failure reasons from the engine: <span class="mono">{e(reasons)}</span>. By the verdict taxonomy (Article VI), a failed run-level check voids the run — no claim verdicts are issued from it, and no claim inherits a verdict it did not earn. The correct response is to fix the cause, re-freeze if the registration must change, and re-run; never to read verdicts off a failed run.</p>
      </div>"""
    run_btn = ""
    if ctx["can_run"] and ctx["frozen"] and run["state"] in ("not-run", "invalid"):
        run_btn = f"""
      <form method="post" action="/studies/{e(sid)}/run">
        <div class="row-actions">
          <button class="btn primary" type="submit">Run evaluation</button>
          <span class="muted small">A run evaluates the frozen registration, its controls, and every claim against its evidence. A valid run's verdicts are appended under your name; an INVALID run appends nothing (WS3 §1).</span>
        </div>
      </form>"""
    reg_card = ""
    freeze_form = ""
    if ctx["frozen"]:
        fe = ctx["frozen"]
        linked = fe["linked"]
        linked_txt = (", ".join(linked) if linked
                      else "none — <strong>empty discloses none, explicitly</strong> (FR-011)")
        reg_card = f"""
      <div class="card">
        <h3>Registration (frozen)</h3>
        <dl class="kv">
          <dt>Registration hash</dt><dd class="mono">{e(fe['registration_hash'])}</dd>
          <dt>Mode</dt><dd>{e(fe['mode'])}{(' · ' + e(ctx['deployment_shape'])) if ctx.get('deployment_shape') else ''}</dd>
          <dt>Frozen by</dt><dd>{e(fe['actor'])}</dd>
          <dt>Claims in registration</dt><dd class="mono">{e(', '.join(fe['claims']))}</dd>
          <dt>Linked exploratory</dt><dd>{linked_txt}</dd>
          <dt>Merkle checkpoint at freeze</dt><dd class="mono">{e(ctx['freeze_root'] or '—')}</dd>
        </dl>
      </div>"""
    elif ctx["can_freeze"]:
        control_fieldsets = ""
        for i, f in enumerate(ctx["control_defaults"]):
            kind = f["kind"]
            control_fieldsets += f"""
        <div class="card">
          <h3>{chip(kind)} Control {i + 1} — {e(kind)}</h3>
          <div class="field">
            <label>Failure mode</label>
            <input name="ctl{i}_failure_mode" type="text" value="{e(f.get('failure_mode', ''))}">
            <div class="help">{e(_CONTROL_KIND_HELP.get(kind, ''))}</div>
          </div>
          <div class="grid2">
            <div class="field">
              <label>Expected outcome</label>
              <input name="ctl{i}_expected" type="text" value="{e(f.get('expected') or '')}" placeholder="{'supported / contradicted' if kind != 'swap' else 'detection (leave empty)'}">
            </div>
            <div class="field">
              <label>Representative rationale</label>
              <input name="ctl{i}_rationale" type="text" value="{e(f.get('representative_rationale', ''))}">
            </div>
          </div>
        </div>"""
        freeze_form = f"""
      <form method="post" action="/studies/{e(sid)}/freeze">
        <div class="card">
          <h3>Freeze the registration</h3>
          <p class="muted" style="margin-top:0">A freeze seals the register as it stands: claims, margins, floors, and the controls below. The engine refuses a freeze whose checks fail — every claim needs a margin and a floor, the run controls must be satisfiable, and a confirmation freeze must disclose its linked exploratory studies, explicitly including none.</p>
          <div class="grid2">
            <div class="field">
              <label for="f-mode">Mode</label>
              <select id="f-mode" name="mode">
                <option value="confirmation" selected>confirmation</option>
                <option value="exploratory">exploratory</option>
              </select>
            </div>
            <div class="field">
              <label for="f-shape">Deployment shape</label>
              <select id="f-shape" name="deployment_shape">
                <option value="hosted" selected>hosted</option>
                <option value="self-hosted">self-hosted</option>
              </select>
            </div>
          </div>
          <div class="field">
            <label for="f-linked">Linked exploratory studies</label>
            <input id="f-linked" name="linked_exploratory" type="text" placeholder="study ids, comma-separated — or leave empty">
            <div class="help"><strong>Empty discloses none — explicitly.</strong> For a confirmation freeze the engine records the empty list in the registration itself; it is a disclosure, not an omission (FR-011).</div>
          </div>
        </div>
        {control_fieldsets}
        <div class="row-actions">
          <button class="btn primary" type="submit">Freeze registration</button>
          <span class="muted small">Freezing appends <span class="mono">study.frozen</span> and a Merkle checkpoint under your name: {e(ctx['actor'])}.</span>
        </div>
      </form>"""
    else:
        reg_card = ('<div class="card empty">This study is not frozen. Freezing is an '
                    "adjudicator action (WS6 §1); this view offers no freeze form.</div>")

    body = f"""
      <div class="crumb">Study · {e(sid)}</div>
      <h1>Freeze &amp; verdicts</h1>
      <p class="page-sub">The freeze seals the registration before outcomes are read. Verdicts are computed only from frozen registrations, and only from valid runs.</p>
      {banner_refusal('Freeze refused.', ctx['refusal']) if ctx.get('refusal') else ''}
      {reg_card}
      {freeze_form}
      <h2>Registered run controls</h2>
      {_controls_cards(ctx['control_fields'], doc_present=bool(ctx['control_fields']))}
      {invalid_block}
      {run_btn}
      <h2>Claim verdicts</h2>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:14%">Claim</th><th style="width:16%">Verdict</th><th style="width:52%">Reason</th><th style="width:18%">Interval</th></tr>
          </thead>
          <tbody>{_verdict_rows(ctx)}
          </tbody>
        </table>
      </div>
      <p class="muted small">Taxonomy: <strong>SUPPORTED</strong> and <strong>CONTRADICTED</strong> require the registered falsifier to have been genuinely at risk — a capable falsifier test that could have observed the refuting outcome (Article VI). <strong>INCONCLUSIVE</strong> is a verdict, not an embarrassment: it is what the evidence honestly buys.</p>"""
    return shell(page_title="Freeze & verdicts", study=study, active="freeze",
                 actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                 actor_note=ctx["actor_note"], pending_count=ctx["pending_count"])


# ------------------------------------------------------------------ (f) export & anchor

_MECHANISM_LABELS = {
    "zenodo": "Zenodo deposit (DOI)",
    "local-filesystem": "Local filesystem (test transport)",
}


def _anchor_card(receipt: dict[str, Any], *, public_check: Optional[dict] = None) -> str:
    mech = receipt.get("mechanism", "")
    label = _MECHANISM_LABELS.get(mech, mech)
    f = receipt.get("file") or {}
    locator = receipt.get("doi") or receipt.get("locator") or ""
    locator_txt = f'<a href="https://doi.org/{e(locator)}">{e(locator)}</a>' if receipt.get("doi") else e(locator)
    verify_row = ""
    if public_check is not None:
        if public_check["ok"]:
            verify_row = (f'<dt>Verified against the public record</dt><dd>'
                          f'<span class="chip stage-ok">verified</span> · bundle verifies; '
                          f"root and bundle hash match the deposit record; "
                          f"file MD5 matches</dd>")
        else:
            verify_row = (f'<dt>Verified against the public record</dt><dd>'
                          f'<span class="chip invalid">FAILED</span> '
                          f'<span class="mono">{e("; ".join(public_check["failures"]))}</span></dd>')
    return f"""
      <div class="card">
        <h3>{e(label)} · <span class="mono">{locator_txt}</span></h3>
        <dl class="kv">
          <dt>Anchored checkpoint root</dt><dd class="mono">{e(receipt.get('root', ''))}</dd>
          <dt>Bundle hash</dt><dd class="mono">{e(receipt.get('bundle_hash', ''))}</dd>
          <dt>Anchored at</dt><dd>{e((receipt.get('anchored_at') or '').replace('T', ' ').rstrip('Z'))} UTC</dd>
          <dt>Deposited file</dt><dd>{e(f.get('name', ''))} · {f.get('bytes', 0):,} bytes · MD5 <span class="mono">{e(f.get('md5', ''))}</span></dd>
          <dt>Approved by</dt><dd>{e(receipt.get('approved_by', ''))}</dd>
          <dt>Receipt in record</dt><dd><span class="mono">anchor.recorded</span> · seq {receipt.get('_seq')}</dd>
          {verify_row}
        </dl>
      </div>"""


def render_export(ctx: dict[str, Any]) -> str:
    study = ctx["study"]
    sid = study["id"]
    current = ctx["current_export"]
    if current is None:
        current_card = ('<div class="card empty">No bundle has been exported from '
                        "this workspace yet. Export packages the whole record — "
                        "ledger byte-for-byte — and verifies before it reports.</div>")
    else:
        ver = current["verification"]
        if ver is None:
            ver_dd = ('bundle produced by another workspace path — not held here, '
                      "so it is not shown verified")
        elif ver["ok"]:
            ver_dd = ('<span class="chip stage-ok">verified</span> · from the bundle '
                      "alone, no live ledger consulted")
        else:
            ver_dd = (f'<span class="chip invalid">FAILED</span> '
                      f'<span class="mono">{e("; ".join(ver["failures"]))}</span>')
        current_card = f"""
      <div class="card">
        <h3>{e(current['name'])}</h3>
        <dl class="kv">
          <dt>Bundle hash</dt><dd class="mono">{e(current['bundle_hash'])}</dd>
          <dt>Ledger events</dt><dd>{current['event_count']} · head checkpoint root <span class="mono">{e(short_hash(current['head_root']))}</span></dd>
          <dt>Exported by</dt><dd>{e(current['actor'])} · <span class="mono">export.generated</span> · seq {current['seq']}</dd>
          <dt>Standalone verification</dt><dd>{ver_dd}</dd>
        </dl>
      </div>"""
    export_btn = ""
    if ctx["can_export"]:
        export_btn = f"""
        <form method="post" action="/studies/{e(sid)}/export">
          <div class="row-actions">
            <button class="btn primary" type="submit">Export audit bundle</button>
            <span class="muted small">The engine refuses an export of an unfrozen study, or one whose registration hash does not match the freeze — the refusal is shown, not hidden.</span>
          </div>
        </form>"""
    anchor_cards = "".join(
        _anchor_card(r, public_check=ctx["public_checks"].get(r.get("_seq")))
        for r in reversed(ctx["anchors"]))
    if not ctx["anchors"]:
        anchor_cards = ('<div class="card empty">No anchor receipt in this record. '
                        "An anchor commits a bundle's Merkle root to an external, "
                        "timestamped public record (Article VII) — deposits appear "
                        "here as receipts.</div>")
    verify_form = f"""
      <div class="card">
        <h3>Verify a bundle</h3>
        <form method="post" action="/studies/{e(sid)}/verify-bundle">
          <div class="field">
            <label for="vb-path">Bundle directory</label>
            <input id="vb-path" name="bundle_path" type="text" value="{e(ctx.get('verify_path') or '')}" placeholder="/path/to/bundle">
            <div class="help">The standalone verifier consumes the bundle alone — the same check anyone holding the deposit can run.</div>
          </div>
          <div class="row-actions">
            <button class="btn" type="submit">Verify bundle</button>
          </div>
        </form>
        {ctx.get('verify_result_html') or ''}
      </div>"""
    deposit_card = ""
    if ctx["deposit"] is not None:
        dep = ctx["deposit"]
        if dep.get("request"):
            deposit_card = f"""
      <div class="card">
        <h3>Deposit for anchoring</h3>
        <p class="muted" style="margin:0 0 12px">A deposit needs an adjudicator's approval, and the approval is recorded with the deposit itself — three separate ledger events, three separate names possible. This view cannot approve one.</p>
        <div class="row-actions" style="margin:0">
          <a class="btn primary" href="{e(dep['link'])}">Request deposit approval</a>
          <span class="muted small">Opens this page in the adjudicator view, where approval and deposit happen.</span>
        </div>
      </div>"""
        elif dep["available"]:
            deposit_card = f"""
      <div class="card">
        <h3>Deposit for anchoring</h3>
        <p class="muted" style="margin-top:0">Deposit requires an adjudicator's approval, recorded in the anchor receipt itself. The deposit on this workspace runs through: <strong>{e(dep['transport_label'])}</strong>{' — a test transport; receipts from it are labelled as such, never presented as a public anchor' if dep['transport_is_test'] else ''}.</p>
        <form method="post" action="/studies/{e(sid)}/deposit">
          <div class="field">
            <label for="dep-approval">Approved by</label>
            <input id="dep-approval" name="approved_by" type="text" value="{e(ctx['actor'])}">
            <div class="help">The engine refuses a deposit without an approval; the approval is written into the receipt that lands on the ledger.</div>
          </div>
          <div class="row-actions">
            <button class="btn primary" type="submit">Deposit latest export</button>
          </div>
        </form>
      </div>"""
        else:
            deposit_card = f"""
      <div class="card">
        <h3>Deposit for anchoring</h3>
        <p class="muted" style="margin:0">{e(dep['reason'])}</p>
      </div>"""
    body = f"""
      <div class="crumb">Study · {e(sid)}</div>
      <h1>Export &amp; anchor</h1>
      <p class="page-sub">The audit bundle is the whole record, exportable and verifiable by anyone. Anchoring commits its Merkle root beyond this ledger.</p>
      {banner_refusal('Refused.', ctx['refusal']) if ctx.get('refusal') else ''}
      <h2>Current bundle</h2>
      {current_card}
      {export_btn}
      <h2>Anchoring receipt</h2>
      {anchor_cards}
      {deposit_card}
      <h2>Standalone verification</h2>
      {verify_form}"""
    return shell(page_title="Export & anchor", study=study, active="export",
                 actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                 actor_note=ctx["actor_note"], pending_count=ctx["pending_count"])


# ------------------------------------------------------------------ (g) specimens

def render_specimens(ctx: dict[str, Any]) -> str:
    demo_sid = ctx.get("demo_sid") or ""
    legend = " ".join(
        f'<span style="margin-right:6px">{verdict_chip(v)}</span>'
        for v in ("supported", "inconclusive", "contradicted")) + \
        f'{chip("INVALID (runs only)", "invalid")}<br>' + \
        f'<span style="margin-right:6px">{chip("metadata-only", "metaonly")}</span>' + \
        f'{chip("DEAD", "dead")}'
    demo_link = (f'<a href="/studies/{e(demo_sid)}/">the demo study register</a>'
                 if demo_sid else "the claim register")
    body = f"""
      <div class="crumb">Wireframe package · specimens</div>
      <h1>Component specimens</h1>
      <p class="page-sub"><strong>Design specimens — component states, not study data.</strong> The record in {demo_link} contains no dead claim, no pending adjudication, and no claim verdicts (its run was INVALID). The states it lacks are rendered here from the same production components, with specimen values, so the design is complete and reviewable. Their falsifiers are the Phase 6 claims in specs/002-mvp-implementation.</p>
      <h2>Verdict &amp; status badges</h2>
      <div class="card">
        {legend}
        <p class="muted small" style="margin:10px 0 0">Chips are the only carriers of verdict and status colour (WIREFRAMES.md §4). INVALID belongs to runs, never to claims; DEAD belongs to withdrawn records.</p>
      </div>
      <h2>Dead claim — register row (specimen)</h2>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:16%">Claim</th><th style="width:44%">Statement</th><th style="width:26%">Status</th><th style="width:14%">Score</th></tr>
          </thead>
          <tbody>
            <tr class="dead-row">
              <td data-h="Claim" class="mono">CLM-SPEC-009 {chip('DEAD', 'dead')}</td>
              <td data-h="Statement" class="statement"><span class="dead-statement">Sleep restriction raises next-day error rates by at least 20% in the replication sample.</span></td>
              <td data-h="Status">dead · reason: “withdrawn by the researcher — superseded protocol made the claim untestable”</td>
              <td data-h="Score" class="mono">0.0</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="muted small">A dead claim is never omitted and never shown as a live claim with a footnote: muted row, struck statement, DEAD chip, the verbatim withdrawal reason, score 0.0 (DN-005).</p>
      <h2>Valid-run banner (specimen)</h2>
      <div class="banner-valid">
        <strong>Latest run: valid.</strong> Claim verdicts were issued and are recorded in the register.
      </div>
      <h2>Pending adjudication — decision control (specimen)</h2>
      <div class="card">
        <h3><span class="mono">ADQ-SPEC</span> {chip('quarantine', 'inconclusive')} <span class="chip invalid">PENDING</span></h3>
        <dl class="kv">
          <dt>Reason queued</dt><dd>resolution failed — spec: no such record at the source</dd>
          <dt>Citation</dt><dd><span class="mono">CIT-SPEC</span> · claim <span class="mono">CLM-SPEC-001</span></dd>
          <dt>Stage outcomes</dt><dd>resolution <strong>not_found</strong> · agreement — · content —</dd>
        </dl>
        <div class="field">
          <label>Rationale</label>
          <textarea rows="2" placeholder="Why — recorded verbatim with the decision, under your name…"></textarea>
          <div class="help">Specimen control: on a live queue item this form posts to the engine's decision service; here it renders the control only.</div>
        </div>
        <div class="field">
          <label>Decision</label>
          <div class="row-actions" style="margin:0">
            <button class="btn" type="button">Exclude</button>
            <button class="btn" type="button">Variant</button>
            <button class="btn" type="button">Same origin</button>
            <button class="btn" type="button">Separate origin</button>
          </div>
        </div>
      </div>
      <h2>Content-coverage meter (specimen)</h2>
      <div class="card">
        <dl class="kv">
          <dt>Content coverage</dt><dd>{meter(2, 5)}</dd>
        </dl>
        <p class="muted small" style="margin:10px 0 0">The numeric fraction is always printed beside the bar, and the percentage never rounds up (WS5 §2): a reader must be able to see at a glance that most of a claim's evidence was never content-checked.</p>
      </div>
      <h2>Role views (WS6 §1)</h2>
      <div class="card flush">
        <table>
          <thead>
            <tr><th>Role</th><th>Sees</th><th>Can append</th><th>Cannot</th></tr>
          </thead>
          <tbody>
            <tr><td data-h="Role"><strong>Researcher</strong></td><td data-h="Sees">register, claim detail, queue (read), freeze (read), export</td><td data-h="Can append">claims, citations, queries</td><td data-h="Cannot">adjudicate, freeze, run, deposit</td></tr>
            <tr><td data-h="Role"><strong>Reviewer</strong></td><td data-h="Sees">register, claim detail, queue</td><td data-h="Can append">second reviews</td><td data-h="Cannot">register claims, adjudicate, freeze</td></tr>
            <tr><td data-h="Role"><strong>Adjudicator</strong></td><td data-h="Sees">everything</td><td data-h="Can append">decisions, freezes, runs, deposits</td><td data-h="Cannot">edit or delete — no one can</td></tr>
            <tr><td data-h="Role"><strong>Integrity</strong></td><td data-h="Sees">everything, read-only</td><td data-h="Can append">nothing</td><td data-h="Cannot">every mutating control is absent, not disabled</td></tr>
          </tbody>
        </table>
      </div>"""
    return shell(page_title="Component specimens", study=None, active="",
                 actor=ctx["actor"], role=ctx["role"], links=ctx["links"], body=body,
                 actor_note="", sidebar_variant="specimens")
