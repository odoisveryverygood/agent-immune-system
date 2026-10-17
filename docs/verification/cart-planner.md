# Cart Planner portability verification

A second, separately implemented cart-planning agent passed the unchanged recursive repair workflow against real Crusoe inference, Nemotron review, You.com research and OpenShell checkout execution.

Run: `run_17c12e373f2b4cac92c684fa4060fff9`. Elapsed: 27.4 seconds. Model calls: 19/24. Private attacks: 8/8 safe, zero errors. Normal purchases: 2/2 accepted. Candidate 1: rejected (1/2 normal purchases). Candidate 2: public checks passed, final verification passed.

Cart Planner produces a validated cart schema, translated into checkout arguments by its own adapter. It does not use the original target's decision prompt or checkout JSON parser. Both implementations share the sandbox store and constrained policy-repair contract. Every model dispatch still uses the root budget.

This is a second implementation built by us, not an independently sourced third-party shopping product. The deliberately seeded recovery drill remains disclosed. Repairs modify checkout policy, not arbitrary agent source code. These results demonstrate two compatible implementations; they do not establish compatibility with arbitrary agents or production stores.

Demo: http://127.0.0.1:5176/?run=run_17c12e373f2b4cac92c684fa4060fff9

Select Cart Planner · second agent, Live models, Recovery drill · seeded fault, then Run. The URL above restores prior live evidence; a fresh Run starts new provider calls. Original demo remains on port 5175.
