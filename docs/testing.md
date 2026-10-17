# Testing and Postman plan

No application or Postman collection exists yet. Each owner adds their six required endpoints with descriptions, variables, assertions, and a credential-free environment template. Test successful calls, missing/invalid fields, duplicate and missing records, missing/invalid/expired authentication, allowed/forbidden roles, cross-user access, state transitions, persistence, and integrations. Label contract tests using doubles as isolated tests.

End-to-end path after services run: authenticate; create/select an asset; report incident; assign analyst; check assignment notification; progress valid incident states; add notes; check audit events; exercise response actions; generate reports and reconcile statistics against records. Record actual commands, results and screenshots in [evidence](evidence/README.md).
