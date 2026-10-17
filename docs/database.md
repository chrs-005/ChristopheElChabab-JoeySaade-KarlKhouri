# Database plan

Joey's initial SQLite schema is [schema.sql](../joey/schema.sql). It defines Users, Assets, Asset History, Notifications and Outbox. It has primary keys; foreign keys from assets to owner and notifications to recipient; unique username/email and event ID; and role/status/type/severity checks. Referenced users cannot be deleted. Asset history survives asset deletion by retaining `original_asset_id`. If Karl's incident/vulnerability tables use asset FKs with RESTRICT, deletion will return 409.

The remaining brief entities are not implemented: Incidents, Investigation Notes, Threats, Logs, Vulnerabilities, Playbooks and Response Actions. Their owners must provide their own migrations and decide if SQLite remains the team database.

Each owner documents their tables and relationships and captures real structure and record evidence. Karl leads the relationship diagram and migration integration guide after topology is agreed. Joey's tests create temporary records; no submitted database screenshots exist yet.
