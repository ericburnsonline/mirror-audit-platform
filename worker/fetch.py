import hashlib
import requests
from coordinator.db import get_connection
from dotenv import load_dotenv

load_dotenv()

AUTHORITATIVE_BASE = "https://mirrors.slackware.com/slackware/"
TARGET_PATH = "slackware64-15.0/CHECKSUMS.md5"
TIMEOUT = 15


def fetch_content(url: str) -> dict:
    """Fetch a URL and return status, size, and content hash."""
    result = {
        "url": url,
        "reachable": False,
        "status_code": None,
        "content_length": None,
        "content_hash": None,
        "error": None,
    }

    try:
        response = requests.get(url, timeout=TIMEOUT)
        result["status_code"] = response.status_code
        result["reachable"] = response.status_code == 200

        if result["reachable"]:
            content = response.content
            result["content_length"] = len(content)
            result["content_hash"] = hashlib.md5(content).hexdigest()

    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "connection_error"
    except Exception as e:
        result["error"] = str(e)

    return result


def audit_mirrors(authoritative_hash: str, mirrors: list) -> dict:
    """Fetch CHECKSUMS.md5 from each mirror and compare to authoritative hash."""
    results = {
        "match": [],
        "mismatch": [],
        "not_found": [],
        "unreachable": [],
    }

    total = len(mirrors)
    for i, (mirror_id, mirror_url) in enumerate(mirrors, 1):
        url = mirror_url.rstrip("/") + "/" + TARGET_PATH
        print(f"[{i}/{total}] Checking {url}")

        result = fetch_content(url)

        if result["status_code"] == 404:
            print(f"  NOT FOUND (404)")
            results["not_found"].append({"id": mirror_id, "url": url})
        elif not result["reachable"]:
            print(f"  UNREACHABLE: {result['error'] or result['status_code']}")
            results["unreachable"].append({
                "id": mirror_id,
                "url": url,
                "error": result["error"] or f"http_{result['status_code']}"
            })
        elif result["content_hash"] == authoritative_hash:
            print(f"  OK")
            results["match"].append({"id": mirror_id, "url": url})
        else:
            print(f"  MISMATCH: {result['content_hash']}")
            results["mismatch"].append({
                "id": mirror_id,
                "url": url,
                "hash": result["content_hash"]
            })

    return results

def get_authoritative_hash() -> str | None:
    """Fetch CHECKSUMS.md5 from the authoritative source and return its hash."""
    url = AUTHORITATIVE_BASE + TARGET_PATH
    print(f"Fetching authoritative source: {url}")
    result = fetch_content(url)

    if not result["reachable"]:
        print(f"ERROR: Could not reach authoritative source: {result['error']}")
        return None

    print(f"Authoritative hash: {result['content_hash']}")
    return result["content_hash"]


def get_mirrors(protocol="https") -> list:
    """Get active mirrors from the database."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, url FROM mirrors
        WHERE active = TRUE AND protocol = %s
        ORDER BY country_code, url
    """, (protocol,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows




def run_audit():
    authoritative_hash = get_authoritative_hash()
    if not authoritative_hash:
        print("Aborting audit.")
        return

    print(f"\nFetching https mirrors from database...")
    mirrors = get_mirrors(protocol="https")
    print(f"Found {len(mirrors)} mirrors\n")

    results = audit_mirrors(authoritative_hash, mirrors)

    print(f"\n--- Audit Results ---")
    print(f"Match:       {len(results['match'])}")
    print(f"Mismatch:    {len(results['mismatch'])}")
    print(f"Not Found:   {len(results['not_found'])}")
    print(f"Unreachable: {len(results['unreachable'])}")

    if results["mismatch"]:
        print(f"\nMISMATCHED MIRRORS:")
        for m in results["mismatch"]:
            print(f"  {m['url']} -> {m['hash']}")

    if results["not_found"]:
        print(f"\nNOT FOUND (404) MIRRORS:")
        for m in results["not_found"]:
            print(f"  {m['url']}")

    if results["unreachable"]:
        print(f"\nUNREACHABLE MIRRORS:")
        for m in results["unreachable"]:
            print(f"  {m['url']} -> {m['error']}")

if __name__ == "__main__":
    run_audit()