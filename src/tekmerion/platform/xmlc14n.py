"""Exclusive XML Canonicalization (xml-exc-c14n), implemented in-repo
(Spec 005 E2, T514). XML-DSig verification needs a byte-exact
canonical form of the signed subtrees; the platform's dependency
posture is stdlib-only, so the canonicalizer lives here, next to the
pure-Python RSA verification in `oidc.py`. Prototype-grade, like the
rest of the service-layer crypto (crypto inventory, T549): it is
validated for determinism, content sensitivity, and equivalence under
insignificant reformatting by the E2 test battery, and against the
fixture IdP's independently-constructed signatures — NOT against a
live Shibboleth IdP (recorded as remains-not-understood at the E2
exit).

Scope: the WithoutComments variant (the only one the SAML SP uses).
Namespace handling follows exc-c14n §2: an element renders the
in-scope namespaces it (or its attributes) *visibly utilize*, if an
ancestor within the canonicalized node-set has not already rendered
the same prefix→URI binding. The apex element additionally renders
visibly-utilized namespaces inherited from ancestors outside the
node-set — the caller supplies that in-scope context, gathered from
the parsed document (see `in_scope_namespaces`).
"""

from __future__ import annotations

from xml.dom import Node, minidom

XML_NS = "http://www.w3.org/XML/1998/namespace"
EXC_C14N = "http://www.w3.org/2001/10/xml-exc-c14n#"


def parse_xml(data: bytes) -> minidom.Document:
    """Parse XML for SAML processing. Documents carrying a DOCTYPE are
    refused outright: SAML messages never need one, and refusing it
    removes the entity-expansion surface (XXE / billion-laughs) from
    a parser (expat) that would otherwise process internal subsets."""
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError("XML documents with DOCTYPE/ENTITY declarations are refused")
    return minidom.parseString(data)


def in_scope_namespaces(element) -> dict[str, str]:
    """prefix -> URI for every namespace declaration in scope at
    `element`, gathered by walking its ancestor chain (nearest
    declaration wins). The empty-string key is the default namespace."""
    chain = []
    node = element
    while node is not None and node.nodeType == Node.ELEMENT_NODE:
        chain.append(node)
        node = node.parentNode
    scope: dict[str, str] = {}
    for el in reversed(chain):  # outermost first so nearer decls override
        if el.attributes is not None:
            for i in range(el.attributes.length):
                attr = el.attributes.item(i)
                if attr.name == "xmlns":
                    scope[""] = attr.value
                elif attr.name.startswith("xmlns:"):
                    scope[attr.name[len("xmlns:"):]] = attr.value
    scope.setdefault("xml", XML_NS)
    return scope


def _escape_text(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace("\r", "&#xD;"))


def _escape_attr(value: str) -> str:
    return (value.replace("&", "&amp;").replace("<", "&lt;")
            .replace('"', "&quot;").replace("\t", "&#x9;")
            .replace("\n", "&#xA;").replace("\r", "&#xD;"))


def _utilized_namespaces(element, scope: dict[str, str]) -> dict[str, str]:
    """The namespaces this element visibly utilizes (exc-c14n §2.1):
    its own name's namespace, plus the namespaces of its prefixed
    attributes. `xml` is predeclared and never rendered."""
    used: dict[str, str] = {}
    if element.prefix:
        if element.prefix != "xml" and element.prefix in scope:
            used[element.prefix] = scope[element.prefix]
    elif element.namespaceURI:
        # Unprefixed element name in a namespace: utilizes the default.
        if scope.get("", "") == element.namespaceURI:
            used[""] = element.namespaceURI
    if element.attributes is not None:
        for i in range(element.attributes.length):
            attr = element.attributes.item(i)
            if attr.prefix and attr.prefix != "xml" and attr.prefix in scope:
                used[attr.prefix] = scope[attr.prefix]
    return used


def canonicalize(element, apex_scope: dict[str, str] | None = None) -> bytes:
    """Canonical bytes for the subtree rooted at `element`.
    `apex_scope` is the in-scope namespace map at the apex (from
    `in_scope_namespaces` on the original element, when the subtree
    was cloned out of its document for the enveloped transform)."""
    scope = dict(apex_scope) if apex_scope is not None else in_scope_namespaces(element)
    out: list[str] = []
    _render(element, scope, {}, out)
    return "".join(out).encode("utf-8")


def _render(element, scope: dict[str, str], rendered: dict[str, str],
            out: list[str]) -> None:
    # Merge this element's own declarations into the effective scope.
    eff_scope = dict(scope)
    decls_here: dict[str, str] = {}
    attrs: list = []
    if element.attributes is not None:
        for i in range(element.attributes.length):
            attr = element.attributes.item(i)
            if attr.name == "xmlns":
                decls_here[""] = attr.value
                eff_scope[""] = attr.value
            elif attr.name.startswith("xmlns:"):
                decls_here[attr.name[len("xmlns:"):]] = attr.value
                eff_scope[attr.name[len("xmlns:"):]] = attr.value
            else:
                attrs.append(attr)
    utilized = _utilized_namespaces(element, eff_scope)
    # Render utilized namespaces not already rendered identically by
    # an ancestor *within the node set*; a conflicting re-declaration
    # deeper in the tree renders again (exc-c14n §2.3).
    to_render = {p: u for p, u in utilized.items() if rendered.get(p) != u}
    new_rendered = dict(rendered)
    new_rendered.update(to_render)

    out.append("<")
    out.append(element.tagName)
    for prefix in sorted(to_render, key=lambda p: (p != "", p)):
        if prefix == "":
            out.append(f' xmlns="{_escape_attr(to_render[prefix])}"')
        else:
            out.append(f' xmlns:{prefix}="{_escape_attr(to_render[prefix])}"')
    attrs.sort(key=lambda a: (a.namespaceURI or "", a.localName or a.name))
    for attr in attrs:
        out.append(f' {attr.name}="{_escape_attr(attr.value)}"')
    out.append(">")
    for child in element.childNodes:
        if child.nodeType == Node.ELEMENT_NODE:
            _render(child, eff_scope, new_rendered, out)
        elif child.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
            out.append(_escape_text(child.data))
        elif child.nodeType == Node.PROCESSING_INSTRUCTION_NODE:
            out.append(f"<?{child.target}")
            if child.data:
                out.append(f" {child.data}")
            out.append("?>")
        # Comments are dropped (WithoutComments); other node kinds
        # do not occur in SAML content.
    out.append(f"</{element.tagName}>")
