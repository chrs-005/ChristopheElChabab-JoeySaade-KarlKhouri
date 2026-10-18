# Real evidence index

The [Joey pytest output](joey-pytest-2026-10-17.txt) is actual local execution of `python -m pytest tests/test_joey.py -q` on 2026-10-17: five tests passed. It covers U/A/N test tasks, including isolated outbox delivery with a test double. It is not a Postman screenshot or a deployed cross-service integration result. For each remaining task, record task ID, owner, API request/Postman item, actual screenshot or output path, database evidence path where required, and explanation. Caption each screenshot: `Full Student Name — API call title — what it demonstrates.` Capture from the running system; code screenshots and generated outputs are insufficient.

The [live HTTP output](joey-live-http-2026-10-17.txt) records actual execution of `python tests/live_smoke.py`: three processes handled registration, login and automatic welcome notification delivery through HTTP, with a database outbox check. The temporary database was removed after the check. This does not cover Karl/Christophe integrations or replace requested screenshots.

Pending capture checklist: per-endpoint success and rejection screenshots; authentication and authorization comparison; validation errors; database schema and stored records; service integrations; lifecycle and end-to-end path; Postman collection execution; final report embeds. Add links as files are actually captured.

Karl Khouri, 2026-10-18: [pytest output](karl-pytest-2026-10-18.txt) (7 passed) and [live HTTP output](karl-live-http-2026-10-18.txt) from `python tests/live_smoke_karl.py`, which ran six real processes against a temporary database. Covers L/P/R test tasks; not Postman screenshots or database screenshots.

Christophe ElChabab, 2026-10-18: new test suite (31 passed); [full regression output](christophe-full-pytest-2026-10-18.txt) records 43 passed, including all 12 existing teammate tests. The [nine-process live HTTP output](christophe-live-http-2026-10-18.txt) records actual server execution. These are automated checks, not Postman/database screenshots. Capture each required API success/error/permission/lifecycle/search case plus DB schema/records using [Christophe's guide](../christophe-api.md), and caption `Christophe ElChabab — API title — what it demonstrates`. All T/V/I-EVID tasks remain TODO until captured and incorporated into the report.

The same Christophe live-output file includes actual Newman execution of the exported collection: 86 requests, 86 assertions, zero failures. The runner used Node's Windows system CA trust and a temporary database; no credentials or tokens were exported. It remains CLI evidence rather than Postman GUI screenshots.

## Current Christophe ElChabab review results

- [Final full regression output](christophe-reviewed-final-pytest-2026-10-18.txt): 60 passed. Includes all teammate tests plus 17 independent review checks.
- [Final nine-service and collection output](christophe-review-delivery-live-http-2026-10-18.txt): 92 collection items, 96 actual requests including four probes, 214 assertions, zero failures. All newly referenced audit/notification events were actually found.
- [First contract/adversarial failures](christophe-review-round1-2026-10-18.txt), [after first fixes](christophe-review-round2-2026-10-18.txt), [numeric-input findings](christophe-adversarial-before-fix-2026-10-18.txt) and [delivery review tests](christophe-review-delivery-pytest-2026-10-18.txt) record real development checks. Earlier live-check failures are retained and superseded by the final output above.
- The final API prefix is `/api/Christophe-ElChabab`. Historical outputs retain the exact earlier route/name that was actually executed.
- No teammate Postman/database screenshots were committed at the remote head checked (`2cf2a2e`). Their JSON collections and automated logs exist; those artifacts alone do not prove a Postman GUI run.

All screenshot/report evidence tasks remain pending. Caption Christophe's actual future screenshots `Christophe ElChabab — API title — what it demonstrates`.
