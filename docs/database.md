# Database plan

Schema and topology are pending. Minimum entities from the brief: Users; Assets (owner → User); Incidents (reporter and assigned analyst → User, affected Asset); Investigation Notes (Incident, Analyst); Threats; Logs (actor User, with durable historical actor label for deleted users); Vulnerabilities (affected Asset); Notifications (recipient User); Playbooks (creator User); Response Actions (Playbook, assigned User). Owner-written migrations must define PKs, FKs or documented cross-service reference checks, unique indexes, enums/checks, and deletion behavior.

Each owner documents their tables and relationships and captures real structure and record evidence. Karl leads the relationship diagram and migration integration guide after topology is agreed. Do not claim schema or sample data exists yet.
