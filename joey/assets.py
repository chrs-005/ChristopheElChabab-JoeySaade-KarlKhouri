import ipaddress
import json
import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from pydantic import BaseModel, ConfigDict, Field

from .common import PREFIX, api_error_handler, current_user, db, error, init_db, now, queue_audit, require_role, row_dict, service_secret, token_secret

ASSET_TYPES = ("Server", "Workstation", "Database", "Application", "Network Device", "Cloud Resource")
CRITICALITY = ("Low", "Medium", "High", "Critical")
STATUSES = ("Active", "Inactive", "Under Maintenance")


@asynccontextmanager
async def lifespan(_: FastAPI):
    token_secret(); service_secret(); init_db()
    yield


app = FastAPI(title="Joey Saade — Asset Management", lifespan=lifespan)
api_error_handler(app)


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    type: str
    ip_address: str
    operating_system: str | None = None
    department: str = Field(min_length=1, max_length=100)
    owner_id: int
    location: str = Field(min_length=1, max_length=200)
    criticality: str
    status: str = "Active"


class AssetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: str | None = None
    ip_address: str | None = None
    operating_system: str | None = None
    department: str | None = Field(default=None, min_length=1, max_length=100)
    owner_id: int | None = None
    location: str | None = Field(default=None, min_length=1, max_length=200)
    criticality: str | None = None
    status: str | None = None


def validate(fields, conn):
    if "type" in fields and fields["type"] not in ASSET_TYPES:
        error(422, "Invalid asset type")
    if "criticality" in fields and fields["criticality"] not in CRITICALITY:
        error(422, "Invalid criticality")
    if "status" in fields and fields["status"] not in STATUSES:
        error(422, "Invalid asset status")
    if "ip_address" in fields:
        try:
            ipaddress.ip_address(fields["ip_address"])
        except ValueError:
            error(422, "Invalid IP address")
    if "owner_id" in fields and not conn.execute("SELECT 1 FROM users WHERE id=?", (fields["owner_id"],)).fetchone():
        error(422, "Owner does not exist")


def history(conn, asset_id, actor_id, action, before, after):
    conn.execute("INSERT INTO asset_history(asset_id,original_asset_id,changed_by,changed_at,before_json,after_json,action) VALUES(?,?,?,?,?,?,?)", (asset_id, asset_id, actor_id, now(), json.dumps(before), json.dumps(after), action))


@app.post(f"{PREFIX}/assets", status_code=201)
def create_asset(data: AssetCreate, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    fields = data.model_dump()
    with db() as conn:
        validate(fields, conn)
        stamp = now()
        cur = conn.execute("INSERT INTO assets(name,type,ip_address,operating_system,department,owner_id,location,criticality,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (*fields.values(), stamp, stamp))
        asset = row_dict(conn.execute("SELECT * FROM assets WHERE id=?", (cur.lastrowid,)).fetchone())
        history(conn, cur.lastrowid, actor["id"], "create", None, asset)
        queue_audit(conn, "asset_created", actor["id"], actor["username"], related_service="assets", subject_id=cur.lastrowid)
        return asset


@app.get(f"{PREFIX}/assets/search")
def search_assets(name: str | None = None, type: str | None = None, ip_address: str | None = None, department: str | None = None, criticality: str | None = None, actor=Depends(current_user)):
    require_role(actor, "Security Administrator", "Security Analyst", "Security Auditor")
    filters = {k: v for k, v in {"name": name, "type": type, "ip_address": ip_address, "department": department, "criticality": criticality}.items() if v is not None}
    query = "SELECT * FROM assets"
    args = []
    if filters:
        query += " WHERE " + " AND ".join(("name LIKE ?" if k == "name" else f"{k}=?") for k in filters)
        args = [f"%{v}%" if k == "name" else v for k, v in filters.items()]
    with db() as conn:
        return [row_dict(x) for x in conn.execute(query + " ORDER BY id", args)]


@app.get(f"{PREFIX}/assets")
def list_assets(actor=Depends(current_user)):
    require_role(actor, "Security Administrator", "Security Auditor")
    with db() as conn:
        return [row_dict(x) for x in conn.execute("SELECT * FROM assets ORDER BY id")]


@app.get(f"{PREFIX}/assets/{{id}}")
def get_asset(id: int, actor=Depends(current_user)):
    require_role(actor, "Security Administrator", "Security Analyst", "Security Auditor")
    with db() as conn:
        asset = conn.execute("SELECT * FROM assets WHERE id=?", (id,)).fetchone()
    if not asset:
        error(404, "Asset not found")
    return row_dict(asset)


@app.get(f"{PREFIX}/assets/{{id}}/history")
def get_history(id: int, actor=Depends(current_user)):
    require_role(actor, "Security Administrator", "Security Auditor")
    with db() as conn:
        return [row_dict(x) for x in conn.execute("SELECT * FROM asset_history WHERE original_asset_id=? ORDER BY id", (id,))]


@app.put(f"{PREFIX}/assets/{{id}}")
def update_asset(id: int, data: AssetUpdate, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    fields = data.model_dump(exclude_unset=True)
    if not fields or any(v is None for k, v in fields.items() if k != "operating_system"):
        error(422, "Provide non-null asset fields")
    with db() as conn:
        before = conn.execute("SELECT * FROM assets WHERE id=?", (id,)).fetchone()
        if not before:
            error(404, "Asset not found")
        validate(fields, conn)
        conn.execute("UPDATE assets SET " + ", ".join(f"{k}=?" for k in fields) + ", updated_at=? WHERE id=?", (*fields.values(), now(), id))
        after = row_dict(conn.execute("SELECT * FROM assets WHERE id=?", (id,)).fetchone())
        history(conn, id, actor["id"], "update", row_dict(before), after)
        queue_audit(conn, "asset_updated", actor["id"], actor["username"], related_service="assets", subject_id=id)
        return after


@app.delete(f"{PREFIX}/assets/{{id}}")
def delete_asset(id: int, actor=Depends(current_user)):
    require_role(actor, "Security Administrator")
    with db() as conn:
        before = conn.execute("SELECT * FROM assets WHERE id=?", (id,)).fetchone()
        if not before:
            error(404, "Asset not found")
        history(conn, id, actor["id"], "delete", row_dict(before), None)
        try:
            conn.execute("DELETE FROM assets WHERE id=?", (id,))
        except sqlite3.IntegrityError:
            error(409, "Asset is referenced by another service")
        queue_audit(conn, "asset_deleted", actor["id"], actor["username"], related_service="assets", subject_id=id)
    return {"message": "Asset deleted"}
