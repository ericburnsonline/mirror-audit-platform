import requests
from bs4 import BeautifulSoup
from coordinator.db import get_connection
from dotenv import load_dotenv

load_dotenv()

MIRROR_LIST_URL = "https://mirrors.slackware.com/mirrorlist/"

SUPPORTED_PROTOCOLS = {"https", "http", "ftp", "rsync"}


def fetch_mirror_list():
    response = requests.get(MIRROR_LIST_URL, timeout=10)
    response.raise_for_status()
    return response.text


def parse_mirrors(html):
    soup = BeautifulSoup(html, "html.parser")
    mirrors = []

    pre = soup.find("pre")
    if not pre:
        return mirrors

    for p in pre.find_all("p"):
        # First line of the <p> contains the protocol
        p_text = p.get_text(separator="\n")
        first_line = p_text.split("\n")[0].lower()

        current_protocol = None
        for protocol in SUPPORTED_PROTOCOLS:
            if protocol in first_line:
                current_protocol = protocol
                break

        if not current_protocol:
            continue

        # Each <a> tag is a mirror, preceded by a text node with the country code
        for a in p.find_all("a"):
            url = a.get("href", "").strip()
            if not url:
                continue

            prev = a.previous_sibling
            country_code = "unknown"
            if prev and isinstance(prev, str):
                parts = prev.strip().split()
                if parts:
                    country_code = parts[-1]

            mirrors.append({
                "country_code": country_code[:10],
                "protocol": current_protocol,
                "url": url,
            })

    return mirrors

    
def upsert_mirrors(mirrors):
    conn = get_connection()
    cur = conn.cursor()

    new_count = 0
    updated_count = 0

    for mirror in mirrors:
        cur.execute("""
            INSERT INTO mirrors (country_code, protocol, url)
            VALUES (%(country_code)s, %(protocol)s, %(url)s)
            ON CONFLICT (url) DO UPDATE
                SET last_seen = NOW(),
                    active = TRUE
            RETURNING (xmax = 0) AS inserted
        """, mirror)

        row = cur.fetchone()
        if row and row[0]:
            new_count += 1
        else:
            updated_count += 1

    conn.commit()
    cur.close()
    conn.close()

    return new_count, updated_count


def run_discovery():
    print(f"Fetching mirror list from {MIRROR_LIST_URL}...")
    html = fetch_mirror_list()

    print("Parsing mirrors...")
    mirrors = parse_mirrors(html)
    print(f"Found {len(mirrors)} mirrors")

    print("Upserting into database...")
    new_count, updated_count = upsert_mirrors(mirrors)
    print(f"Done. New: {new_count}, Updated: {updated_count}")


if __name__ == "__main__":
    run_discovery()