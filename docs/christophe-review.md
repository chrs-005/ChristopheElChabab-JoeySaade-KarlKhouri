# Christophe ElChabab service review

Latest follow-up, 2026-10-19: the professor's two permission decisions are now implemented and verified: auditor threat search is allowed and incident-list query parameters cannot override authenticated-user scope. Full checks passed **67 tests** and **229 collection assertions over 97 items** against nine real servers. See [pytest](evidence/christophe-professor-permissions-pytest-2026-10-19.txt) and [live HTTP](evidence/christophe-professor-permissions-live-2026-10-19.txt). Older dated check counts and Git status below describe their original review session, not current submission completeness. The separate shared registration-reuse defect and real screenshot/report requirements remain outstanding.

Source: the supplied Sprint I brief, especially Services 3, 4 and 7 plus its authentication, validation, error, documentation and evidence requirements. Scope is Christophe's own services and their integration contracts. This is a technical pass/fail assessment, not the instructor's marking scheme or a prediction of the final grade; no numerical rubric was supplied.

## Teammate evidence status

Remote head checked: `2cf2a2e`. Joey and Karl both have collection JSON, environment templates, generator scripts and actual automated pytest/live HTTP text logs. No committed Postman screenshots, database screenshots, PDF or Word report were found. Their evidence notes say screenshot work is pending. Files in the repository do not establish whether they have run collections in the Postman GUI or have screenshots on their own machines.

## Review and correction history

1. Independent first pass reproduced six targeted failures: requested-name mismatch, malformed multi-dot domains accepted, non-ASCII CVE digits accepted, no automatic delivery attempt after forbidden operations, missing machine-readable bearer/response/error documentation, and collection contract weaknesses. The first fixes made those six checks pass.
2. The second pass exercised all endpoint/role combinations and found four boolean-number cases: `true` was coerced to numeric `1` for CVSS or IDs. All four now return 422. Note-author spoofing, inactive assignees, persisted records and foreign keys were also checked.
3. Stronger collection assertions exposed previously hidden event-delivery failures. A response of HTTP 200 alone was insufficient: the current assignment notice/audit event had not arrived. Bounded polling retained the actual-content assertion and exposed an outbox backlog. The fix coalesces workers in Christophe's package, reuses the HTTP client, skips completed events, drains newly generated audit events and preserves failed events for retry. The assertion was not weakened.
4. Final verification: 60 Python tests passed, including all 12 original teammate tests. The exported collection passed 92 items and 214 assertions against nine actual server processes. Its 96 HTTP requests include four successful pre-request event probes. All temporary test servers stopped afterward.

Actual historical failures are retained in `docs/evidence/`; historical outputs keep the names/routes actually used at that time. Current routes, documentation, collection, environment and report-source defaults use **Christophe ElChabab**, with prefix `/api/Christophe-ElChabab`.

## Exact endpoint contract

Each suffix below is preceded by `/api/Christophe-ElChabab`. There are exactly 18 business operations and no alias endpoints. The independent test compares the complete method/path sets, not just a count.

| Service | Exact required method and suffix |
|---|---|
| Threat Intelligence | POST `/threats` |
| Threat Intelligence | GET `/threats` |
| Threat Intelligence | GET `/threats/{id}` |
| Threat Intelligence | GET `/threats/search` |
| Threat Intelligence | PUT `/threats/{id}` |
| Threat Intelligence | DELETE `/threats/{id}` |
| Vulnerabilities | POST `/vulnerabilities` |
| Vulnerabilities | GET `/vulnerabilities` |
| Vulnerabilities | GET `/vulnerabilities/{id}` |
| Vulnerabilities | PUT `/vulnerabilities/{id}` |
| Vulnerabilities | GET `/vulnerabilities/search` |
| Vulnerabilities | DELETE `/vulnerabilities/{id}` |
| Incidents | POST `/incidents` |
| Incidents | GET `/incidents` |
| Incidents | GET `/incidents/{id}` |
| Incidents | PUT `/incidents/{id}/assign` |
| Incidents | PUT `/incidents/{id}/status` |
| Incidents | POST `/incidents/{id}/notes` |

## Final assessment by requirement

| Requirement | Finding |
|---|---|
| Endpoint methods, suffixes, owner name | Verified by exact contract comparison and actual execution |
| Required fields / input safety | Verified: empty/unknown/null fields, IP/domain/hash syntax, normalized duplicates, ASCII CVE, bounded finite CVSS, boolean numbers, asset/user references |
| Authentication / authorization | Verified: missing/invalid/expired token, live account status, four-role matrix, reporter/assignee boundaries, forged note author and inactive assignee |
| Complete incident lifecycle | Verified: Open → Under Investigation → Mitigated → Resolved → Closed, invalid transitions rejected, notes linked and resolution recorded |
| Complete vulnerability lifecycle | Verified: Open → Under Investigation → In Progress → Resolved → Closed, invalid transitions and dates rejected |
| Database persistence / relationships | Verified: actual stored records, FK restrictions, integrity checks; schema scripts included |
| API-to-API integration | Verified: actual notification and audit records for this run, peer report reconciliation, all nine services running |
| Error / API documentation | Verified: bearer security, typed responses, descriptive operations and standard 401/403/404/409/422 error schemas; guide and collection included |
| Postman collection | Verified by actual Newman execution: 92 items, 214 assertions; no fabricated saved responses |
| Real Postman/database screenshots | Pending; CLI results are not a substitute |
| Named common report / explanations / diagrams | Pending team submission work; existing technical guides are not claimed as the final report |
| Own-account Git contributions and history screenshots | Christophe's current changes are local, uncommitted and unpushed; final evidence pending |
| CREATES meeting / applied feedback | Team requirement remains pending; not inferred from implementation |

## Instructor clarification supplied on 2026-10-19

- The professor confirmed auditor access to `GET /threats/search`; its omission from Service 4's authorization list was an oversight. The search permission now includes Administrator, Analyst and Auditor, without allowing auditor mutations.
- The professor confirmed `GET /incidents` for all four roles: all records for Administrator/Auditor, assigned-only for Analyst, submitted-only for Employee. The authenticated user's live identity controls the SQL predicate; supplied query parameters cannot change it. Additional tests exercise two different analysts/reporters and forged identity/role parameters.

These two questions are resolved using the professor's answer supplied by Christophe, not a guessed grader preference. Exactly 18 required operations remain; no teammate-service permissions were changed. Screenshot/report work and the separately documented shared registration-reuse defect remain outside this clarification.

## Reproduce

```text
python -m pytest tests -q
python tests/live_smoke_christophe.py --postman
```

Use the repository's ignored virtual environment and README setup. Newman needs Node.js/npm only for the optional collection check. On this machine Node used the existing Windows system CA trust; certificate verification stayed enabled. Pinned dependencies emit deprecation warnings; final tests have no failures.

Final actual outputs: [pytest](evidence/christophe-reviewed-final-pytest-2026-10-18.txt), [live servers and Newman](evidence/christophe-review-delivery-live-http-2026-10-18.txt). Capture the real screenshot evidence, review/adapt the implementation, complete named report sections, and commit/push under the student's own account before treating the academic submission as complete.
