# Security / customer policy council

Verified live run: run_4d372f64be8c4aa1b9c8875a8574593f, 25.3 seconds.

Candidate 1: security accepted; customer challenged with normal-purchase receipts and a constraint restoring the authorized discount. A child investigator consumed both positions; a depth-2 repair child produced a revision citing both evidence sets. Candidate 2: both agents accepted. Final verification: 8/8 private attacks safe, 2/2 legitimate purchases accepted, 23/24 model calls.

New scenario: Security vs customer · seeded drill. Both advocates are separate tasks using the shared model budget. They receive only their relevant public receipts, not private attacks. Their model-proposed constraints are validated against bounded domain rules. Revisions must satisfy both constraint sets and cite evidence from both advocates. Deterministic checks retain final authority. One unsuccessful attempt stopped at invalid_advocate_position before revision; explicit perspective-specific output shapes resolved the successful run.

Scope: owned simulated store, deliberately seeded attack and bad initial policy. This is bounded policy negotiation, not unconstrained debate or production deployment. Model explanations are opinions, not replacements for numeric receipts. Original demo remains available on port 5176. New scenario is served on port 5177.

Validation: existing 106 backend tests plus 6 council tests passed; 13 frontend unit tests, 11 browser tests and production build passed. Browser inspection confirmed both advocate nodes, candidate positions, constraints and receipts.

http://127.0.0.1:5177/?run=run_4d372f64be8c4aa1b9c8875a8574593f
