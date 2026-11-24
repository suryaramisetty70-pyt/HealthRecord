# HealthRecord
Academic prototype. Use fictional data only. Python 3.10+.

Run `pip install -r requirements.txt` then `uvicorn app:app --host 127.0.0.1 --port 8000` and open http://127.0.0.1:8000.
SQLite persists in health.db (or DATABASE_PATH). Set SECURE_COOKIE=1 behind HTTPS. Do not deploy for real patient data: encryption at rest, clinical validation, doctor consent workflow, rate limiting, backups and production security review remain necessary. ML is a synthetic classification benchmark, not a medical risk model. No OCR or wearable integration.

Reviewer access: register two accounts, grant access by email, view shared records from reviewer account, revoke from patient account. Reviewer identity is not verified. Dockerfile requires HTTPS and persistent /data volume. No clinical validation or production encryption.
