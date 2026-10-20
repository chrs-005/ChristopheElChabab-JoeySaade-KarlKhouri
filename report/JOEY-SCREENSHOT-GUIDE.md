# Joey Saade: one screenshot per evidence category

The report has **ten** named PNG slots in `joey-evidence.tex`: five Postman folder runs, four populated database views, and one database view after Cleanup. Save each screenshot under `report/joey-screenshots/` with the exact path below. A missing file shows a pending box; the matching real PNG loads when the report is compiled again. The three individual Users PNGs already saved in `01-Users/` are preserved as supplementary captures; the report's new Users slot expects a folder-run image.

## Step 1: keep the demo running

Use the private `.env` in the repository root with `DATABASE_PATH=joey-evidence.db`, completed `BOOTSTRAP_ADMIN_*` fields and distinct secrets. The administrator should already have been created once. Keep the Users, Assets and Notifications services running on ports 8001, 8002 and 8003. Do not use `tests/postman_joey.py` for screenshots; it uses a disposable database.

## Step 2: run one Postman folder at a time

Select **Joey local template** in Postman. Run one folder with the Collection Runner, **one iteration**, and turn on **Keep variable values** so `token`, `userId`, `assetId` and notification IDs remain available to the next folder. Postman documents folder runs and this option in its [Collection Runner guide](https://learning.postman.com/docs/tests-and-scripts/running-collections/intro-to-collection-runs). After each run, make sure every listed request has the expected status and a green PASS result. Capture the full run-results list, like the Users image you showed. If the list does not fit, maximize Postman or zoom out until every request is readable.

Run and save in this order. Paths are relative to `report/joey-screenshots/`:

| Order | Run this folder | Requests shown | Save the one PNG as |
|---:|---|---:|---|
| 1 | Users and Identity -- Joey Saade | 6 | `01-Users/Users-and-Identity-Runner.png` |
| 2 | Asset Management -- Joey Saade | 6 | `02-Assets/Asset-Management-Runner.png` |
| 3 | Notification and Alert Management -- Joey Saade | 5 | `03-Notifications/Notification-Management-Runner.png` |
| 4 | Negative checks -- Joey Saade | 6 | `04-Negative/Negative-Checks-Runner.png` |

**Save the Users screenshot you just showed** as `report/joey-screenshots/01-Users/Users-and-Identity-Runner.png`; it contains all six Users results. Do not rename or delete your three earlier individual PNGs.

Check the selected environment after the Users run: `token` and `userId` should be filled. After Assets, `assetId` should be filled. After Notifications, `notificationId` and `welcomeNotificationId` should be filled. If a value is blank, rerun that folder with **Keep variable values** enabled before continuing. The Notifications list should include the automatic Welcome and service-created Assigned records. If Welcome is absent, run `python -m joey.outbox` in a repository terminal, then rerun the Notifications folder.

**Stop before Cleanup.** The sample database rows must still exist for Step 3.

To save a screenshot on Windows, press **Win+Shift+S**, select the entire run-results list, open the Snipping Tool thumbnail, press **Ctrl+S**, choose PNG and enter the exact path. Keep the folder name, method, owner-prefixed URLs, response codes and green assertions visible. The Runner list does not need to expose passwords or bearer tokens.

## Step 3: take four populated database screenshots

In Command Prompt at the repository root, open the persistent database:

```cmd
C:\Android\platform-tools\sqlite3.exe joey-evidence.db
```

At the `sqlite>` prompt enter:

```text
.headers on
.mode column
```

For each category, run the commands below, then capture the **real command output together in one image**. Maximize the terminal or reduce its font size if needed. The sample user, asset and notifications must still be present. Do not display `password_hash` or private credentials.

**Users database** -- save as `05-Database/Users-Database.png`:

```sql
.schema users
SELECT id, username, role, status FROM users ORDER BY id;
```

**Assets database** -- save as `05-Database/Assets-Database.png`:

```sql
.schema assets
.schema asset_history
SELECT id, name, owner_id, status FROM assets;
SELECT original_asset_id, action FROM asset_history ORDER BY id;
```

**Notifications database** -- save as `05-Database/Notifications-Database.png`:

```sql
.schema notifications
SELECT id, user_id, title, type, status, event_id FROM notifications ORDER BY id;
```

**Outbox and issued IDs database** -- save as `05-Database/Outbox-and-User-IDs-Database.png`:

```sql
.schema outbox
.schema user_id_allocations
SELECT id, destination, event_id, attempts, delivered_at FROM outbox ORDER BY id DESC LIMIT 10;
SELECT id FROM user_id_allocations ORDER BY id;
```

If a category's output is too tall for one readable screenshot, capture the key schema and rows at a smaller terminal font. Keep extra screenshots as supplementary evidence if needed; the report uses the single named category image.

## Step 4: run Cleanup and capture its folder result

Back in Postman, run **Cleanup -- Joey Saade** as one folder with one iteration and **Keep variable values** on. It should show four HTTP 200 results in order: delete asset, created notification, Welcome notification, then user. Save the full Runner list as:

`report/joey-screenshots/06-Cleanup/Cleanup-Runner.png`

Return to SQLite and run the four checks below. Save their combined output as `report/joey-screenshots/05-Database/After-Cleanup-Database.png`:

```sql
SELECT id, username FROM users ORDER BY id;
SELECT id, name FROM assets ORDER BY id;
SELECT original_asset_id, action FROM asset_history ORDER BY id;
SELECT id FROM user_id_allocations ORDER BY id;
```

The sample user and asset should be gone; asset history and issued IDs should remain. Type `.quit` to leave SQLite.

## Step 5: check the report

Compile `report/main.tex` again. From the `report/` folder, use `tectonic main.tex` if available or `xelatex main.tex` twice; Overleaf can also compile the report source and uploaded image folders. Each exact PNG replaces its pending box on the next PDF build. Keep `.env`, the SQLite database, passwords, bearer tokens and service keys out of the report and Git.
