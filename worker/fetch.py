import hashlib
import re
import requests
from pathlib import Path
from datetime import datetime
from coordinator.db import get_connection
from dotenv import load_dotenv

load_dotenv()

AUTHORITATIVE_BASE = "https://mirrors.slackware.com/slackware/"
TARGET_PATH = "slackware64-15.0/CHECKSUMS.md5"
TIMEOUT = 15


def fetch_content(url: str) -> dict:
    """Fetch a URL and return status, size, content, and hash."""
    result = {
        "url": url,
        "reachable": False,
        "status_code": None,
        "content_length": None,
        "content_hash": None,
        "content": None,
        "error": None,
        "invalid_content": False,
    }

    try:
        response = requests.get(url, timeout=TIMEOUT)
        result["status_code"] = response.status_code
        result["reachable"] = response.status_code == 200

        if result["reachable"]:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" in content_type:
                result["reachable"] = False
                result["invalid_content"] = True
                result["error"] = "unexpected html response"
                return result

            content = response.content
            result["content_length"] = len(content)
            result["content_hash"] = hashlib.md5(content).hexdigest()
            result["content"] = response.text

            # Validate it looks like a checksums file
            if "MD5 message digest" not in result["content"] and \
               not any(len(line) > 34 and line[:32].isalnum()
                       for line in result["content"].splitlines()):
                result["reachable"] = False
                result["invalid_content"] = True
                result["error"] = "response does not appear to be a checksums file"

    except requests.exceptions.Timeout:
        result["error"] = "timeout"
    except requests.exceptions.ConnectionError:
        result["error"] = "connection_error"
    except Exception as e:
        result["error"] = str(e)

    return result


def parse_checksums(content: str) -> dict:
    """Parse CHECKSUMS.md5 content into a dict of filename -> md5hash."""
    checksums = {}
    for line in content.splitlines():
        line = line.strip()
        if len(line) < 35:
            continue
        hash_part = line[:32]
        rest = line[32:].strip()
        if not rest or not all(c in '0123456789abcdef' for c in hash_part.lower()):
            continue
        checksums[rest] = hash_part.lower()
    return checksums


def save_checksums_locally(url: str, content: str, base_dir: str = "data/checksums"):
    """Save raw CHECKSUMS.md5 content to local storage for later analysis."""
    date_str = datetime.now().strftime("%Y%m%d")

    safe_name = re.sub(r'[^\w\-.]', '_', url.replace("https://", "").replace("http://", ""))
    safe_name = re.sub(r'_+', '_', safe_name).strip('_')

    out_dir = Path(base_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{safe_name}_{date_str}.txt"
    out_path = out_dir / filename
    out_path.write_text(content, encoding="utf-8")

    return out_path


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


def audit_mirrors(authoritative_checksums: dict, authoritative_content: str, mirrors: list) -> dict:
    """
    Fetch CHECKSUMS.md5 from each mirror and compare individual file
    checksums against the authoritative source.
    """
    save_checksums_locally(
        AUTHORITATIVE_BASE + TARGET_PATH,
        authoritative_content,
        base_dir="data/checksums/authoritative"
    )

    results = {
        "match": [],
        "mismatch": [],
        "not_found": [],
        "unreachable": [],
        "invalid": [],
    }

    total = len(mirrors)
    for i, (mirror_id, mirror_url) in enumerate(mirrors, 1):
        url = mirror_url.rstrip("/") + "/" + TARGET_PATH
        print(f"[{i}/{total}] Checking {url}")

        result = fetch_content(url)

        if result["invalid_content"]:
            print(f"  INVALID RESPONSE: {result['error']}")
            results["invalid"].append({
                "id": mirror_id,
                "url": url,
                "error": result["error"]
            })

        elif result["status_code"] == 404:
            print(f"  NOT FOUND (404)")
            results["not_found"].append({"id": mirror_id, "url": url})

        elif not result["reachable"]:
            print(f"  UNREACHABLE: {result['error'] or result['status_code']}")
            results["unreachable"].append({
                "id": mirror_id,
                "url": url,
                "error": result["error"] or f"http_{result['status_code']}"
            })

        else:
            save_checksums_locally(
                url,
                result["content"],
                base_dir="data/checksums/mirrors"
            )

            mirror_checksums = parse_checksums(result["content"])

            mismatched_files = []
            matched_files = 0

            for filename, auth_hash in authoritative_checksums.items():
                if filename in mirror_checksums:
                    if mirror_checksums[filename] != auth_hash:
                        mismatched_files.append({
                            "file": filename,
                            "authoritative": auth_hash,
                            "mirror": mirror_checksums[filename]
                        })
                    else:
                        matched_files += 1

            if mismatched_files:
                print(f"  MISMATCH: {len(mismatched_files)} files differ")
                results["mismatch"].append({
                    "id": mirror_id,
                    "url": url,
                    "mismatched_files": mismatched_files,
                    "matched_files": matched_files,
                })
            else:
                print(f"  OK ({matched_files} files matched)")
                results["match"].append({
                    "id": mirror_id,
                    "url": url,
                    "matched_files": matched_files
                })

    return results


def run_audit():
    print(f"Fetching authoritative CHECKSUMS.md5...")
    auth_url = AUTHORITATIVE_BASE + TARGET_PATH
    auth_result = fetch_content(auth_url)

    if not auth_result["reachable"]:
        print(f"ERROR: Could not reach authoritative source: {auth_result['error']}")
        return

    authoritative_checksums = parse_checksums(auth_result["content"])
    print(f"Authoritative source has {len(authoritative_checksums)} file entries\n")

    print(f"Fetching https mirrors from database...")
    mirrors = get_mirrors(protocol="https")
    print(f"Found {len(mirrors)} mirrors\n")

    results = audit_mirrors(authoritative_checksums, auth_result["content"], mirrors)

    print(f"\n--- Audit Results ---")
    print(f"Match:       {len(results['match'])}")
    print(f"Mismatch:    {len(results['mismatch'])}")
    print(f"Not Found:   {len(results['not_found'])}")
    print(f"Invalid:     {len(results['invalid'])}")
    print(f"Unreachable: {len(results['unreachable'])}")

    if results["mismatch"]:
        print(f"\nMISMATCHED MIRRORS:")
        for m in results["mismatch"]:
            print(f"\n  {m['url']}")
            print(f"  Matched files: {m['matched_files']}")
            print(f"  Mismatched files: {len(m['mismatched_files'])}")
            for f in m["mismatched_files"][:5]:
                print(f"    {f['file']}")
                print(f"      authoritative: {f['authoritative']}")
                print(f"      mirror:        {f['mirror']}")
            if len(m["mismatched_files"]) > 5:
                print(f"    ... and {len(m['mismatched_files']) - 5} more")

    if results["not_found"]:
        print(f"\nNOT FOUND (404):")
        for m in results["not_found"]:
            print(f"  {m['url']}")

    if results["invalid"]:
        print(f"\nINVALID RESPONSE:")
        for m in results["invalid"]:
            print(f"  {m['url']} -> {m['error']}")

    if results["unreachable"]:
        print(f"\nUNREACHABLE:")
        for m in results["unreachable"]:
            print(f"  {m['url']} -> {m['error']}")


if __name__ == "__main__":
    run_audit()