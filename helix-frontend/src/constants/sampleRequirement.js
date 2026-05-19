/** Realistic ambiguous PRD for demos — payment + auth with intentional gaps. */
export const SAMPLE_REQUIREMENT = `Title: Unified Pay & Identity (maybe)

We need the new checkout thing to work better soon. Users should be able to pay quickly.

Authentication:
- Support "the usual" login options. SSO might be required for enterprise but not sure which IdP.
- Session length should be secure. Revoke access when needed.

Payments:
- Integrate with our payment partner (contract is being renewed — vendor TBD).
- Handle cards and wallets. Refunds should happen "fast" (legal wants wording reviewed).
- PCI: we must be compliant; exact scope (SAQ vs full) is open.

Edge cases:
- If the user is "blocked" for fraud-ish reasons, show a message (copy not finalized).
- International: support multiple currencies "where it makes sense" — FX policy undefined.

Non-goals (probably):
- Maybe no crypto this quarter unless sales insists.

Success:
- Conversion goes up.
- Ops should see fewer tickets about payments failing "randomly" (define random).

Timeline: aggressive target before the big marketing push (date TBC).`
