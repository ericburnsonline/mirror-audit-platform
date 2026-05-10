from fastapi import FastAPI
import psycopg2
import redis
import os

app = FastAPI(title="Mirror Audit Coordinator")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mirror_audit")
DB_USER = os.getenv("DB_USER", "map_user")
DB_PASS = os.getenv("DB_PASS", "map_password")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")


@app.get("/")
def root():
    return {"status": "ok", "service": "mirror-audit-coordinator"}


@app.get("/health")
def health():
    results = {}

    # Check Postgres
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            dbname=DB_NAME, user=DB_USER, password=DB_PASS
        )
        conn.close()
        results["postgres"] = "ok"
    except Exception as e:
        results["postgres"] = f"error: {e}"

    # Check Redis
    try:
        r = redis.Redis(host=REDIS_HOST, port=int(REDIS_PORT))
        r.ping()
        results["redis"] = "ok"
    except Exception as e:
        results["redis"] = f"error: {e}"

    return results