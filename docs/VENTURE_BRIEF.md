# Lokito — Venture Creation brief

## Problem

People can identify nearby places but still spend time checking which place offers a toilet, drinking water, a suitable prayer space or wheelchair access. The hypothesis is that **facility-level uncertainty**, particularly access and current condition, creates avoidable search effort. This has not yet been validated through user research.

## Solution and distinction

Lokito (Lokasi Toilet) starts with the immediate need for a suitable toilet. It presents the nearest mapped option, concise known information and a directions handoff. Prayer spaces and drinking water are secondary options. Its intended differentiation is recent, useful facility detail: access conditions, fees, opening hours, accessibility, condition and verification. Coordinates alone are easy to replicate; reliable enrichment and a repeatable verification operation could become the strategic data asset.

The MVP demonstrates toilet-first discovery, coordinated cards and map, geographic ranking, preferences, external directions, visible unknowns, provenance and pending community observations. It does not claim a validated advantage over existing map products.

## Initial market and development scope

Jakarta is the pilot. Candidate early users include commuters, students, visitors, caregivers and people who need accessible facilities. These are segments to investigate, not proven customers. Start field work in a small transit/campus/commercial area before expanding to Jabodetabek, major Indonesian cities and eventually nationwide coverage.

## Hybrid data strategy

1. OSM/public data seed: a real starting inventory with source IDs and an audit trail.
2. Official government/open datasets: investigate availability, licence, scope and update cadence before importing. None are integrated yet.
3. Community observations: availability, condition and issues, followed by moderation and anti-abuse checks.
4. Provider/owner submissions: validate authority and periodically reconfirm facility details.

Keep source facts and observations separate. A download date is not a verification date. A future verified badge should require evidence, review and expiry rules. No proprietary ownership over OSM coordinates is claimed; any future enriched database strategy must account for ODbL obligations.

## Business model hypotheses

| Candidate model | Who might pay | What must be validated |
|---|---|---|
| Verified provider profiles | Malls, campuses, property managers | Value of keeping facility details accurate and visible |
| Clearly labelled promoted listings | Suitable facility providers | Commercial demand without harming need relevance or trust |
| Partner facility directories | Transport and tourism operators | Procurement, integration cost and maintenance responsibility |
| Coverage/condition analytics | Property operators or government partners | Decision value, representativeness and privacy requirements |

No payments, customer commitments or revenue forecasts are implemented. Operational cost hypotheses include field checks, moderation, partner coordination and maintenance. Trust must not become a benefit available only to paying facilities.

## Evidence from the prototype

The snapshot contains **5,824 OSM objects**: **141 toilets**, **5,645 worship facilities**, and **38 drinking-water points**. Names are present for **92.60%**, but access, hours, wheelchair and fee metadata each cover less than 1% of the total. These figures establish data acquisition feasibility and expose the enrichment challenge. They do not measure Jakarta-wide facility supply or business demand.

## Proposed next experiments

- Observe 8–12 candidate users completing realistic facility-finding tasks with existing tools and the MVP; compare time, successful selection and confidence. The sample size is an exploratory plan, not a completed study.
- Field-check a small set of 30–50 mapped facilities in one district with operators and accessibility users; record availability, entry, fee, hours, entrance and wheelchair details.
- Discuss maintenance responsibility and willingness to pilot with 3–5 potential institutional partners.
- Define verification expiry, minimum evidence and moderation standards before adding trusted badges.

## Lecturer demonstration — approximately four minutes

1. **0:00–0:40: Immediate value.** Open Lokito. The closest toilet is already featured near Bundaran HI. Confirm the starting point and explain the goal: finding a nearby toilet suitable for the user's needs.
2. **0:40–1:30: Choose and go.** Show the featured card, its honest missing-information message and Open directions. Choose a nearby card or numbered map pin; both share the same selected facility. Distances are straight-line estimates; Google Maps supplies the route.
3. **1:30–2:15: Personal needs.** Open Preferences for wheelchair, free or public-access requirements. Explain why sparse source information can leave few matches. Show Prayer spaces and Drinking water under Other facilities, then return to Toilets.
4. **2:15–3:05: Trust.** Open View details and the Report a change disclosure. Save only a real visit observation. QA submissions use an isolated database; observations do not create a verified badge.
5. **3:05–4:00: Evidence and venture.** Open Data & trust for the real snapshot and coverage gaps, then About for the focused proposition. Frame partner maintenance and revenue as hypotheses; the next step is a small field-verified pilot.

## Seven talking points

- The problem is uncertainty about a needed facility, even when a nearby place is easy to find.
- The product starts with a need and ranks matching mapped facilities nearby.
- Visible access details and unknowns help avoid unjustified confidence.
- Real Jakarta public data make a low-cost technical starting point possible.
- Long-term value could come from trustworthy, recent facility information and partner maintenance.
- Geographic expansion should follow evidence of demand and a repeatable verification process.
- Provider profiles, partnerships and aggregated analytics are business hypotheses to test, not proven revenue streams.
