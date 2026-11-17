# How it works, in plain words

Venture Builder is a small team of AI helpers with a strict manager.

1. **You give a brief.** Your starting idea, your skills, budget, hours per week, who you want to sell to, and your values. A sentence-style brief works too: the intake agent turns it into fields.
2. **The safety check runs first.** Physical goods, financial or crypto products, and health or legal advice products are refused before any work starts.
3. **Phase 1, Discover.** The researcher sharpens your idea, suggests two alternatives, and reads real public discussions (Hacker News, Reddit, GitHub, Stack Exchange) for people who have the problem. Every claim links to its source, or says `ASSUMPTION`. The scorer compares your idea with the alternatives using fixed formulas. You get a customer profile and a Mom Test interview guide. After you have talked to real people, paste your notes into the dashboard: an agent separates commitments (time, money, introductions) from compliments and quotes only what your notes say.
4. **Gate.** Pass marks are fixed in code before the data is seen. The gate recommends go, repeat, pivot or stop, with reasons. **You** click the decision. Before each gate, a critic agent challenges the phase's documents and their authors answer: a mistake they concede is corrected in the document (only when safety checks pass), and anything still open is shown to you next to the gate. The debate never changes the gate's recommendation.
5. **Phase 2, Validate.** A Lean Canvas and a landing page with an honest waitlist form. The demand test target (for example 100 real sign-ups in 14 days) is set before the test starts.
6. **Phase 3, Build.** The builder writes the product itself (modules with steps, examples, checklists) and a user guide. A verifier agent checks each module for factual errors and runs its SQL examples; a module with errors is revised once. An originality check (plain code) makes sure the product copies no passage from the sources it read and does not take the name of an existing product it found. Twelve automatic tests, originality among them, must all pass.
7. **Phase 4, Commercial setup.** A price based on prices found in the sources, and draft terms, privacy and refund policies. No payments.
8. **Phase 5, Launch.** A store page and launch posts for you to publish yourself, plus a full test of "payment → automatic delivery → refund removes access → books balance" against a MOCKED payment provider. Before you approve anything, a promise checker matches every promise on the store page and in each post to the product, the price, the refund policy and the delivery test. A promise it can't prove is flagged for you to confirm or reword, and a page or post with a promise the product contradicts can't be approved.
9. **Phase 6, Operate and learn.** A support kit, honest metrics (MOCKED test numbers never count), and a persevere-or-pivot memo.

## Your controls

- **Gate buttons:** Go, Repeat, Pivot, Stop. The recommended one is highlighted. Choosing differently is allowed and is logged as an override.
- **Approval queue:** every page, post, message or refund waits for Approve or Reject. After approval it goes to an outbox for you to publish; the system never posts by itself.
- **Ask the team:** a box for free-text requests. Every request passes the guardrails first.
- **Decision log:** every action, which model did it, which sources it used, what it cost ($0.00) and who approved it.

## Why it can say "stop"

The scores and gates are plain code, not model opinions. A model can be persuaded; a threshold in `gates.py` can't. If the evidence is weak and no alternative is stronger, the system recommends stopping, and it says why.
