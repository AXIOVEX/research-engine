# Adoption record — source registry discovery tier (§8)

**Status:** Adoption record, dated 2026-10-13, recording an owner directive relayed from the main chat. This note extends the scholarly source registry recorded in `01-source-layer.md` §3 (adopted 2026-10-11) with the registry's new §8: a discovery tier of non-WWW and shadow sources.

**Canonical text:** §8 of the research sources registry, `research-sources-registry.md` (kept with the research notes). That registry is the canonical source for this tier. This note summarizes the tier and what it means for this project; it does not copy the registry text, apart from the standing discipline quoted below.

## Standing discipline for the tier

The registry's standing discipline, quoted in full:

> Standing discipline for this section: these sources extend discovery breadth only. Anything found here is a lead, never evidence. A load-bearing document must be verified against a legitimate copy (publisher, library, or a §1–§4 source) before it can bear on any claim, and the verification recorded. Shadow libraries are infringing sources in the United States; the owner directed their inclusion on 2026-10-13 with this discipline attached. Access was verified live from the Muse VM on 2026-10-13 unless an entry says otherwise.

## The tier

- **Anna's Archive** — meta-search across the major shadow libraries. Access: annas-archive.li.
- **Sci-Hub** — paper full text by DOI. Access: sci-hub.st.
- **Library Genesis** — book and paper shadow library. Access: libgen.li.
- **Ahmia** — clearnet search engine indexing Tor onion services. Access: ahmia.fi; fetching an onion result runs through the owner's Tor.
- **IPFS** — content-addressed storage, where a fetched object is self-verifying against its content identifier. Access: the filebase public gateway is the standing gateway from the Muse VM; the ipfs.io, dweb.link, w3s.link, and Pinata gateways returned 403 to this VM.
- **Gopher** — the pre-web document network. Access: the Floodgap web proxy (gopher.floodgap.com/gopher/gw); native gopher is not available from the Muse VM.
- **Gemini** — a lightweight text protocol between gopher and the web. Access: the portal.mozz.us proxy.
- **Usenet archives** — decades of technical discussion. Access: web archives; Google Groups rate-limited the Muse VM, so use at low volume or through alternate archives.
- **I2P** — the I2P anonymity network and its native sites. Access: the owner runs the I2P Windows service on his machine (router HTTP proxy 127.0.0.1:4444); the Muse VM cannot join I2P directly, so the fetch route is pending the desktop fetch integration below.
- **Tor** — onion services beyond what Ahmia indexes. Access: the owner's Tor Browser now; a headless tor service on the same machine is the planned programmatic route, via the desktop fetch integration.
- **Freenet (Hyphanet)** — a censorship-resistant publishing network read through a local node. Planned, not yet installed; it joins this tier's discipline when live.
- **Desktop fetch integration** — one fetch router on the owner's desktop, driven through the existing desktop-relay, routing each address type to I2P, Tor, Freenet, or direct. It is being designed in the main chat; nothing is built by this note.

## What this adoption means for Tekmerion

- **No new connectors are created.** The engine's evidence-bearing connectors remain Crossref, OpenAlex, and CORE. Discovery-tier sources are not connectors and produce no evidence records.
- **Anything found through the tier is a lead only.** A document enters a study only through the existing citation-verification path against a legitimate copy, with the licence basis recorded. The citation machinery already refuses records without a licence basis, so a document sourced from the tier cannot enter a bundle as evidence by construction.
- **Verification is recorded with both paths.** When a lead from the tier is verified against a legitimate copy, that verification and both provenance paths — where the lead was found and where it was verified — are recorded in the study record.
- **This note authorizes no fetching from the tier.** The desktop fetch integration will be briefed separately when it exists.
