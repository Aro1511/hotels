from firebase_db import db
from datetime import datetime

def create_tenant(tenant_id: str):
    db.collection("tenants").document(tenant_id).set({
        "active": True,
        "created_at": datetime.utcnow()
    })

def deactivate_tenant(tenant_id: str):
    db.collection("tenants").document(tenant_id).update({"active": False})

def delete_tenant(tenant_id: str):
    db.collection("tenants").document(tenant_id).delete()

def list_tenants():
    tenants_ref = db.collection("tenants").stream()
    tenants = []
    for doc in tenants_ref:
        t = doc.to_dict()
        t["id"] = doc.id
        tenants.append(t)
    return tenants

def is_tenant_active(tenant_id: str) -> bool:
    doc = db.collection("tenants").document(tenant_id).get()
    if not doc.exists:
        return False
    return doc.to_dict().get("active", True)
