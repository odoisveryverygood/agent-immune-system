# Bounded repair revision — 2026-10-17

Implemented on `feature/verified-repair-revision`.

A candidate first faces the immutable original attack and public normal-purchase checks. If those fail, an investigator diagnoses the observed receipts and a child repair agent proposes one constrained revision. Both use the existing root budget. Catalog pricing and the original discount limit are enforced deterministically. The revised candidate repeats the same public checks. Only a passing candidate reaches the private attacks and independent final review. Failed second attempts remain unverified. The UI preserves both candidate outcomes across refreshes.

## Verification

- 96 backend unittest tests passed: target 35, review 38, heldout 9, integration 14.
- 13 frontend unit tests passed.
- 10 Playwright browser tests passed, including rejected/revised candidate display and refresh persistence without claiming final verification.
- TypeScript and Vite production build passed; git diff whitespace check passed.
- New synthetic integration tests prove recovery from an overstrict patch, rejection of a security-weakening revision, termination after a second failed candidate, preservation of root model budget, and exclusion of private attack cases from revision prompts. They exercise the real target/reviewer adapters with fake models and explicitly synthetic sandbox provenance.
- Two actual live runs reached Crusoe HTTP 429 before repair. Both stopped without fallback or a success claim. The new revision path has NOT been verified with real models. Earlier main-branch live verification does not establish this feature's live recovery behavior.

No code was pushed or merged into main.
