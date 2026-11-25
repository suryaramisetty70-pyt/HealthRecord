import os
import tempfile
import unittest

tmp = tempfile.TemporaryDirectory()
os.environ["DATABASE_PATH"] = os.path.join(tmp.name, "test.db")
os.environ["SECURE_COOKIE"] = "0"
from fastapi.testclient import TestClient
from app import app

class HealthRecordTests(unittest.TestCase):
    def test_workflows(self):
        p, r, stranger = (TestClient(app) for _ in range(3))
        for client, name in [(p,"patient"),(r,"reviewer"),(stranger,"stranger")]:
            data = {"email":name+"@example.com","password":"fictional-test-123","name":name}
            self.assertEqual(client.post("/api/register",json=data).status_code,200)
            self.assertEqual(client.post("/api/login",json=data).status_code,200)
        bad = p.post("/api/register",json={"email":"x@example.com","password":"secret","name":"x"})
        self.assertEqual(bad.status_code,422)
        self.assertNotIn("secret",bad.text)
        record = {"kind":"Medication","title":"Example","day":"2026-11-25","notes":"Synthetic only"}
        for patch in [{"title":"   "},{"day":"2026-02-31"}]:
            self.assertEqual(p.post("/api/records",json={**record,**patch}).status_code,422)
        self.assertEqual(p.post("/api/records",json=record).status_code,200)
        item = p.get("/api/dashboard").json()["records"][0]
        self.assertEqual(stranger.delete("/api/records/"+str(item["id"])).status_code,404)
        self.assertEqual(p.post("/api/share",json={"email":"reviewer@example.com"}).status_code,200)
        patient = r.get("/api/sharing").json()["incoming"][0]["id"]
        recipient = p.get("/api/sharing").json()["outgoing"][0]["id"]
        self.assertEqual(r.get(f"/api/shared/{patient}").status_code,200)
        self.assertEqual(stranger.get(f"/api/shared/{patient}").status_code,404)
        self.assertEqual(r.delete("/api/records/"+str(item["id"])).status_code,404)
        self.assertEqual(p.post(f"/api/revoke/{recipient}").status_code,200)
        self.assertEqual(r.get(f"/api/shared/{patient}").status_code,404)
        self.assertTrue(p.get("/api/report").content.startswith(b"%PDF"))
        self.assertEqual(p.post("/api/logout").status_code,200)
        self.assertEqual(p.get("/api/dashboard").status_code,401)

if __name__ == "__main__":
    unittest.main()
