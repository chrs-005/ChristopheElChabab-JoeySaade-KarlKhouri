# Joey Saade: detailed Postman and database screenshots

The report now has **32 individual image slots**: 27 Postman requests and 5 database views. Each file loads automatically after you save it under `report/joey-screenshots/` and compile `report/main.tex`. The existing whole-folder Runner images remain supplementary evidence; do not delete them.

## 1. Open the completed Postman run

In Postman, open the Joey collection, choose **Runs**, and open the successful run. Click one request row to inspect its executed request, response, status, and test results. Postman can show response headers and body from a run when **Persist responses for a session** was enabled. If an old run lacks the response body, rerun the ordered collection with that setting enabled on a fresh demo database; do not resend isolated create/delete requests against the cleaned database. See [Postman's Collection Runner instructions](https://learning.postman.com/docs/tests-and-scripts/running-collections/intro-to-collection-runs).

The collection uses literal service URLs (`http://127.0.0.1:8001`, `:8002`, and `:8003`). It still uses runtime values for credentials, bearer token, and IDs returned by earlier requests. In the run results, open the **executed request details** to show the resolved URL and sent body. A request tab may show the editable template with `{{userId}}`; do not use that template view as the sole detailed screenshot. Never expose a password, bearer token, service key, or password hash.

For each row below, capture the individual request details and actual response with the method, owner-prefixed URL, status, and passing test visible. Use **Win+Shift+S**, then save the PNG to the exact relative path. The first digit is the section; the second is the request position.

| Section | Request | Save under `report/joey-screenshots/` |
|---|---|---|
| 1 Users | Register employee | `01-Users/11-Register-employee.png` |
| 1 Users | Login | `01-Users/12-Login.png` |
| 1 Users | Update profile | `01-Users/13-Update-profile.png` |
| 1 Users | List users | `01-Users/14-List-users.png` |
| 1 Users | Get user by username | `01-Users/15-Get-user-by-username.png` |
| 1 Users | Admin role/status update | `01-Users/16-Admin-role-status-update.png` |
| 2 Assets | Create asset | `02-Assets/21-Create-asset.png` |
| 2 Assets | Update asset | `02-Assets/22-Update-asset.png` |
| 2 Assets | List assets | `02-Assets/23-List-assets.png` |
| 2 Assets | Get asset | `02-Assets/24-Get-asset.png` |
| 2 Assets | Search assets | `02-Assets/25-Search-assets.png` |
| 2 Assets | Asset history | `02-Assets/26-Asset-history.png` |
| 3 Notifications | Create notification as service | `03-Notifications/31-Create-notification-as-service.png` |
| 3 Notifications | List user notifications | `03-Notifications/32-List-user-notifications.png` |
| 3 Notifications | Get notification | `03-Notifications/33-Get-notification.png` |
| 3 Notifications | Mark notification read | `03-Notifications/34-Mark-notification-read.png` |
| 3 Notifications | Search notifications | `03-Notifications/35-Search-notifications.png` |
| 4 Negative | Reject invalid registration email | `04-Negative/41-Reject-invalid-registration-email.png` |
| 4 Negative | Reject privileged public registration | `04-Negative/42-Reject-privileged-public-registration.png` |
| 4 Negative | Reject unauthenticated users listing | `04-Negative/43-Reject-unauthenticated-users-listing.png` |
| 4 Negative | Reject invalid asset IP | `04-Negative/44-Reject-invalid-asset-IP.png` |
| 4 Negative | Reject missing asset | `04-Negative/45-Reject-missing-asset.png` |
| 4 Negative | Reject notification without auth | `04-Negative/46-Reject-notification-without-auth.png` |
| 5 Database | Users | `05-Database/51-Users-Database.png` |
| 5 Database | Assets | `05-Database/52-Assets-Database.png` |
| 5 Database | Notifications | `05-Database/53-Notifications-Database.png` |
| 5 Database | Outbox and user IDs | `05-Database/54-Outbox-and-User-IDs-Database.png` |
| 6 Cleanup | Delete asset | `06-Cleanup/61-Delete-asset.png` |
| 6 Cleanup | Delete created notification | `06-Cleanup/62-Delete-created-notification.png` |
| 6 Cleanup | Delete welcome notification | `06-Cleanup/63-Delete-welcome-notification.png` |
| 6 Cleanup | Delete user | `06-Cleanup/64-Delete-user.png` |
| 5 Database after Cleanup | Retained history and IDs | `05-Database/55-After-Cleanup-Database.png` |

## 2. Database screenshots

The existing whole-category database captures are at the old filenames. If they show the intended real results, **copy** each to its new numbered name above; keep the originals. The old after-Cleanup capture is in `06-Cleanup/After-Cleanup-Database.png`, so copy it to `05-Database/55-After-Cleanup-Database.png`. Do not label a screenshot as populated if it only shows the cleaned database.

For new captures, open Command Prompt in the repo and run:

```cmd
cd /d "C:\Main\School\CSE FALL 4\EECE 435L\Labs\Sprint1\repo"
"C:\Android\platform-tools\sqlite3.exe" "joey-evidence.db"
```

At `sqlite>`, type `.headers on` and `.mode column`. Capture these commands and their real output, with the relevant schema and rows visible:

- **51 Users:** `.schema users` then `SELECT id, username, role, status FROM users ORDER BY id;`
- **52 Assets:** `.schema assets`, `.schema asset_history`, then `SELECT id, name, owner_id, status FROM assets;` and `SELECT original_asset_id, action FROM asset_history ORDER BY id;`
- **53 Notifications:** `.schema notifications` then `SELECT id, user_id, title, type, status, event_id FROM notifications ORDER BY id;`
- **54 Outbox and IDs:** `.schema outbox`, `.schema user_id_allocations`, then `SELECT id, destination, event_id, attempts, delivered_at FROM outbox ORDER BY id DESC LIMIT 10;` and `SELECT id FROM user_id_allocations ORDER BY id;`
- **55 After Cleanup:** `SELECT id, username FROM users ORDER BY id;`, `SELECT id, name FROM assets ORDER BY id;`, `SELECT original_asset_id, action FROM asset_history ORDER BY id;`, and `SELECT id FROM user_id_allocations ORDER BY id;`

If Cleanup has already run, your persistent DB will no longer have the sample rows. Use the genuine earlier captures for 51-54, or perform a new ordered demo run before Cleanup. Do not fabricate rows.

## 3. Compile and check

From `report/`, run `xelatex main.tex` twice. Open `main.pdf` and check that all 32 named images load and their captions match. Missing filenames show pending boxes. Keep `.env`, databases, passwords, bearer tokens, and service keys out of the report and Git.
