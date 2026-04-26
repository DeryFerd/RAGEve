import sys
from pathlib import Path
_project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_project_root))

from test.api.base import APITestBase
from backend.models_peewee import Dialog, get_database

class TestDebug(APITestBase):
    @classmethod
    def setup_class(cls):
        super().setup_class()
        print(f"[Class Setup] tenant_id={cls.test_tenant_id}")

    def test_create(self):
        payload = {
            "tenant_id": self.test_tenant_id,
            "name": "Test Dialog",
            "llm_id": "llama3.2:latest",
            "kb_ids": [],
        }
        resp = self.client.post("/dialogs/", json=payload)
        print(f"Create response: {resp.status_code}")
        self.dialog_id = resp.json()["id"]
        print(f"Created dialog ID: {self.dialog_id}")
        
        # Check DB directly
        db = get_database()
        with db.connection_context():
            count = Dialog.select().where(Dialog.tenant_id == self.test_tenant_id).count()
            print(f"Direct DB count after create: {count}")

    def test_list(self):
        print(f"test_list self has dialog_id? {hasattr(self, 'dialog_id')}")
        if hasattr(self, 'dialog_id'):
            print(f"  dialog_id = {self.dialog_id}")
        else:
            print("  No dialog_id attribute")
        
        # Check DB directly before API call
        db = get_database()
        with db.connection_context():
            count = Dialog.select().where(Dialog.tenant_id == self.test_tenant_id).count()
            print(f"Direct DB count before list: {count}")
            rows = list(Dialog.select().where(Dialog.tenant_id == self.test_tenant_id))
            print(f"  Rows: {[(r.id, r.name) for r in rows]}")
        
        resp = self.client.get("/dialogs/", params={"tenant_id": self.test_tenant_id})
        print(f"List response: {resp.status_code}")
        print(f"Response JSON: {resp.json()}")

# Run as a suite
import pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
