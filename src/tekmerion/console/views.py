"""HTML rendering for the admin console (Spec 005, E5).

The markup mirrors the approved wireframes screen for screen
(`docs/wireframes/console/*.html`; constitution Article XIV): same
shells, same components, same classes — the wireframe files are the
requirements, this module is their production rendering against
live platform records (`tekmerion.platform`). Every value rendered
comes from the service layer; nothing here invents a state.

Ratified readings applied (owner approval with the coordinator
recommendation block, 2026-10-12; README addendum in the wireframe
package): Q1 inherited density · Q2 separate plane shells · Q3
tenant landing = Users & roles · Q4 event detail by inline row
expansion · Q5 phase chips stripped (state labels ship, task ids
do not) · Q7 compliance platform-only · Q8 tenant-by-identifier
sign-in entry instead of the drawn picker.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from typing import Any, Optional


def e(x: Any) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def chip(text: str, cls: str = "") -> str:
    return f'<span class="chip {e(cls)}">{e(text)}</span>'


def short(h: Optional[str], head: int = 8, tail: int = 5) -> str:
    """Shortened hash/fingerprint, the WIREFRAMES.md §5 table form."""
    if not h:
        return "—"
    return f"{h[:head]}…{h[-tail:]}" if len(h) > head + tail + 1 else h


def actor_short(actor_id: Optional[str]) -> str:
    if not actor_id:
        return "—"
    if actor_id in ("system", "bootstrap", "unknown"):
        return actor_id
    return f"actor {actor_id[:4]}…{actor_id[-4:]}"


def fmt_ts(ts: Optional[float]) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def fmt_date(ts: Optional[float]) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def fmt_duration(seconds: Optional[float]) -> str:
    if not seconds:
        return "—"
    seconds = int(seconds)
    if seconds % 3600 == 0:
        return f"{seconds // 3600} h"
    if seconds % 60 == 0:
        return f"{seconds // 60} min"
    return f"{seconds} s"


def banner_refusal(heading: str, message: str, note: str = "") -> str:
    note_html = (f'<div class="why" style="color:var(--ink-2);margin-top:6px">{e(note)}</div>'
                 if note else "")
    return (f'<div class="banner-refusal"><strong>{e(heading)}</strong> '
            f'<span class="mono">{e(message)}</span>{note_html}</div>')


def banner_valid(heading: str, message: str) -> str:
    return (f'<div class="banner-valid"><strong>{e(heading)}</strong> '
            f'<span class="mono">{e(message)}</span></div>')


def build_footer(build_id: str) -> str:
    return (f'<div class="screen-note">Admin console · BUILD_ID '
            f'<span class="mono">{e(build_id)}</span> — the stamp of the '
            f"artifact serving this page; a deployment is verified only "
            f"when the stamp matches the build.</div>")


def page(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} — Tekmerion admin console</title>
<link rel="stylesheet" href="/static/style.css">
<link rel="stylesheet" href="/static/console.css">
</head>
<body>
{body}
</body>
</html>
"""


def _act(active: str, key: str) -> str:
    return "active" if active == key else ""


def _actor_utilities(ctx: dict) -> str:
    """Step-up state + sign-out, under the actor block of either shell."""
    if ctx.get("stepped_up"):
        step = '<span class="micro">Step-up: fresh MFA on this session.</span>'
    else:
        step = ('<a href="/auth/step-up">Step up (fresh MFA)</a> — '
                "adjudicator key actions require it; the window is "
                "recorded session policy.")
    return (f'<p class="micro">{step}</p>'
            '<form method="post" action="/auth/logout" style="margin:0">'
            '<button class="btn" type="submit">Sign out</button></form>')


def platform_shell(*, active: str, ctx: dict, body: str) -> str:
    count = ctx.get("tenant_count")
    count_html = f' <span class="count">{count}</span>' if count is not None else ""
    inner = f"""<div class="shell">
  <aside class="side">
    <div>
      <div class="brand-name">TEKMERION</div>
      <div class="brand-tag">Admin console</div>
    </div>
    <div class="study-block">
      <div class="study-label">Scope</div>
      <div class="study-name">Deployment — all tenants</div>
      <span class="chip" style="background:#274B74;border-color:#4A6E99;color:#DCE6F2">Platform plane</span>
    </div>
    <nav class="nav">
      <a href="/platform/tenants" class="{_act(active, 'tenants')}">Tenants{count_html}</a>
      <a href="/platform/audit" class="{_act(active, 'audit')}">Audit ledger</a>
      <a href="/platform/compliance" class="{_act(active, 'compliance')}">Compliance</a>
      <a href="/platform/status" class="{_act(active, 'status')}">System status</a>
    </nav>
    <div class="spacer"></div>
    <div class="actor-block">
      <div class="study-label">Acting as</div>
      <div class="who">{e(ctx['actor_name'])}</div>
      <div class="role-switch"><span class="on">Platform admin</span></div>
      <p class="micro" style="color:#9FB6CE">Identity arrives via the deployment IdP.
        A platform admin holds no study role and cannot sign study appends (CLM-005-09).
        Every action is appended under this name.</p>
      {_actor_utilities(ctx)}
    </div>
  </aside>
  <main class="main">
    <div class="wrap">
{body}
      {build_footer(ctx['build_id'])}
    </div>
  </main>
</div>
"""
    return page(ctx["title"], inner)


def tenant_shell(*, active: str, ctx: dict, body: str) -> str:
    count = ctx.get("user_count")
    count_html = f' <span class="count">{count}</span>' if count is not None else ""
    inner = f"""<div class="shell">
  <aside class="side tenant">
    <div>
      <div class="brand-name">TEKMERION</div>
      <div class="brand-tag">Admin console</div>
    </div>
    <div class="study-block">
      <div class="study-label">Tenant</div>
      <div class="study-name">{e(ctx['tenant_name'])}</div>
      <span class="tenant-chip">Tenant plane · {e(ctx['tenant_id'])}</span>
    </div>
    <nav class="nav">
      <a href="/tenant/users" class="{_act(active, 'users')}">Users &amp; roles{count_html}</a>
      <a href="/tenant/keys" class="{_act(active, 'keys')}">Keys &amp; bindings</a>
      <a href="/tenant/events" class="{_act(active, 'events')}">Lifecycle events</a>
      <a href="/tenant/break-glass" class="{_act(active, 'break-glass')}">Break-glass</a>
    </nav>
    <div class="spacer"></div>
    <div class="actor-block">
      <div class="study-label">Acting as</div>
      <div class="who">{e(ctx['actor_name'])}</div>
      <div class="role-switch"><span class="on">Tenant admin</span></div>
      <p class="micro">Identity arrives via {e(ctx['tenant_name'])}'s IdP. Tenant admin powers are
        disjoint from study roles — an admin grant signs no verdicts (CLM-005-09).
        Every action is appended under this name.</p>
      {_actor_utilities(ctx)}
    </div>
  </aside>
  <main class="main">
    <div class="wrap">
{body}
      {build_footer(ctx['build_id'])}
    </div>
  </main>
</div>
"""
    return page(ctx["title"], inner)


def plane_strip(plane: str, text: str) -> str:
    name = "Platform plane" if plane == "platform" else "Tenant plane"
    return (f'<div class="plane-strip {plane}"><span class="plane-name">{name}</span>'
            f"<span>{text}</span></div>")


def kv(rows: list[tuple[str, str]], grid: str = "") -> str:
    style = f' style="grid-template-columns:{grid}"' if grid else ""
    items = "".join(f"<dt>{label}</dt><dd>{value}</dd>" for label, value in rows)
    return f'<dl class="kv"{style}>{items}</dl>'


def state_chip(state: str) -> str:
    """Chips for recorded states: the label is the record's own word;
    the class is the wireframes' treatment of that class of state."""
    cls = {
        "active": "supported", "enrolled": "supported", "configured": "supported",
        "intact": "supported", "recorded": "supported", "review recorded": "supported",
        "superseded": "brand", "rotated": "brand",
        "not configured": "", "pending": "inconclusive",
        "pending second authorization": "inconclusive",
        "review outstanding": "inconclusive", "open": "invalid",
        "revoked": "contradicted", "denied": "contradicted", "refused": "contradicted",
        "failed": "contradicted", "broken": "invalid",
        "closed": "dead", "expired": "dead", "deactivated": "dead", "system": "dead",
    }.get(state, "")
    return chip(state, cls)


# ---------------------------------------------------------------- sign-in

def render_signin(ctx: dict) -> str:
    refusal = ""
    if ctx.get("refusal"):
        refusal = f"""
  <h2>How a refusal looks</h2>
  {banner_refusal("Sign-in refused.", ctx["refusal"],
                    "Refusals are stated as the service states them, and the refusal itself is "
                    "appended to the tenant's audit ledger before it is shown. The service's "
                    "record carries the specific reason; this surface does not distinguish "
                    "unknown identity from failed authentication (§3.5.11).")}"""
    platform_options = "".join(
        f'<option value="{e(i["issuer"])}">{e(i["issuer"])}</option>'
        for i in ctx["platform_idps"])
    platform_field = ""
    if len(ctx["platform_idps"]) > 1:
        platform_field = f"""<div class="field">
          <label for="platform-issuer">Deployment identity provider</label>
          <select id="platform-issuer" name="issuer">{platform_options}</select>
        </div>"""
    elif ctx["platform_idps"]:
        platform_field = (f'<input type="hidden" name="issuer" '
                          f'value="{e(ctx["platform_idps"][0]["issuer"])}">')
    platform_button = ('<button class="btn primary" type="submit">Continue to the '
                       "deployment identity provider</button>") if ctx["platform_idps"] else \
        '<span class="chip">no deployment IdP configured</span>'
    body = f"""<div class="signin-wrap">
  <div class="signin-head">
    <div class="brand-name" style="color:var(--brand)">TEKMERION</div>
    <div class="brand-tag" style="color:var(--ink-3)">Admin console</div>
    <h1 style="margin-top:14px">Sign in to the admin console</h1>
    <p class="page-sub">The console has two planes, and they are disjoint: a platform
      sign-in holds no tenant powers, and a tenant sign-in reaches no other tenant
      (Spec 005 §5, CLM-005-09). Choose the plane you mean to work in — you will
      authenticate at that plane's identity provider.</p>
  </div>

  <div class="plane-cards">
    <div class="plane-card platform">
      <div class="scope">Platform plane · deployment scope</div>
      <h2>Platform administration</h2>
      <p class="muted">Tenant lifecycle, platform configuration, break-glass policy,
        the deployment audit ledger. For the deployment's operators.</p>
      <form method="post" action="/auth/platform/oidc">
        {platform_field}
        <div class="row-actions">{platform_button}</div>
      </form>
      <p class="small muted">Sign-in completes at the deployment IdP. There is no
        platform-plane password. Admin actions additionally require step-up:
        MFA evidence at the IdP, fresh within the tenant's recorded policy window.</p>
    </div>

    <div class="plane-card tenant">
      <div class="scope">Tenant plane · one tenant only</div>
      <h2>Tenant administration</h2>
      <p class="muted">Your institution's IdP configuration, membership, role grants,
        keys, and audit record. A session here can see no other tenant's records.</p>
      <form method="post" action="/auth/tenant/start">
        <div class="field">
          <label for="tenant-id">Your tenant identifier</label>
          <input id="tenant-id" name="tenant_id" type="text" autocomplete="off"
                 placeholder="e.g. uni-a">
          <div class="help">The tenant list is not published on this page — an
            enumerated picker would disclose tenant names to anyone who reaches
            it. The tenant of a session comes from the authenticated session,
            never from this entry alone: the entry only chooses which IdP you
            are sent to.</div>
        </div>
        <div class="row-actions">
          <button class="btn primary" type="submit" name="protocol" value="oidc">Continue via OIDC</button>
          <button class="btn" type="submit" name="protocol" value="saml">Continue via SAML 2.0</button>
        </div>
      </form>
      <p class="small muted">Your tenant's IdP (OIDC or SAML 2.0) is the only
        credential. There is no Tekmerion password — a screen asking for one is
        not this product (CLM-005-01).</p>
    </div>
  </div>
{refusal}
  {build_footer(ctx['build_id'])}
</div>
"""
    return page("Console sign-in & plane selection", body)


def render_plane_choice(ctx: dict) -> str:
    """An identity holding BOTH planes' roles chooses its working
    plane — the planes stay disjoint; the session works in one."""
    body = f"""<div class="signin-wrap">
  <div class="signin-head">
    <div class="brand-name" style="color:var(--brand)">TEKMERION</div>
    <div class="brand-tag" style="color:var(--ink-3)">Admin console</div>
    <h1 style="margin-top:14px">Choose a plane</h1>
    <p class="page-sub">You are signed in as {e(ctx['actor_name'])}. This identity holds
      roles in both planes; the planes are disjoint, so choose the one you mean
      to work in. The other plane's controls will not exist in that shell.</p>
  </div>
  <div class="plane-cards">
    <div class="plane-card platform">
      <div class="scope">Platform plane · deployment scope</div>
      <h2>Platform administration</h2>
      <div class="row-actions"><a class="btn primary" href="/platform/tenants">Enter the platform plane</a></div>
    </div>
    <div class="plane-card tenant">
      <div class="scope">Tenant plane · one tenant only</div>
      <h2>Tenant administration</h2>
      <div class="row-actions"><a class="btn primary" href="/tenant/users">Enter the tenant plane</a></div>
    </div>
  </div>
  {build_footer(ctx['build_id'])}
</div>
"""
    return page("Choose a plane", body)


def render_no_plane(ctx: dict) -> str:
    body = f"""<div class="signin-wrap">
  <div class="signin-head">
    <div class="brand-name" style="color:var(--brand)">TEKMERION</div>
    <div class="brand-tag" style="color:var(--ink-3)">Admin console</div>
    <h1 style="margin-top:14px">No admin plane for this identity</h1>
  </div>
  {banner_refusal("Access refused.",
                    "this identity holds no admin-plane role — the console's planes are "
                    "tenant admin and platform admin, and study roles confer neither "
                    "(CLM-005-09). The sign-in itself is recorded in the audit ledger.",
                    "If this is wrong, a tenant admin (for the tenant plane) or a platform "
                    "admin (for the platform plane) grants the role as a recorded event.")}
  <form method="post" action="/auth/logout" style="margin-top:16px">
    <button class="btn" type="submit">Sign out</button>
  </form>
  {build_footer(ctx['build_id'])}
</div>
"""
    return page("No admin plane", body)


# ------------------------------------------------------- platform: tenants

def _idp_cell(configs: list[dict], label: str) -> str:
    if configs:
        return f'{label} {chip("configured", "supported")}'
    return f'{label} {chip("not configured")}'


def render_tenants(ctx: dict) -> str:
    rows = []
    for t in ctx["tenants"]:
        link = f'<a href="/platform/tenants/{e(t["tenant_id"])}"><strong>{e(t["name"])}</strong></a>'
        rows.append(f"""<tr>
          <td data-h="Tenant">{link}<br><span class="mono">{e(t['tenant_id'])}</span></td>
          <td data-h="Shape · region">{e(t['shape'])}<br><span class="muted">{e(t['region'] or '—')}</span></td>
          <td data-h="Identity providers">{_idp_cell(t['oidc'], 'OIDC')}<br>{_idp_cell(t['saml'], 'SAML')}</td>
          <td data-h="Identities">{t['identities']}</td>
          <td data-h="Keys">{t['keys']}</td>
          <td data-h="SCIM">{state_chip('configured' if t['scim'] else 'not configured')}</td>
          <td data-h="State">{state_chip('active' if t['active'] else 'deactivated')}</td>
        </tr>""")
    p = ctx["platform_tenant"]
    rows.append(f"""<tr class="dead-row">
          <td data-h="Tenant"><strong>Platform</strong><br><span class="mono">{e(p['tenant_id'])}</span></td>
          <td data-h="Shape · region">system tenant</td>
          <td data-h="Identity providers">deployment IdP</td>
          <td data-h="Identities">{p['identities']}</td>
          <td data-h="Keys">—</td>
          <td data-h="SCIM">—</td>
          <td data-h="State">{chip('system', 'dead')}</td>
        </tr>""")
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    notice = banner_valid("Recorded.", ctx["notice"]) if ctx.get("notice") else ""
    body = f"""{plane_strip('platform', 'Deployment scope — every tenant below is administered from here; study content is not visible in this plane.')}
      <h1>Tenants</h1>
      <p class="page-sub">Organization = tenant (Spec 005 §6). Every study, identity, and
        platform record is tenant-scoped; tenant context comes from the authenticated
        session, never from request parameters.</p>
      {refusal}{notice}
      <div class="stats">
        <div class="stat"><div class="num">{ctx['stats']['tenants']}</div><div class="lab">Tenants</div></div>
        <div class="stat"><div class="num">{ctx['stats']['identities']}</div><div class="lab">Identities (all tenants)</div></div>
        <div class="stat"><div class="num">{ctx['stats']['keys']}</div><div class="lab">Keys enrolled</div></div>
        <div class="stat"><div class="num">{ctx['stats']['deployment_events']}</div><div class="lab">Deployment-ledger events</div></div>
      </div>

      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:24%">Tenant</th><th style="width:16%">Shape · region</th><th style="width:22%">Identity providers</th><th style="width:10%">Identities</th><th style="width:8%">Keys</th><th style="width:10%">SCIM</th><th style="width:10%">State</th></tr>
          </thead>
          <tbody>
{''.join(rows)}
          </tbody>
        </table>
      </div>

      <h2>Create tenant</h2>
      <form method="post" action="/platform/tenants">
        <div class="card">
          <div class="field">
            <label for="ct-id">Tenant ID</label>
            <input id="ct-id" name="tenant_id" type="text" autocomplete="off">
          </div>
          <div class="field">
            <label for="ct-name">Name</label>
            <input id="ct-name" name="name" type="text" autocomplete="off">
          </div>
          <div class="field">
            <label for="ct-shape">Shape</label>
            <select id="ct-shape" name="shape">
              <option value="hosted">hosted (multi-tenant)</option>
              <option value="self-hosted">self-hosted (single-tenant)</option>
            </select>
          </div>
          <div class="field">
            <label for="ct-region">Residency pin — region</label>
            <input id="ct-region" name="region" type="text" autocomplete="off">
            <div class="help">Recorded at creation. Moving a pin later is a migration —
              export, anchor, move, record — never a field edit.</div>
          </div>
          <div class="row-actions" style="margin-bottom:0">
            <button class="btn primary" type="submit">Create tenant</button>
            <span class="muted small">Tenant creation is a platform-admin act — v1 has no
              tenant self-signup (Spec 005 §11). Creation appends
              <span class="mono">tenant.created</span> to the deployment ledger.</span>
          </div>
        </div>
      </form>
"""
    ctx = {**ctx, "title": "Tenants"}
    return platform_shell(active="tenants", ctx=ctx, body=body)


# ---------------------------------------------- tenant detail (both planes)

def render_tenant_detail(ctx: dict) -> str:
    """One view, two shells: platform admins administer the tenant
    from outside it; tenant admins see the same sections for their
    own tenant (T536). `ctx['variant']` is 'platform' or 'tenant';
    action endpoints follow the variant's plane."""
    t = ctx["tenant"]
    base = "/platform/tenants/" + t["tenant_id"] if ctx["variant"] == "platform" else "/tenant/idp"
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    notice = banner_valid("Recorded.", ctx["notice"]) if ctx.get("notice") else ""
    strip = (plane_strip("platform", "Deployment scope — you are administering a tenant from outside it. Tenant-plane sessions never see this view of another tenant.")
             if ctx["variant"] == "platform" else
             plane_strip("tenant", f"{e(t['name'])} only — this session can reach no other tenant's records, and no control here affects one."))
    crumb = f'<div class="crumb">Tenants · {e(t["tenant_id"])}</div>' if ctx["variant"] == "platform" else ""
    pin = ctx["pin"]
    pin_rows = [
        ("Tenant ID", f'<span class="mono">{e(t["tenant_id"])}</span>'),
        ("Shape", f"{e(t['shape'])} — one codebase, one authorization model (CLM-005-12)"),
        ("Residency pin", f"region <span class=\"mono\">{e(pin['region'] or '—')}</span>, recorded at creation"
         + (f"; {pin['migrations']} migration(s) on record" if pin["migrations"] else "")
         + ". Changing a pin is a migration — export, anchor the pre-migration state, move, record the event."),
        ("State", state_chip("active" if t["active"] else "deactivated")),
        ("Legal hold", (f'<span class="chip invalid">hold active</span> <span class="mono">{e(ctx["hold"]["hold_id"])}</span> — erasure, pin change, and tenant-plane export are refused while it stands'
                        if ctx.get("hold") else "none")),
        ("Created", ctx["created"]),
    ]
    pin_form = ""
    if ctx["variant"] == "platform":
        pin_form = f"""
      <form method="post" action="{base}/residency">
        <div class="row-actions">
          <span class="field" style="margin:0"><label for="pin-region">Move pin — new region</label>
          <input id="pin-region" name="region" type="text" autocomplete="off"></span>
          <span class="field" style="margin:0"><label for="pin-shape">New shape</label>
          <select id="pin-shape" name="shape"><option value="hosted">hosted</option><option value="self-hosted">self-hosted</option></select></span>
          <button class="btn" type="submit">Change residency pin</button>
          <span class="muted small">Refused unless an anchored audit export of this tenant's
            ledger exists — the refusal is ledgered too.</span>
        </div>
      </form>"""
    # --- OIDC card
    oidc = ctx["oidc"]
    if oidc:
        oidc_rows = [
            ("Issuer", f'<span class="mono">{e(oidc["issuer"])}</span>'),
            ("Client ID", f'<span class="mono">{e(oidc["client_id"])}</span>'),
            ("Client secret", 'held in the secrets store — <strong>reference only; the value is never displayed</strong> (Spec 005 §9)'),
            ("Secret reference", f'<span class="mono">{e(oidc["client_secret_ref"])}</span>'),
            ("Flow", "authorization code + PKCE, S256 required"),
            ("Required AMR", f'<span class="mono">{e(", ".join(oidc["required_amr"]))}</span> (MFA evidence, §13.5)'),
        ]
        oidc_card = f"""<div class="card">
          <h3>OIDC {chip('configured', 'supported')}</h3>
          {kv(oidc_rows, '118px 1fr')}
          <form method="post" action="{base}/idp/oidc">
            <div class="field"><label>Issuer</label><input name="issuer" type="text" value="{e(oidc['issuer'])}"></div>
            <div class="field"><label>Client ID</label><input name="client_id" type="text" value="{e(oidc['client_id'])}"></div>
            <div class="field"><label>Redirect URI</label><input name="redirect_uri" type="text" value="{e(oidc['redirect_uri'])}"></div>
            <div class="field"><label>Client secret reference</label><input name="client_secret_ref" type="text" value="{e(oidc['client_secret_ref'])}"></div>
            <div class="field"><label>New client secret (value)</label><input name="client_secret" type="password" autocomplete="new-password">
              <div class="help">Leave blank to keep the secret currently held under the reference. A value entered here goes to the secrets store; it is never written to a config payload or a ledger.</div></div>
            <div class="row-actions" style="margin-bottom:0"><button class="btn" type="submit">Save OIDC configuration</button></div>
          </form>
          <p class="small muted">Edits append <span class="mono">idp.updated</span>; an invalid
            configuration is refused by the service, never repaired silently — the refusal
            appears here verbatim.</p>
        </div>"""
    else:
        oidc_card = f"""<div class="card">
          <h3>OIDC {chip('not configured')}</h3>
          <form method="post" action="{base}/idp/oidc">
            <div class="field"><label>Issuer</label><input name="issuer" type="text" autocomplete="off"></div>
            <div class="field"><label>Client ID</label><input name="client_id" type="text" autocomplete="off"></div>
            <div class="field"><label>Redirect URI</label><input name="redirect_uri" type="text" autocomplete="off"></div>
            <div class="field"><label>Client secret reference</label><input name="client_secret_ref" type="text" autocomplete="off"></div>
            <div class="field"><label>Client secret (value)</label><input name="client_secret" type="password" autocomplete="new-password">
              <div class="help">Stored in the secrets store under the reference; never in the config payload.</div></div>
            <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Configure OIDC</button></div>
          </form>
        </div>"""
    # --- SAML card
    saml = ctx["saml"]
    saml_form = f"""
          <form method="post" action="{base}/idp/saml">
            <div class="field"><label>SP entity ID</label><input name="sp_entity_id" type="text" value="{e(saml['sp_entity_id'] if saml else '')}"></div>
            <div class="field"><label>ACS URL</label><input name="acs_url" type="text" value="{e(saml['acs_url'] if saml else '')}"></div>
            <div class="field"><label>IdP metadata (XML)</label><textarea name="metadata_xml" rows="6" spellcheck="false"></textarea>
              <div class="help">Metadata import is validated at configuration time — expired validity, a missing signing certificate, or non-IdP metadata are refused by name. Certificates are held by reference; only their SHA-256 fingerprints are recorded.</div></div>
            <div class="field"><label>Subject source</label>
              <select name="subject_source"><option value="nameid">nameid</option><option value="eppn">eduPersonPrincipalName (eppn)</option></select></div>
            <div class="row-actions" style="margin-bottom:0"><button class="btn" type="submit">{'Replace SAML configuration' if saml else 'Configure SAML'}</button></div>
          </form>"""
    if saml:
        fps = "<br>".join(f'<span class="mono">{short(fp, 8, 6)}</span> (SHA-256 fingerprint)'
                          for fp in saml["signing_cert_fingerprints"]) or "—"
        saml_rows = [
            ("Entity ID", f'<span class="mono">{e(saml["idp_entity_id"])}</span>'),
            ("SSO endpoint", f'<span class="mono">{e(saml["sso_redirect_url"] or saml["sso_post_url"] or "—")}</span>'),
            ("Signing cert", fps + " — certificate held <strong>by reference</strong>; fingerprints are what ledgers and screens carry"),
            ("Subject source", f'<span class="mono">{e(saml["subject_source"])}</span>'),
            ("Assertions", "signed only — an unsigned or wrongly-signed assertion is rejected, never repaired"),
        ]
        saml_card = f"""<div class="card">
          <h3>SAML 2.0 {chip('configured', 'supported')}</h3>
          {kv(saml_rows, '118px 1fr')}
          {saml_form}
        </div>"""
    else:
        saml_card = f"""<div class="card">
          <h3>SAML 2.0 {chip('not configured')}</h3>
          {saml_form}
        </div>"""
    # --- provisioning cards
    scim = ctx["scim"]
    if scim["configured"]:
        cred_rows = "".join(
            f'<tr><td data-h="Credential" class="mono">{e(c["credential_id"])}</td>'
            f'<td data-h="State">{state_chip("revoked" if c["revoked"] else "active")}</td>'
            f'<td data-h="Revoke"><form method="post" action="{base}/scim/revoke">'
            f'<input type="hidden" name="credential_id" value="{e(c["credential_id"])}">'
            f'<button class="btn danger" type="submit">Revoke</button></form></td></tr>'
            for c in scim["credentials"])
        scim_card = f"""<div class="card">
          <h3>SCIM 2.0 {chip('configured', 'supported')}</h3>
          <p class="muted">SCIM is this tenant's lifecycle source of truth where configured:
            Users create/update/deactivate; Groups map to role grants only through
            tenant-admin-approved mapping records ({scim['mappings']} approved) — a group
            membership never silently becomes an adjudicator grant (Spec 005 §4).
            Last sync outcome on record: <span class="mono">{e(scim['last_sync'])}</span>.</p>
          <div class="card flush"><table><thead><tr><th>Credential</th><th>State</th><th></th></tr></thead>
          <tbody>{cred_rows}</tbody></table></div>
          <form method="post" action="{base}/scim/issue">
            <div class="row-actions" style="margin-bottom:0"><button class="btn" type="submit">Issue a SCIM credential</button>
            <span class="muted small">The secret is shown once, at issuance; only its hash is stored.</span></div>
          </form>
        </div>"""
    else:
        scim_card = f"""<div class="card">
          <h3>SCIM 2.0 {chip('not configured')}</h3>
          <p class="muted">Where configured, SCIM is the tenant's lifecycle source of truth:
            Users create/update/deactivate; Groups map to role grants only through
            tenant-admin-approved mapping records — a group membership never silently
            becomes an adjudicator grant (Spec 005 §4).</p>
          <form method="post" action="{base}/scim/issue">
            <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Issue a SCIM credential</button>
            <span class="muted small">Issuing the first credential configures SCIM for this tenant. The secret is shown once; only its hash is stored.</span></div>
          </form>
        </div>"""
    if ctx.get("scim_secret"):
        scim_card += banner_valid(
            "SCIM credential issued — shown once.",
            f"credential {ctx['scim_secret']['credential_id']} · secret {ctx['scim_secret']['secret']}")
    jit = ctx["jit"]
    jit_card = f"""<div class="card">
          <h3>Just-in-time provisioning</h3>
          <p class="muted">For tenants without SCIM: the first assertion creates the identity
            <strong>in the asserting tenant only</strong>, holding <strong>no study role</strong>
            until a recorded grant. On record for this tenant: {jit['created']} identities
            created by assertion, {jit['roleless']} currently holding no role.</p>
        </div>"""
    pol = ctx["policy"]
    policy_rows = [
        ("MFA", "required at the IdP, enforced platform-side (CLM-005-27) — a session without MFA evidence cannot mutate or step up"
         if pol["require_mfa"] else "not required by this tenant's recorded policy"),
        ("Step-up freshness", f"{fmt_duration(pol['stepup_freshness_seconds'])} for verdict-signing and admin-plane actions"),
        ("Session lifetimes", f"idle {fmt_duration(pol['session_idle_seconds'])} · absolute {fmt_duration(pol['session_absolute_seconds'])} (tenant-configurable downward only)"),
        ("Key custody", "permitted modes recorded per tenant policy: " + ", ".join(pol["allowed_custody"]) + "; the mode is recorded on every append, never blurred"),
        ("Rate limit", f"{pol['rate_limit_per_minute']} per minute per endpoint class; exhaustion is a recorded stop (429)"),
    ]
    body = f"""{strip}
      {crumb}
      <h1>{e(t['name'])}</h1>
      <p class="page-sub">Tenant record and identity configuration. Changes here are
        appended events (<span class="mono">tenant.updated</span>,
        <span class="mono">idp.configured</span>, <span class="mono">idp.updated</span>) —
        there is no silent edit path, and the console has no mutation path of its own (Spec 005 §7).</p>
      {refusal}{notice}
      <div class="card">
        {kv(pin_rows)}
        {pin_form}
      </div>

      <h2>Identity providers</h2>
      <div class="grid2">
        {oidc_card}
        {saml_card}
      </div>

      <h2>Provisioning</h2>
      <div class="grid2">
        {scim_card}
        {jit_card}
      </div>

      <h2>Tenant policy (recorded, Spec 005 §§2–3, 9)</h2>
      <div class="card">
        {kv(policy_rows)}
      </div>
"""
    ctx = {**ctx, "title": f"Tenant — {t['name']}"}
    if ctx["variant"] == "platform":
        return platform_shell(active="tenants", ctx=ctx, body=body)
    return tenant_shell(active="idp", ctx=ctx, body=body)


# --------------------------------------------------------- tenant: users

def render_users(ctx: dict) -> str:
    t = ctx["tenant"]
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    notice = banner_valid("Recorded.", ctx["notice"]) if ctx.get("notice") else ""
    rows = []
    for u in ctx["users"]:
        holds = []
        for role in u["roles"]:
            holds.append(
                f'<span class="role-line">{chip(role, "brand" if role in ("tenant_admin", "platform_admin") else "")} '
                f'<form method="post" action="/tenant/users/revoke" style="display:inline">'
                f'<input type="hidden" name="identity_id" value="{e(u["identity_id"])}">'
                f'<input type="hidden" name="role" value="{e(role)}">'
                f'<button class="btn danger" type="submit">Revoke</button></form></span>')
        if not holds:
            holds = ['<span class="muted">no roles — can authenticate, can do nothing</span>']
        grant_options = "".join(f'<option value="{e(r)}">{e(r)}</option>' for r in ctx["grantable"])
        state_action = (
            f'<form method="post" action="/tenant/users/deactivate" style="display:inline">'
            f'<input type="hidden" name="identity_id" value="{e(u["identity_id"])}">'
            f'<button class="btn danger" type="submit">Deactivate</button></form>'
            if u["active"] else
            f'<form method="post" action="/tenant/users/reactivate" style="display:inline">'
            f'<input type="hidden" name="identity_id" value="{e(u["identity_id"])}">'
            f'<button class="btn" type="submit">Reactivate</button></form>')
        via = {"oidc": "assertion · OIDC", "saml": "assertion · SAML",
               "admin": "tenant admin", "bootstrap": "bootstrap"}.get(u["created_via"], u["created_via"])
        rows.append(f"""<tr class="{'' if u['active'] else 'dead-row'}">
          <td data-h="Person"><strong>{e(u['display_name'] or u['subject'])}</strong><br>
            <span class="muted">{e(u['email'] or '')}{' · ' if u['email'] else ''}{e(u['affiliation'] or '')}</span><br>
            <span class="mono">{e(actor_short(u['actor_id']))}</span></td>
          <td data-h="Sign-in"><span class="mono">{e(short(u['issuer'], 22, 8))}</span><br>
            <span class="muted">subject <span class="mono">{e(u['subject'])}</span></span><br>
            <span class="muted">bound {fmt_date(u['first_seen'])}, via {e(via)}</span></td>
          <td data-h="Held in this tenant">{''.join(holds)}
            <form method="post" action="/tenant/users/grant" class="grant-form">
              <input type="hidden" name="identity_id" value="{e(u['identity_id'])}">
              <select name="role">{grant_options}</select>
              <button class="btn" type="submit">Grant</button>
            </form></td>
          <td data-h="State">{state_chip('active' if u['active'] else 'deactivated')}<br>{state_action}</td>
        </tr>""")
    grant_rows = []
    for g in ctx["grant_events"]:
        grant_rows.append(f"""<tr>
          <td data-h="Grantor">{e(g['grantor'])}</td>
          <td data-h="Grantee">{e(g['grantee'])}</td>
          <td data-h="Role">{chip(g['role'], 'brand' if g['role'] in ('tenant_admin', 'platform_admin') else '')}</td>
          <td data-h="When">{fmt_ts(g['ts'])}</td>
          <td data-h="Event"><span class="mono">{e(g['event_type'])}</span> · seq {g['seq']}</td>
        </tr>""")
    issuer_options = "".join(
        f'<option value="{e(i)}">{e(i)}</option>' for i in ctx["issuers"])
    body = f"""{plane_strip('tenant', f"{e(t['name'])} only — this session can reach no other tenant's records, and no control here affects one.")}
      <h1>Users &amp; roles</h1>
      <p class="page-sub">A person appears here when their identity is bound to {e(t['name'])} —
        by IdP assertion or by a tenant admin — never before (§4). Roles exist only where a
        recorded grant creates them: there is no default role, and no combination of flags
        synthesizes one (§6, CLM-005-09).</p>
      {refusal}{notice}
      <div class="stats">
        <div class="stat"><div class="num">{ctx['stats']['identities']}</div><div class="lab">Identities</div></div>
        <div class="stat"><div class="num">{ctx['stats']['with_roles']}</div><div class="lab">Hold a role in this tenant</div></div>
        <div class="stat"><div class="num">{ctx['stats']['deactivated']}</div><div class="lab">Deactivated</div></div>
      </div>

      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:26%">Person</th><th style="width:26%">Sign-in</th><th style="width:32%">Held in this tenant</th><th style="width:16%">State</th></tr>
          </thead>
          <tbody>
{''.join(rows)}
          </tbody>
        </table>
      </div>

      <h2>Role grants on record</h2>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:26%">Grantor</th><th style="width:26%">Grantee</th><th style="width:16%">Role</th><th style="width:14%">When</th><th style="width:18%">Event</th></tr>
          </thead>
          <tbody>
{''.join(grant_rows) if grant_rows else '<tr><td colspan="5" class="muted">No grants on record.</td></tr>'}
          </tbody>
        </table>
      </div>
      <p class="small muted">Every grant and revocation names grantor and grantee in the
        tenant ledger itself (<span class="mono">role.granted</span> /
        <span class="mono">role.revoked</span>) — this table is a projection of the ledger,
        not a separate record. Platform powers are granted only from the platform plane.</p>

      <h2>Create an identity record</h2>
      <form method="post" action="/tenant/users/create">
        <div class="card">
          <div class="field"><label>Identity provider (issuer)</label>
            <select name="issuer">{issuer_options}</select>
            <div class="help">The record binds the person to this tenant before their first
              sign-in. Their sign-in subject must match the subject entered here.</div></div>
          <div class="field"><label>Subject</label><input name="subject" type="text" autocomplete="off"></div>
          <div class="field"><label>Display name</label><input name="display_name" type="text" autocomplete="off"></div>
          <div class="field"><label>Email</label><input name="email" type="text" autocomplete="off"></div>
          <div class="field"><label>Affiliation</label><input name="affiliation" type="text" autocomplete="off"></div>
          <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Create identity record</button>
          <span class="muted small">Appends <span class="mono">identity.created</span> (via admin). The identity holds no role until a recorded grant.</span></div>
        </div>
      </form>

      <div class="card">
        <h3>Identity provider configuration</h3>
        <p class="muted" style="margin-bottom:0">This tenant's IdP configuration — issuers,
          certificates by fingerprint, SCIM and group mappings — is administered on the
          tenant record screen: <a href="/tenant/idp">IdP configuration →</a></p>
      </div>
"""
    ctx = {**ctx, "title": "Users & roles"}
    return tenant_shell(active="users", ctx=ctx, body=body)


# ---------------------------------------------------------- tenant: keys

_CUSTODY_NOTE = """<div class="card">
        <h3>What "delegated" honestly means</h3>
        <p class="muted" style="margin-bottom:0">The platform signer holds a seed-derived
          Ed25519 keypair for the identity. The seed and private key stay in the secrets
          store of the tenant's deployment; the identity signs nothing themselves, and
          the append names the custody mode — a reader sees the key's fingerprint and
          <span class="mono">custody=delegated</span>, never a self-custody claim. It is a
          software development signer, <strong>not a KMS/HSM custody claim</strong>
          (Spec 005 §3, decision 4). Non-repudiation for a study verdict comes from
          <em>self</em>-custody enrollment; delegated appends remain fully attributable
          (CLM-005-26).</p>
      </div>"""


def render_keys(ctx: dict) -> str:
    t = ctx["tenant"]
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    notice = banner_valid("Recorded.", ctx["notice"]) if ctx.get("notice") else ""
    status_label = {"enrolled": "enrolled", "superseded": "rotated",
                    "revoked": "revoked", "closed": "closed"}
    rows = []
    for k in ctx["keys"]:
        lineage = ""
        if k["status"] == "superseded" and k.get("replaced_by"):
            lineage = f'<br><span class="muted">superseded by <span class="mono">{short(k["replaced_by"])}</span> — verification unaffected</span>'
        elif k["status"] == "closed":
            lineage = '<br><span class="muted">closed at deprovisioning — history stays verifiable</span>'
        elif k["status"] == "revoked":
            lineage = '<br><span class="muted">new appends refused from the revocation event onward</span>'
        revoke = ""
        if k["status"] == "enrolled":
            revoke = (f'<form method="post" action="/tenant/keys/revoke" style="display:inline">'
                      f'<input type="hidden" name="fingerprint" value="{e(k["fingerprint"])}">'
                      f'<input type="hidden" name="reason" value="revoked from the console">'
                      f'<button class="btn danger" type="submit">Revoke</button></form>')
        rows.append(f"""<tr class="{'' if k['status'] == 'enrolled' else 'dead-row'}">
          <td data-h="Key" class="mono">{short(k['fingerprint'])}</td>
          <td data-h="Identity">{e(k['identity_name'])}<br><span class="mono">{e(actor_short(k['actor_id']))}</span></td>
          <td data-h="Custody">{chip(k['custody'], 'brand' if k['custody'] == 'delegated' else '')}</td>
          <td data-h="Status">{state_chip(status_label[k['status']])}{lineage}</td>
          <td data-h="Enrolled">seq {k['enrolled_seq']}</td>
          <td data-h="">{revoke}</td>
        </tr>""")
    api_rows = []
    for a in ctx["api_keys"]:
        scopes = "<br>".join(f'<span class="mono small">{e(s)}</span>' for s in a["scopes"][:4])
        if len(a["scopes"]) > 4:
            scopes += f'<br><span class="muted small">+{len(a["scopes"]) - 4} more</span>'
        revoke = ""
        if a["state"] == "active":
            revoke = (f'<form method="post" action="/tenant/keys/apikey-revoke">'
                      f'<input type="hidden" name="key_id" value="{e(a["key_id"])}">'
                      f'<button class="btn danger" type="submit">Revoke</button></form>')
        api_rows.append(f"""<tr class="{'' if a['state'] == 'active' else 'dead-row'}">
          <td data-h="Key" class="mono">{e(a['key_id'])}</td>
          <td data-h="Principal">{e(a['principal'])}</td>
          <td data-h="Role class">{chip(a['role_class'], 'brand')}</td>
          <td data-h="Scopes">{scopes}</td>
          <td data-h="Expires">{fmt_date(a['expires_at'])}</td>
          <td data-h="Last used">{fmt_ts(a['last_used_at']) if a['last_used_at'] else 'never'}</td>
          <td data-h="State">{state_chip(a['state'])}</td>
          <td data-h="">{revoke}</td>
        </tr>""")
    principal_options = "".join(
        f'<option value="{e(p["identity_id"])}">{e(p["name"])} ({e(p["kind"])})</option>'
        for p in ctx["principals"])
    role_options = "".join(f'<option value="{e(r)}">{e(r)}</option>' for r in ctx["role_classes"])
    my = ctx["my_keys"]
    my_rows = "".join(
        f'<div class="row-actions"><span class="mono">{short(k["fingerprint"])}</span>'
        f'<span class="muted small">custody {e(k["custody"])} · {e(k["status"])}</span></div>'
        for k in my) or '<p class="muted">You hold no enrolled key in this tenant.</p>'
    body = f"""{plane_strip('tenant', f"{e(t['name'])} only — this session can reach no other tenant's records, and no control here affects one.")}
      <h1>Keys &amp; bindings</h1>
      <p class="page-sub">Each identity's verdicts are signed by a key bound to its actor at
        enrollment (§3, CLM-005-04): the binding is recorded in the ledger, so bundle
        verification reads the binding from the record, not from a live lookup. Public keys
        and fingerprints are shown in full where a verifier needs them; <strong>private
        material is never displayed anywhere</strong>.</p>
      {refusal}{notice}
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:18%">Key</th><th style="width:18%">Identity</th><th style="width:12%">Custody</th><th style="width:26%">Status</th><th style="width:10%">Enrolled</th><th style="width:16%"></th></tr>
          </thead>
          <tbody>
{''.join(rows) if rows else '<tr><td colspan="6" class="muted">No keys enrolled in this tenant.</td></tr>'}
          </tbody>
        </table>
      </div>
      {ctx.get('custody_note', '')}
      <h2>Enroll a key</h2>
      <div class="card">
        <h3>Your keys (the signed-in identity)</h3>
        {my_rows}
        <form method="post" action="/tenant/keys/begin-enrollment">
          <div class="row-actions"><button class="btn" type="submit">Begin enrollment — issue a nonce</button>
          <span class="muted small">Self-custody: sign the nonce with your key device and submit
            the public key + proof below. The nonce binds the enrollment to this request.</span></div>
        </form>
        {f'<div class="banner-valid"><strong>Enrollment nonce.</strong> <span class="mono">{e(ctx["nonce"])}</span></div>' if ctx.get('nonce') else ''}
        <form method="post" action="/tenant/keys/enroll-self">
          <div class="field"><label>Public key (hex, 64 chars)</label><input name="public_key" type="text" autocomplete="off" spellcheck="false"></div>
          <div class="field"><label>Proof signature over the nonce (hex, 128 chars)</label><input name="proof_signature" type="text" autocomplete="off" spellcheck="false"></div>
          <div class="field"><label>Nonce</label><input name="nonce" type="text" autocomplete="off" value="{e(ctx.get('nonce') or '')}"></div>
          <div class="row-actions"><button class="btn primary" type="submit">Enroll self-custody key</button></div>
        </form>
        <form method="post" action="/tenant/keys/enroll-delegated">
          <div class="row-actions" style="margin-bottom:0"><button class="btn" type="submit">Enroll a delegated key for me</button>
          <span class="muted small">The platform signer generates the seed in the secrets store —
            it never transits this page. Honestly labeled below; not a KMS/HSM claim.</span></div>
        </form>
      </div>
      <div class="card">
        <h3>Countersigned re-enrollment (adjudicator, terminal key state)</h3>
        <p class="muted">An adjudicator whose key is in a terminal state is re-enrolled only
          countersigned by a tenant admin (the bootstrap-sole path is refused for this role).
          The subject's own enrollment nonce — from their Begin-enrollment step above — is
          required.</p>
        <form method="post" action="/tenant/keys/enroll-countersigned">
          <div class="field"><label>Identity</label>
            <select name="identity_id">{''.join(f'<option value="{e(p["identity_id"])}">{e(p["name"])}</option>' for p in ctx['adjudicators'])}</select></div>
          <div class="field"><label>Public key (hex)</label><input name="public_key" type="text" autocomplete="off" spellcheck="false"></div>
          <div class="field"><label>Proof signature (hex)</label><input name="proof_signature" type="text" autocomplete="off" spellcheck="false"></div>
          <div class="field"><label>Subject's enrollment nonce</label><input name="nonce" type="text" autocomplete="off"></div>
          <div class="row-actions" style="margin-bottom:0"><button class="btn" type="submit">Enroll countersigned</button></div>
        </form>
      </div>

      <h2>API keys &amp; service identities</h2>
      <p class="page-sub" style="margin-top:0">Machine principals are dedicated records, never
        human accounts (Spec 005 §5): an API key carries its own principal, a named study
        role class, and an explicit scope subset of that class's actions, with expiry
        (≤ 1 year). The secret is shown once, at issuance; only its hash is stored.</p>
      {banner_valid('API key issued — shown once.', f"key {ctx['issued_key']['key_id']} · secret {ctx['issued_key']['secret']} · principal {ctx['issued_key']['principal_name']}") if ctx.get('issued_key') else ''}
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:13%">Key</th><th style="width:15%">Principal</th><th style="width:11%">Role class</th><th style="width:19%">Scopes</th><th style="width:10%">Expires</th><th style="width:10%">Last used</th><th style="width:9%">State</th><th style="width:13%"></th></tr>
          </thead>
          <tbody>
{''.join(api_rows) if api_rows else '<tr><td colspan="8" class="muted">No API keys issued in this tenant.</td></tr>'}
          </tbody>
        </table>
      </div>
      <form method="post" action="/tenant/keys/apikey-issue">
        <div class="card">
          <div class="field"><label>Create a service identity for this key</label>
            <input name="service_name" type="text" autocomplete="off" placeholder="e.g. Ingest pipeline"></div>
          <div class="field"><label>…or bind the key to an existing principal</label>
            <select name="principal_id"><option value="">— create new (name above) —</option>{principal_options}</select></div>
          <div class="field"><label>Role class</label><select name="role_class">{role_options}</select>
            <div class="help">The console offers study role classes only — admin-plane powers are never minted as standing API keys here. Whatever the class, scopes must be a subset of its actions: a key can never hold a power its class denies a human, and the service validates and refuses by name.</div></div>
          <div class="field"><label>Scopes (action names, comma-separated)</label>
            <input name="scopes" type="text" autocomplete="off" placeholder="e.g. study.register_claim, study.log_query">
            <div class="help">Must be a subset of the role class's actions; the service validates and refuses by name.</div></div>
          <div class="field"><label>Expiry (days, ≤ 365)</label><input name="expires_days" type="text" value="90"></div>
          <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Issue API key</button></div>
        </div>
      </form>
"""
    ctx = {**ctx, "title": "Keys & bindings"}
    return tenant_shell(active="keys", ctx=ctx, body=body)


# -------------------------------------------------------- tenant: events

_EVENT_CLASSES = [
    ("all", "All"),
    ("identity.created", "Identity"),
    ("role.", "Roles"),
    ("key.", "Keys"),
    ("auth.", "Sign-in"),
    ("authz.", "Authorization"),
    ("breakglass.", "Break-glass"),
    ("scim.", "SCIM"),
    ("apikey.", "API keys"),
    ("webhook.", "Webhooks"),
    ("security.", "Security"),
]


def _event_rows(events: list[dict], expand_seq: Optional[int], base: str) -> str:
    rows = []
    for ev in events:
        p = ev.get("payload") or {}
        actor = p.get("actor_id") or ev.get("actor") or "—"
        who = actor_short(actor) if actor != "—" else "—"
        target = p.get("target") or "—"
        outcome = p.get("outcome") or "recorded"
        outcome_chip = {"recorded": "", "succeeded": "supported", "granted": "supported",
                        "failed": "contradicted", "denied": "contradicted"}.get(outcome, "")
        detail = ""
        if expand_seq is not None and ev.get("seq") == expand_seq:
            payload = json.dumps(p, indent=1, default=str, sort_keys=True)
            detail = (f'<tr class="detail-row"><td></td><td colspan="5">'
                      f'<div class="mono small" style="white-space:pre-wrap">{e(payload)}</div>'
                      f'<div class="muted small" style="margin-top:6px">The event as recorded — '
                      f"payload in full; the export carries the same payload plus the chain "
                      f"position and the checkpoint structure. Nothing here is a summary of "
                      f"the record; it is the record.</div></td></tr>")
        when_raw = p.get("ts") or p.get("ts_utc") or p.get("at") or ev.get("ts")
        when = when_raw[:16].replace("T", " ") if isinstance(when_raw, str) else fmt_ts(when_raw)
        rows.append(f"""<tr>
          <td data-h="Seq"><a href="{base}?expand={ev.get('seq')}">{ev.get('seq')}</a></td>
          <td data-h="When">{e(when)}</td>
          <td data-h="Event" class="evt">{e(ev.get('type'))}</td>
          <td data-h="Actor" class="mono">{e(who)}</td>
          <td data-h="Target" class="mono">{e(str(target)[:44])}</td>
          <td data-h="Outcome">{chip(outcome, outcome_chip) if outcome_chip else e(outcome)}</td>
        </tr>{detail}""")
    return "".join(rows)


def render_events(ctx: dict) -> str:
    t = ctx["tenant"]
    seg = []
    for key, label in _EVENT_CLASSES:
        cls = "on" if ctx["filter"] == key else ""
        href = "/tenant/events" if key == "all" else f"/tenant/events?class={e(key)}"
        seg.append(f'<a class="{cls}" href="{href}">{e(label)}</a>')
    verify_line = ""
    v = ctx.get("verify")
    if v:
        if v["ok"]:
            verify_line = (f'<div class="verify-line"><span class="chip supported">chain verification: passed</span>'
                           f'<span class="small muted">{v["events"]} events verified at request time; '
                           f'the latest anchor for this ledger is an internal checkpoint — '
                           f"an external anchor is a separate, recorded act.</span></div>")
        else:
            verify_line = (f'<div class="verify-line"><span class="chip invalid">chain verification: FAILED</span>'
                           f'<span class="small muted">break at seq {v["break_seq"]} — {e(v["reason"])}</span></div>')
    body = f"""{plane_strip('tenant', f"{e(t['name'])} only — this session can reach no other tenant's records, and no control here affects one.")}
      <h1>Lifecycle events</h1>
      <p class="page-sub">The tenant-plane projection of {e(t['name'])}'s audit ledger: every
        lifecycle act — identity, roles, keys, sign-ins, authorization decisions, SCIM,
        break-glass — is an appended event here, in order. Select a sequence number to
        expand the recorded payload in place.</p>
      {verify_line}
      <div class="seg" role="group" aria-label="Event class">{''.join(seg)}</div>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:7%">Seq</th><th style="width:15%">When</th><th style="width:26%">Event</th><th style="width:16%">Actor</th><th style="width:22%">Target</th><th style="width:14%">Outcome</th></tr>
          </thead>
          <tbody>
{_event_rows(ctx['events'], ctx.get('expand'), '/tenant/events') if ctx['events'] else '<tr><td colspan="6" class="muted">No events in this class.</td></tr>'}
          </tbody>
        </table>
      </div>
      <p class="small muted">Showing the most recent {len(ctx['events'])} events in this class.
        The full record — with chain positions and checkpoint structure — is the audit
        export, produced from the platform plane or under a break-glass session.</p>
"""
    ctx = {**ctx, "title": "Lifecycle events"}
    return tenant_shell(active="events", ctx=ctx, body=body)


# ------------------------------------------------------- platform: audit

def render_audit(ctx: dict) -> str:
    ledgers = ctx["ledgers"]  # [{key, label, base}]
    seg = []
    for led in ledgers:
        cls = "on" if led["key"] == ctx["selected"] else ""
        seg.append(f'<a class="{cls}" href="/platform/audit?ledger={e(led["key"])}">{e(led["label"])}</a>')
    v = ctx["verify"]
    if v["ok"]:
        verify_card = f"""<div class="card">
        <div class="verify-line">
          <span class="chip supported">chain intact</span>
          <span class="small">{v['events']} events · verified {e(ctx['verified_at'])}</span>
        </div>
        {kv([("Latest checkpoint root", f'<span class="mono small">{e(ctx["checkpoint_root"] or "—")}</span>'),
             ("Scope of this check", "hash chain + Merkle structure of this ledger only; a standalone verifier checks the same structure from the exported bundle, offline"),
             ("External anchor", ctx['anchor_text'])])}
        <p class="small muted" style="margin-bottom:0">What the green state means: every event's
          hash links to its predecessor and the Merkle checkpoints recomputed — as of the
          verification time above. It is not a claim about anything outside this ledger, and
          it is re-run at request time, never cached.</p>
      </div>"""
    else:
        verify_card = f"""<div class="gap-card">
        <div class="verify-line">
          <span class="chip invalid">chain verification failed</span>
          <span class="small">break at seq {v['break_seq']} — {e(v['reason'] or '')}</span>
        </div>
        <p class="small muted" style="margin-bottom:0">A failed chain is a security-significant
          state: the failure itself has been recorded as a security event in this ledger
          (T554), and the break is shown, not hidden. Investigate from the export, offline.</p>
      </div>"""
    notice = banner_valid("Export recorded.", ctx["notice"]) if ctx.get("notice") else ""
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    body = f"""{plane_strip('platform', 'Deployment scope — the audit inspector reads every ledger; tenant-plane sessions reach only their own tenant\u2019s projection (Lifecycle events).')}
      <h1>Audit ledger inspector</h1>
      <p class="page-sub">Append-only Axiomere ledgers (Spec 005 §9, CLM-005-10): deployment
        events in the deployment ledger, tenant events in each tenant's own ledger. The
        inspector verifies chains and exports bundles; it has no edit or delete path —
        corrections are later events.</p>
      {refusal}{notice}
      <div class="seg" role="group" aria-label="Ledger">{''.join(seg)}</div>
      {verify_card}

      <h2>Events — {e(ctx['selected_label'])}</h2>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:7%">Seq</th><th style="width:15%">When</th><th style="width:26%">Event</th><th style="width:16%">Actor</th><th style="width:22%">Target</th><th style="width:14%">Outcome</th></tr>
          </thead>
          <tbody>
{_event_rows(ctx['events'], ctx.get('expand'), '/platform/audit?ledger=' + e(ctx['selected']))}
          </tbody>
        </table>
      </div>
      <p class="small muted">Showing the most recent {len(ctx['events'])} events. Select a
        sequence number to expand the recorded payload in place — shown in full here,
        as the export carries it.</p>

      <h2>Export</h2>
      <form method="post" action="/platform/audit/export">
        <input type="hidden" name="ledger" value="{e(ctx['selected'])}">
        <div class="card">
          <div class="row-actions" style="margin-bottom:0">
            <button class="btn primary" type="submit">Export this ledger as a standalone-verifiable bundle</button>
            <span class="muted small">The export is itself an appended event
              (<span class="mono">audit.exported</span>) carrying the export id and bundle
              hash; anchors are recorded against it
              (<span class="mono">audit.export_anchored</span>) when an external anchoring
              act happens.</span>
          </div>
        </div>
      </form>
"""
    ctx = {**ctx, "title": "Audit ledger inspector"}
    return platform_shell(active="audit", ctx=ctx, body=body)


# -------------------------------------------------- platform: compliance

_FAMILY_NAMES = {
    "3.1": "Access Control", "3.2": "Awareness & Training",
    "3.3": "Audit & Accountability", "3.4": "Configuration Management",
    "3.5": "Identification & Authentication", "3.6": "Incident Response",
    "3.7": "Maintenance", "3.8": "Media Protection",
    "3.9": "Personnel Security", "3.10": "Physical Protection",
    "3.11": "Risk Assessment", "3.12": "Security Assessment",
    "3.13": "System & Communications Protection",
    "3.14": "System & Information Integrity",
}


def render_compliance(ctx: dict) -> str:
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    notice = banner_valid("Recorded.", ctx["notice"]) if ctx.get("notice") else ""
    fam_rows = []
    for fam, counts in ctx["families"]:
        fam_rows.append(f"""<tr>
          <td data-h="Family">{e(fam)} {e(_FAMILY_NAMES.get(fam, ''))}</td>
          <td data-h="Platform">{counts['Platform']}</td>
          <td data-h="Supports">{counts['Supports']}</td>
          <td data-h="Organizational">{counts['Organizational']}</td>
          <td data-h="Total"><strong>{sum(counts.values())}</strong></td>
        </tr>""")
    sprs = ctx["sprs"]
    if sprs is None:
        sprs_card = f"""<div class="card">
        <h3>NIST SP 800-171 self-assessment (SPRS)</h3>
        <p class="muted">No control states are seeded yet. Seeding derives one state per
          requirement from the classification matrix — mechanically, never by hand.</p>
        <form method="post" action="/platform/compliance/sprs-seed">
          <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Seed control states</button>
          <span class="muted small">A recorded act (<span class="mono">compliance.states_seeded</span>).</span></div>
        </form>
      </div>"""
    else:
        ded_rows = "".join(
            f'<tr><td data-h="Requirement" class="mono">{e(d["requirement"])}</td>'
            f'<td data-h="State">{e(d["state"])}</td>'
            f'<td data-h="Deduction">−{d["deduction"]}</td>'
            f'<td data-h="Basis">{e(d["evidence"] or d["gap_reason"] or "—")}</td></tr>'
            for d in sprs["deductions"])
        sprs_card = f"""<div class="card">
        <h3>NIST SP 800-171 self-assessment (SPRS)</h3>
        <div class="verify-line">
          <span class="chip {'supported' if sprs['score'] > 0 else 'invalid'}">self-score: {sprs['score']}</span>
          <span class="small muted">computed at request time by the E6 machinery from the
            {sprs['inputs']} recorded control states — never a stored number</span>
        </div>
        <p class="muted">Methodology {e(sprs['methodology'])} · seed {e(sprs['seed_version'])} ·
          total deduction {sprs['total_deduction']} · completeness failures
          {len(sprs['completeness_failures'])} · agreement failures
          {len(sprs['agreement_failures'])}.
          {e(sprs['submission'])} Submitting a score to SPRS is the operator's external act;
          this screen maintains the inputs.</p>
        <div class="card flush"><table>
          <thead><tr><th style="width:16%">Requirement</th><th style="width:20%">State</th><th style="width:12%">Deduction</th><th style="width:52%">Basis on record</th></tr></thead>
          <tbody>{ded_rows if ded_rows else '<tr><td colspan="4" class="muted">No deductions — every requirement is recorded implemented.</td></tr>'}</tbody>
        </table></div>
      </div>"""
    poam = ctx["poam"]
    poam_rows = []
    for item in poam["items"]:
        miles = "".join(
            f'<div class="mono small">{e(m["milestone_id"])} · {e(m["status"])} — {e(m["text"])}</div>'
            for m in item["milestones"]) or '<span class="muted small">no milestones</span>'
        poam_rows.append(f"""<tr>
          <td data-h="Item" class="mono">{e(item['item_id'])}</td>
          <td data-h="Weakness"><strong>{e(item['title'])}</strong><br><span class="muted small">{e(item['weakness'])}</span><br>{miles}</td>
          <td data-h="Requirements">{'<br>'.join(f'<span class="mono">{e(r)}</span>' for r in item['affected_requirements'])}</td>
          <td data-h="Status">{chip(item['status'], 'invalid' if item['status'] == 'open' else ('supported' if item['status'] == 'completed' else 'inconclusive'))}<br>
            <form method="post" action="/platform/compliance/poam-status" style="margin-top:6px">
              <input type="hidden" name="item_id" value="{e(item['item_id'])}">
              <select name="status"><option value="open">open</option><option value="in-progress">in-progress</option><option value="completed">completed</option><option value="risk-accepted">risk-accepted</option></select>
              <button class="btn" type="submit">Set</button></form>
            <form method="post" action="/platform/compliance/poam-milestone">
              <input type="hidden" name="item_id" value="{e(item['item_id'])}">
              <input name="text" type="text" placeholder="New milestone" autocomplete="off">
              <button class="btn" type="submit">Add</button></form></td>
          <td data-h="Owner / source">{e(item['owner'])}<br><span class="muted small">{e(item['source_ref'])}</span></td>
        </tr>""")
    marking_rows = "".join(
        f'<tr><td data-h="Tenant">{e(m["tenant"])}</td><td data-h="Marking">{e(m["text"])}</td></tr>'
        for m in ctx["markings"])
    fips = ctx["fips"]
    body = f"""{plane_strip('platform', 'Deployment scope — compliance evidence lives in the platform plane in v1; tenant admins see their own tenant\u2019s SPRS inputs, not the deployment register.')}
      <h1>Compliance evidence</h1>
      <p class="page-sub">This screen states what the records support and stops there. SPRS
        self-assessment inputs are maintained as recorded states (§12); the crypto inventory
        states which operations run in FIPS-validated modules and which do not. Nothing on
        this screen is a certification claim: a C3PAO assesses CMMC; SOC 2 is a readiness
        position, never "SOC 2 certified" (Spec 005 §12, CLM-005-23).</p>
      {refusal}{notice}
      <div class="stats">
        <div class="stat"><div class="num">110</div><div class="lab">800-171 requirements classified</div></div>
        <div class="stat"><div class="num">{ctx['class_totals']['Platform']}</div><div class="lab">Platform-satisfiable</div></div>
        <div class="stat"><div class="num">{ctx['class_totals']['Supports']}</div><div class="lab">Platform supports</div></div>
        <div class="stat"><div class="num">{ctx['class_totals']['Organizational']}</div><div class="lab">Purely organizational</div></div>
      </div>

      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:40%">Family</th><th style="width:15%">Platform</th><th style="width:15%">Supports</th><th style="width:15%">Organizational</th><th style="width:15%">Total</th></tr>
          </thead>
          <tbody>
{''.join(fam_rows)}
          </tbody>
        </table>
      </div>
      <p class="small muted">The matrix is a claim-bearing artifact (Spec 005 §12): each
        classification carries its justification in the matrix document; a C3PAO's
        disagreement is resolvable from the records this screen maintains.</p>

      {sprs_card}

      <h2>POA&amp;M register</h2>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:12%">Item</th><th style="width:36%">Weakness &amp; milestones</th><th style="width:14%">Requirements</th><th style="width:20%">Status</th><th style="width:18%">Owner / source</th></tr>
          </thead>
          <tbody>
{''.join(poam_rows) if poam_rows else '<tr><td colspan="5" class="muted">The register is empty.</td></tr>'}
          </tbody>
        </table>
      </div>
      <form method="post" action="/platform/compliance/poam-create">
        <div class="card">
          <div class="field"><label>Title</label><input name="title" type="text" autocomplete="off"></div>
          <div class="field"><label>Weakness</label><input name="weakness" type="text" autocomplete="off"></div>
          <div class="field"><label>Affected requirements (comma-separated)</label><input name="requirements" type="text" autocomplete="off"></div>
          <div class="field"><label>Source reference</label><input name="source_ref" type="text" autocomplete="off"></div>
          <div class="field"><label>Owner</label><input name="owner" type="text" autocomplete="off"></div>
          <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Add POA&amp;M item</button></div>
        </div>
      </form>

      <div class="gap-card">
        <h3>FIPS 140-3 — the honest gap (§3.13.11)</h3>
        <div class="verify-line">
          <span class="chip invalid">FIPS-validated cryptography: {fips['validated']} of {fips['operations']} operations</span>
        </div>
        <p class="muted" style="margin-bottom:0">Every cryptographic operation the platform
          performs is in the crypto inventory
          (<span class="mono">{e(fips['path'])}</span>), and none currently runs inside a
          FIPS 140-3 validated module boundary. Posture value is preserved (the operations are
          real, standard cryptography — Ed25519, SHA-256, HMAC, Argon2id/PBKDF2 vendor-side)
          but §3.13.11 is <strong>not implemented in v1</strong>: the SPRS self-score takes
          the deduction, and the POA&amp;M carries the remediation item — engaging a validated
          module (e.g. an HSM/KMS track) is a named, owner-level program decision, not an
          edit. That is the whole gap entry; it is stated here exactly as the SPRS inputs
          state it (CLM-005-31-adjacent; no claim is made).</p>
      </div>

      <div class="grid2">
        <div class="card">
          <h3>CUI marking (per tenant)</h3>
          <div class="card flush"><table><thead><tr><th>Tenant</th><th>Marking on record</th></tr></thead>
          <tbody>{marking_rows}</tbody></table></div>
          <p class="small muted" style="margin-bottom:0">CUI handling requirements flow from the
            customer's contract; the platform records markings where the customer has
            designated them and serves them verbatim on export-facing surfaces. Nothing is
            inferred from content.</p>
        </div>
        <div class="card">
          <h3>DFARS / FedRAMP posture</h3>
          <p class="muted" style="margin-bottom:0">A FedRAMP-authorized (or
            FedRAMP-equivalency-evidenced) hosted shape is a sales-gating requirement for
            DFARS 252.204-7012 covered defense information (§12.8). Tekmerion's hosted shape
            is <strong>not</strong> FedRAMP-authorized in v1; the self-hosted shape keeps CUI
            inside the customer's own boundary, where the customer's authorization applies.
            This is a standing flag for the owner and counsel — no console state changes it,
            and no claim is made for it (CLM-005-31 remains an open, draft claim by design).</p>
        </div>
      </div>
      <div class="card">
        <h3>SOC 2 — readiness, not certification</h3>
        <p class="muted" style="margin-bottom:0">The readiness package maps the platform's controls
          to the TSC with the gaps named (sole gap: no live pilot operating history yet); it is
          written as readiness evidence for a future Type I observation window. The phrase
          "SOC 2 certified" appears nowhere in product material (Spec 005 §12, CLM-005-23).</p>
      </div>
"""
    ctx = {**ctx, "title": "Compliance evidence"}
    return platform_shell(active="compliance", ctx=ctx, body=body)


# -------------------------------------------------------- platform: status

def render_status(ctx: dict) -> str:
    rows = []
    for led in ctx["ledgers"]:
        if led["ok"]:
            verify = state_chip("intact")
        else:
            verify = state_chip("broken") + f'<br><span class="small muted">break at seq {led["break_seq"]} — {e(led["reason"] or "")}</span>'
        rows.append(f"""<tr>
          <td data-h="Ledger"><strong>{e(led['label'])}</strong><br><span class="mono">{e(led['ref'])}</span></td>
          <td data-h="Chain state">{verify}</td>
          <td data-h="Events">{led['events']}</td>
          <td data-h="Latest checkpoint"><span class="mono">{e(led['checkpoint'])}</span></td>
          <td data-h="External anchor">{e(led['anchor'])}</td>
        </tr>""")
    pol = ctx["policy_defaults"]
    body = f"""{plane_strip('platform', 'Deployment scope — service state across the deployment; no tenant content, only ledger and service facts.')}
      <h1>System status</h1>
      <p class="page-sub">The deployment's own state, read from the records: ledger chain
        state per ledger, the §9 abuse-control contract the service enforces, and the
        identity posture. Every figure is computed at request time.</p>
      <div class="card flush">
        <table>
          <thead>
            <tr><th style="width:24%">Ledger</th><th style="width:22%">Chain state</th><th style="width:10%">Events</th><th style="width:20%">Latest checkpoint</th><th style="width:24%">External anchor</th></tr>
          </thead>
          <tbody>
{''.join(rows)}
          </tbody>
        </table>
      </div>

      <h2>Security baseline (Spec 005 §9)</h2>
      <div class="card">
        {kv([("Transport", "HTTPS only; HSTS max-age 63072000 sent on every response of this console; TLS 1.2+ at the deployment's terminator — the console binds the header contract, not a protocol claim"),
             ("Headers", '<span class="mono">Content-Security-Policy: default-src \'self\'; frame-ancestors \'none\'</span> · <span class="mono">X-Content-Type-Options: nosniff</span> · <span class="mono">Referrer-Policy: no-referrer</span> — set on every console response'),
             ("Session cookie", '<span class="mono">Secure; HttpOnly; SameSite=Lax; Path=/</span> (the baseline contract)'),
             ("Rate limits", f"per endpoint class (login, SAML, SCIM, append, break-glass), recorded stops (429 + Retry-After); tenant-policy default {pol['rate_limit_per_minute']}/min"),
             ("Break-glass", f"{ctx['breakglass_open']} session(s) open deployment-wide; every tenant's policy state is on the platform break-glass view — an open session is an alarmed state, never a routine one")])}
      </div>

      <div class="grid2">
        <div class="card">
          <h3>Identity posture</h3>
          {kv([("Tenants with an IdP", f"{ctx['idp_tenants']} of {ctx['tenant_total']} ({ctx['oidc_tenants']} OIDC · {ctx['saml_tenants']} SAML)"),
               ("MFA posture", f"{ctx['mfa_tenants']} tenant(s) record require-MFA policy; sessions without MFA evidence cannot mutate or step up, platform-side (CLM-005-27)"),
               ("Step-up freshness", f"recorded-policy default {fmt_duration(pol['stepup_freshness_seconds'])}")], '150px 1fr')}
        </div>
        <div class="card">
          <h3>Egress &amp; deliveries</h3>
          {kv([("Webhook subscriptions", str(ctx['webhook_subscriptions'])),
               ("Deliveries pending", f"{ctx['pending_deliveries']} — signed HMAC-SHA256 or Ed25519 deliveries; signing mode is a platform policy fact, uniform across subscribers"),
               ("Security egress", "T554 classes egress as incident-response records: authentication-failure bursts, chain-verification failures, break-glass use, rate-limit exhaustion")], '150px 1fr')}
        </div>
      </div>

      <div class="card">
        <h3>Platform break-glass overview</h3>
        <p class="muted" style="margin-bottom:0">Per-tenant declarations, pending
          authorizations, active sessions, and outstanding reviews — including the sessions
          whose declared second authorizer is this plane:
          <a href="/platform/break-glass">Platform break-glass →</a></p>
      </div>
"""
    ctx = {**ctx, "title": "System status"}
    return platform_shell(active="status", ctx=ctx, body=body)


# ------------------------------------------------------ break-glass screens

def _bg_state_label(state: str) -> str:
    return {"pending": "pending second authorization", "active": "break-glass active",
            "closed": "closed", "expired": "expired", "denied": "denied"}[state]


def _bg_session_log(sessions: list[dict], base: str) -> str:
    if not sessions:
        return """<div class="card empty">No break-glass sessions yet — for this tenant, none have occurred.
        When one does, it appears here as it happens: invoker, second authorizer, time box,
        alarm state, and the marked audit trail, closing with its post-use review item.</div>"""
    rows = []
    for s in sessions:
        if s["state"] in ("closed", "expired"):
            review = (state_chip("review recorded") if s["review_completed"]
                      else f'<a href="{base}#review-{e(s["review_item_id"] or "")}">{state_chip("review outstanding")}</a>')
        elif s["state"] == "denied":
            review = "— (never activated)"
        elif s["state"] == "active":
            review = "— (session open)"
        else:
            review = "—"
        end = {"expired": "time box exhausted", "closed": f"closed — {s['close_reason'] or 'closed'}",
               "denied": "second authorizer refused", "active": "session open",
               "pending": "awaiting authorization"}[s["state"]]
        actions = f" · {s['actions_taken']} action(s)" if s["state"] in ("closed", "expired", "active") else ""
        rows.append(f"""<tr>
          <td data-h="Session" class="mono">{short(s['bg_session_id'], 10, 0)}…</td>
          <td data-h="Invoker">{e(s['invoker_name'])}</td>
          <td data-h="State">{state_chip('denied' if s['state'] == 'denied' else ('expired' if s['state'] == 'expired' else ('closed' if s['state'] == 'closed' else ('pending second authorization' if s['state'] == 'pending' else 'active'))))}</td>
          <td data-h="How it ended">{e(end)}{actions}</td>
          <td data-h="Review">{review}</td>
        </tr>""")
    return f"""<div class="card flush">
        <table>
          <thead>
            <tr><th style="width:20%">Session</th><th style="width:16%">Invoker</th><th style="width:16%">State</th><th style="width:24%">How it ended</th><th style="width:24%">Review</th></tr>
          </thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>"""


def _bg_reviews(sessions: list[dict], base: str, can_review: bool) -> str:
    outstanding = [s for s in sessions
                   if s["state"] in ("closed", "expired") and s["review_item_id"]
                   and not s["review_completed"]]
    completed = [s for s in sessions
                 if s["state"] in ("closed", "expired") and s["review_completed"]]
    out = []
    for s in outstanding:
        acts = "; ".join(a.get("action", "") for a in s["actions"]) or "none"
        form = ""
        if can_review:
            form = f"""<form method="post" action="{base}/review">
          <input type="hidden" name="review_item_id" value="{e(s['review_item_id'])}">
          <div class="field"><label>Disposition</label>
            <select name="disposition">
              <option>reviewed — actions appropriate to the stated reason</option>
              <option>reviewed — concerns noted (say what, in the note)</option>
              <option>escalated — referred to platform security</option>
            </select></div>
          <div class="field"><label>Note (recorded with the disposition)</label>
            <input name="note" type="text" autocomplete="off"></div>
          <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Record disposition</button>
          <span class="muted small">Recording is final for this item — a second disposition is refused and the refusal is recorded.</span></div>
        </form>"""
        out.append(f"""<div class="card" id="review-{e(s['review_item_id'])}">
        <div class="verify-line">
          {state_chip('review outstanding')}
          <span class="mono">{e(s['review_item_id'])}</span>
          <span class="small muted">for session <span class="mono">{e(s['bg_session_id'])}</span></span>
        </div>
        {kv([("Invoker", f"{e(s['invoker_name'])} — authorized by {e(s['authorized_by_name'] or '—')}"),
             ("Reason", e(s['reason'])),
             ("Marked actions", f"<span class=\"mono\">{e(acts)}</span> — each recorded as breakglass.action in both ledgers, marked break_glass=true"),
             ("Alarm", "security.break_glass_use egressed at authorization (incident-response class, T554)")])}
        {form}
      </div>""")
    done = ""
    if completed:
        rows = "".join(
            f'<tr><td data-h="Review item" class="mono">{e(s["review_item_id"])}</td>'
            f'<td data-h="Session" class="mono">{short(s["bg_session_id"], 10, 0)}…</td>'
            f'<td data-h="Disposition">{state_chip("review recorded")}</td></tr>'
            for s in completed)
        done = (f'<h3>Completed reviews</h3><div class="card flush"><table><thead>'
                f"<tr><th>Review item</th><th>Session</th><th>Disposition</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>")
    return "".join(out) + done


def render_break_glass_tenant(ctx: dict) -> str:
    t = ctx["tenant"]
    base = "/tenant/break-glass"
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    notice = banner_valid("Recorded.", ctx["notice"]) if ctx.get("notice") else ""
    state = ctx["bg_state"]
    policy = state["policy"]
    sessions = state["sessions"]
    parts = [f"""{plane_strip('tenant', f"{e(t['name'])} only — break-glass policy is declared per tenant; the platform-plane variant lists every tenant's policy state and session log.")}
      <h1>Break-glass</h1>
      <p class="page-sub">Break-glass exists only as a named mechanism (CLM-005-10): pre-declared
        per tenant, dually authorized, time-boxed, alarmed, and every action under the session
        marked in the audit record. It mints a <em>session</em>, never a credential.
        <strong>There is no standing backdoor.</strong></p>
      {refusal}{notice}"""]
    # Policy card: undeclared (approved screen 8) or declared (extension 8a).
    if policy is None:
        role_boxes = "".join(
            f'<span style="margin-right:14px"><input type="checkbox" name="invoker_roles" value="{e(r)}"> {e(r)}</span>'
            for r in ctx["all_roles"])
        scope_boxes = "".join(
            f'<span style="margin-right:14px"><input type="checkbox" name="scopes" value="{e(s)}"> <span class="mono">{e(s)}</span></span>'
            for s in ctx["bg_scopes"])
        parts.append(f"""
      <h2>Policy — {e(t['name'])}</h2>
      <div class="card">
        <div class="verify-line">
          {chip('no declaration')}
        </div>
        <p class="muted">Break-glass cannot be invoked for this tenant. It becomes possible
          only when a tenant admin declares, in advance and on the record: who may invoke,
          which plane supplies the <strong>second authorizer</strong>, which of the
          mechanism's implementable scopes it may exercise, and the time-box ceiling
          (4 hours, hard-coded maximum).</p>
        <form method="post" action="{base}/declare">
          <div class="field"><label>Invoker roles (who may request a session)</label><div>{role_boxes}</div></div>
          <div class="field"><label>Second authorizer</label>
            <select name="second_authorizer_plane">
              <option value="platform_admin">a platform admin (the deployment plane)</option>
              <option value="tenant_admin">a second tenant admin (this plane)</option>
            </select>
            <div class="help">The invoker can never authorize their own session, whatever roles they hold.</div></div>
          <div class="field"><label>Scopes the mechanism may exercise</label><div>{scope_boxes}</div>
            <div class="help">Only actions the mechanism can exercise are declarable — a declaration naming a study power is refused, by name. Study powers can never be declared.</div></div>
          <div class="field"><label>Time-box ceiling (minutes, ≤ 240)</label>
            <input name="max_duration_minutes" type="text" value="60"></div>
          <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Declare the policy</button>
          <span class="muted small">Declaration is itself a recorded tenant-admin act
            (<span class="mono">breakglass.policy_declared</span>) and requires a fresh step-up.</span></div>
        </form>
      </div>

      <h2>What a declaration must name (the mechanism's shape)</h2>
      <div class="card">
        <p class="muted" style="margin:0 0 10px">Four facts, all recorded before any session can exist:</p>
        <ol class="clean" style="margin-bottom:0">
          <li><strong>Invoker roles</strong> — a holder of a named role may request a session.</li>
          <li><strong>A second authorizer</strong> — the session activates only on their recorded authorization; the invoker can never self-authorize.</li>
          <li><strong>Scopes</strong> — only the tenant-admin operations the mechanism implements: audit export, key management, membership management. Study powers are never declarable.</li>
          <li><strong>A time box</strong> — minutes to hours, ceiling 4 h, after which the session expires and a post-use review item is created automatically.</li>
        </ol>
      </div>
""")
    else:
        parts.append(f"""
      <h2>Policy — {e(t['name'])}</h2>
      <div class="card">
        <div class="verify-line">
          {chip('policy declared', 'supported')}
          <span class="small muted">declaration on the deployment record as well as here</span>
        </div>
        {kv([("Invoker roles", e(", ".join(policy['invoker_roles'])) + " — a holder of a named role may request a session"),
             ("Second authorizer", f"a <strong>{e(policy['second_authorizer_plane'].replace('_', ' '))}</strong>, per this tenant's declaration — never the invoker, whatever roles the invoker holds"),
             ("Time box", f"declared maximum <strong>{fmt_duration(policy['max_duration_seconds'])}</strong> — the 4 h ceiling is hard-coded; a declaration may set less, nothing sets more"),
             ("Scopes", " · ".join(f'<span class="mono">{e(s)}</span>' for s in policy['scopes']) + " — only actions the mechanism can exercise are declarable; study powers can never be declared"),
             ("Declared", f"{fmt_ts(policy['declared_at'])} by {e(actor_short(policy['declared_by_actor_id']))} (breakglass.policy_declared, tenant ledger) — declaration is itself a recorded act"),
             ("Alarm", "every step is recorded in this tenant's ledger <em>and</em> the deployment security log; authorization egresses a security.break_glass_use incident-response event")])}
        <form method="post" action="{base}/revoke-policy">
          <div class="row-actions" style="margin-bottom:0">
            <button class="btn danger" type="submit">Revoke declaration</button>
            <span class="muted small">Revoking a declaration denies pending sessions and closes
              active ones on the spot — revocation never leaves a live session behind.</span>
          </div>
        </form>
      </div>

      <h2>Invoke a session</h2>
      <div class="card">
        <p class="muted" style="margin-top:0">Invocation mints a <strong>pending</strong> session —
          it confers nothing until a second authorizer activates it, and the time box starts
          only at authorization.</p>
        <form method="post" action="{base}/invoke">
          <div class="field"><label>Reason (recorded verbatim)</label>
            <input name="reason" type="text" autocomplete="off"></div>
          <div class="field"><label>Requested time box (minutes)</label>
            <input name="duration_minutes" type="text" value="60">
            <div class="help">A request outside the declared maximum is refused and the refusal
              is recorded — in this tenant's ledger and the deployment log — before it is shown.</div></div>
          <div class="row-actions" style="margin-bottom:0"><button class="btn primary" type="submit">Invoke break-glass</button>
          <span class="muted small">Appends <span class="mono">breakglass.invoked</span> in both ledgers.</span></div>
        </form>
      </div>
""")
    # Pending + active session cards (extension 8b/8c).
    identity_options = "".join(
        f'<option value="{e(i["identity_id"])}">{e(i["name"])}</option>' for i in ctx["identities"])
    for s in sessions:
        if s["state"] == "pending":
            if s["viewer_can_authorize"]:
                authz = f"""<form method="post" action="{base}/authorize" style="display:inline">
            <input type="hidden" name="bg_session_id" value="{e(s['bg_session_id'])}">
            <button class="btn primary" type="submit">Authorize session</button></form>
          <form method="post" action="{base}/deny" style="display:inline">
            <input type="hidden" name="bg_session_id" value="{e(s['bg_session_id'])}">
            <button class="btn danger" type="submit">Deny</button></form>
          <span class="muted small">Authorization appends breakglass.authorized and egresses security.break_glass_use; the box starts now.</span>"""
            else:
                authz = (f'<span class="muted small">Awaiting the declared second authorizer '
                         f"({e(policy['second_authorizer_plane'].replace('_', ' ')) if policy else ''}). "
                         f"The invoker can never authorize their own session; a wrong-plane "
                         f"authorizer is refused, and the refusal is recorded in both ledgers.</span>")
            parts.append(f"""
      <h2>Session awaiting authorization</h2>
      <div class="card">
        <div class="verify-line">
          {chip('pending second authorization', 'inconclusive')}
          <span class="mono">{e(s['bg_session_id'])}</span>
        </div>
        {kv([("Invoker", f"{e(s['invoker_name'])} — {e(actor_short(s['invoker_actor_id']))}"),
             ("Reason", e(s['reason']) + " (recorded verbatim at invocation)"),
             ("Requested box", f"{fmt_duration(s['requested_duration_seconds'])} — the clock starts at authorization, not at invocation"),
             ("Invoked", fmt_ts(s['invoked_at']) + " (breakglass.invoked, recorded in both ledgers)"),
             ("Confers", "<strong>nothing yet.</strong> A pending session can perform no action; an attempt is refused and the refusal is recorded in both ledgers.")])}
        <div class="row-actions" style="margin-bottom:0">{authz}</div>
      </div>
""")
        elif s["state"] == "active":
            acts = "".join(
                f'<tr><td data-h="When">{fmt_ts(a.get("ts"))}</td>'
                f'<td data-h="Action" class="evt">{e(a.get("action", ""))}</td>'
                f'<td data-h="Target">{e(a.get("target", ""))}</td>'
                f'<td data-h="Recorded"><span class="mono">breakglass.action</span> · both ledgers · <span class="mono">break_glass=true</span></td></tr>'
                for a in s["actions"]) or \
                '<tr><td colspan="4" class="muted">No actions taken yet under this session.</td></tr>'
            parts.append(f"""
      <div class="gap-card">
        <div class="verify-line">
          {chip('break-glass session active', 'invalid')}
          <span class="mono">{e(s['bg_session_id'])}</span>
        </div>
        {kv([("Invoker", f"{e(s['invoker_name'])} — {e(actor_short(s['invoker_actor_id']))}"),
             ("Authorized by", f"{e(s['authorized_by_name'] or '—')} — the declared second-authorizer plane, {fmt_ts(s['authorized_at'])}"),
             ("Reason", e(s['reason'])),
             ("Expires", fmt_ts(s['expires_at']) + " — <strong>no extension exists</strong>; a longer need is a new declaration and a new session. At expiry the session closes automatically and its post-use review item is created."),
             ("Alarm", "authorization was recorded in both ledgers and egressed as security.break_glass_use")])}
        <form method="post" action="{base}/close">
          <input type="hidden" name="bg_session_id" value="{e(s['bg_session_id'])}">
          <div class="row-actions" style="margin-bottom:0">
            <button class="btn danger" type="submit">Close session now</button>
            <span class="muted small">Closing ends the session immediately and creates the post-use review item.</span>
          </div>
        </form>
      </div>

      <h2>Act under this session</h2>
      <div class="card">
        <p class="muted" style="margin-top:0">Only the declaration's scopes can be exercised, and
          they dispatch through the <strong>same service cores</strong> as the tenant plane —
          every act, granted or refused, is a marked <span class="mono">breakglass.action</span>
          event in <strong>both</strong> ledgers.</p>
        <form method="post" action="{base}/act">
          <input type="hidden" name="bg_session_id" value="{e(s['bg_session_id'])}">
          <div class="row-actions">
            <button class="btn" type="submit" name="action" value="tenant.audit_export">Export the tenant audit record</button>
            <span class="mono small">tenant.audit_export</span>
          </div>
          <div class="row-actions">
            <span class="field" style="margin:0"><label>Key fingerprint (full)</label>
            <input name="fingerprint" type="text" autocomplete="off" spellcheck="false"></span>
            <button class="btn" type="submit" name="action" value="tenant.key_manage">Revoke that key</button>
            <span class="mono small">tenant.key_manage</span>
          </div>
          <div class="row-actions" style="margin-bottom:0">
            <span class="field" style="margin:0"><label>Identity</label>
            <select name="identity_id">{identity_options}</select></span>
            <button class="btn" type="submit" name="action" value="tenant.member_manage">Deactivate that identity</button>
            <span class="mono small">tenant.member_manage</span>
          </div>
        </form>
      </div>

      <h2>Marked actions under this session</h2>
      <div class="card flush">
        <table>
          <thead><tr><th style="width:14%">When</th><th style="width:24%">Action</th><th style="width:34%">Target</th><th style="width:28%">Recorded</th></tr></thead>
          <tbody>{acts}</tbody>
        </table>
      </div>
""")
    parts.append(f"""
      <h2>Session log</h2>
      {_bg_session_log(sessions, base)}
""")
    reviews = _bg_reviews(sessions, base, can_review=True)
    if reviews:
        parts.append(f"""
      <h2>Post-use reviews</h2>
      <p class="page-sub" style="margin-top:0">Every closed or expired session leaves a review
        item, created automatically at close. The disposition is a tenant admin's recorded
        act — it appends <span class="mono">breakglass.review_completed</span>; it never edits
        the session's record, and an item is completable exactly once.</p>
      {reviews}
""")
    ctx = {**ctx, "title": "Break-glass"}
    return tenant_shell(active="break-glass", ctx=ctx, body="".join(parts))


def render_break_glass_platform(ctx: dict) -> str:
    """Platform variant: every tenant's policy state and session log,
    plus the pending sessions whose declared second authorizer is
    this plane (authorizing here is T529's second door)."""
    base = "/platform/break-glass"
    refusal = banner_refusal("Refused.", ctx["refusal"]) if ctx.get("refusal") else ""
    notice = banner_valid("Recorded.", ctx["notice"]) if ctx.get("notice") else ""
    sections = []
    for entry in ctx["tenants"]:
        tid = entry["tenant_id"]
        st = entry["state"]
        policy = st["policy"]
        policy_line = (chip("no declaration") if policy is None else
                       chip("policy declared", "supported") +
                       f' <span class="small muted">authorizer: {e(policy["second_authorizer_plane"])} · max {fmt_duration(policy["max_duration_seconds"])} · scopes: {e(", ".join(policy["scopes"]))}</span>')
        pending_forms = ""
        for s in st["sessions"]:
            if s["state"] == "pending" and entry["viewer_can_authorize"]:
                pending_forms += f"""<div class="row-actions">
          <span class="mono">{e(s['bg_session_id'])}</span>
          <span class="muted small">invoker {e(s['invoker_name'])} · {e(s['reason'])} · box {fmt_duration(s['requested_duration_seconds'])}</span>
          <form method="post" action="{base}/authorize" style="display:inline">
            <input type="hidden" name="tenant_id" value="{e(tid)}">
            <input type="hidden" name="bg_session_id" value="{e(s['bg_session_id'])}">
            <button class="btn primary" type="submit">Authorize</button></form>
          <form method="post" action="{base}/deny" style="display:inline">
            <input type="hidden" name="tenant_id" value="{e(tid)}">
            <input type="hidden" name="bg_session_id" value="{e(s['bg_session_id'])}">
            <button class="btn danger" type="submit">Deny</button></form>
        </div>"""
        sections.append(f"""
      <h2>{e(entry['tenant_name'])} <span class="mono small muted">{e(tid)}</span></h2>
      <div class="card">
        <div class="verify-line">{policy_line}</div>
        {pending_forms}
      </div>
      {_bg_session_log(st['sessions'], base)}
      {_bg_reviews(st['sessions'], base, can_review=False)}
""")
    body = f"""{plane_strip('platform', 'Deployment scope — break-glass policy state and session logs for every tenant; authorizing here is possible only where the tenant declared this plane as second authorizer.')}
      <h1>Break-glass — platform view</h1>
      <p class="page-sub">Break-glass exists only as a named mechanism (CLM-005-10): pre-declared
        per tenant, dually authorized, time-boxed, alarmed. This plane sees policy state and
        session logs for every tenant, and supplies the second authorization where a tenant
        declared it. <strong>There is no standing backdoor</strong> — this view grants no
        session of its own.</p>
      {refusal}{notice}
      {''.join(sections) if sections else '<div class="card empty">No tenants.</div>'}
"""
    ctx = {**ctx, "title": "Break-glass — platform view"}
    return platform_shell(active="break-glass", ctx=ctx, body=body)
