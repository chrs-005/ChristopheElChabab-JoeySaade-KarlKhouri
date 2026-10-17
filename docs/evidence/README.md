# Real evidence index

The [Joey pytest output](joey-pytest-2026-10-17.txt) is actual local execution of `python -m pytest tests/test_joey.py -q` on 2026-10-17: five tests passed. It covers U/A/N test tasks, including isolated outbox delivery with a test double. It is not a Postman screenshot or a deployed cross-service integration result. For each remaining task, record task ID, owner, API request/Postman item, actual screenshot or output path, database evidence path where required, and explanation. Caption each screenshot: `Full Student Name — API call title — what it demonstrates.` Capture from the running system; code screenshots and generated outputs are insufficient.

The [live HTTP output](joey-live-http-2026-10-17.txt) records actual execution of `python tests/live_smoke.py`: three processes handled registration, login and automatic welcome notification delivery through HTTP, with a database outbox check. The temporary database was removed after the check. This does not cover Karl/Christophe integrations or replace requested screenshots.

Pending capture checklist: per-endpoint success and rejection screenshots; authentication and authorization comparison; validation errors; database schema and stored records; service integrations; lifecycle and end-to-end path; Postman collection execution; final report embeds. Add links as files are actually captured.
