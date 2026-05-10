import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DATA_DIR = Path("data/checksums")
AUTHORITATIVE_DIR = DATA_DIR / "authoritative"
MIRRORS_DIR = DATA_DIR / "mirrors"


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


def load_latest(directory: Path) -> dict:
    """Load the most recent file from a directory, return parsed checksums and filename."""
    files = sorted(directory.glob("*.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        return None, None
    latest = files[0]
    content = latest.read_text(encoding="utf-8")
    return parse_checksums(content), latest.name


def load_all_mirrors() -> dict:
    """Load all saved mirror checksum files. Returns dict of filename -> checksums dict."""
    results = {}
    for f in sorted(MIRRORS_DIR.glob("*.txt")):
        content = f.read_text(encoding="utf-8")
        parsed = parse_checksums(content)
        if parsed:
            results[f.name] = {
                "checksums": parsed,
                "file_count": len(parsed),
                "size": f.stat().st_size,
            }
    return results


def derive_mirror_name(filename: str) -> str:
    """Strip date suffix from filename to get a readable mirror name."""
    return re.sub(r'_\d{8}\.txt$', '', filename)


def analyze():
    print("Loading authoritative checksums...")
    auth_checksums, auth_filename = load_latest(AUTHORITATIVE_DIR)
    if not auth_checksums:
        print("ERROR: No authoritative file found in data/checksums/authoritative/")
        return
    print(f"Authoritative: {auth_filename} ({len(auth_checksums)} files)\n")

    print("Loading mirror checksums...")
    mirrors = load_all_mirrors()
    print(f"Found {len(mirrors)} saved mirror files\n")

    # Track which files differ across mirrors
    file_mismatch_count = defaultdict(int)
    mirror_summaries = []

    for filename, data in mirrors.items():
        mirror_name = derive_mirror_name(filename)
        mirror_checksums = data["checksums"]

        mismatched = []
        missing = []
        matched = 0

        for fname, auth_hash in auth_checksums.items():
            if fname not in mirror_checksums:
                missing.append(fname)
            elif mirror_checksums[fname] != auth_hash:
                mismatched.append({
                    "file": fname,
                    "authoritative": auth_hash,
                    "mirror": mirror_checksums[fname],
                })
                file_mismatch_count[fname] += 1
            else:
                matched += 1

        mirror_summaries.append({
            "name": mirror_name,
            "matched": matched,
            "mismatched": mismatched,
            "missing": missing,
            "file_count": data["file_count"],
            "size": data["size"],
        })

    # Sort by mismatch count descending
    mirror_summaries.sort(key=lambda x: len(x["mismatched"]), reverse=True)

    # Print mirror summary
    print("=" * 60)
    print("MIRROR SUMMARY")
    print("=" * 60)
    for m in mirror_summaries:
        status = "OK" if not m["mismatched"] else f"MISMATCH({len(m['mismatched'])})"
        missing_note = f" missing={len(m['missing'])}" if m["missing"] else ""
        print(f"  [{status}]{missing_note} {m['name']}")

    # Print files that mismatch most often
    if file_mismatch_count:
        print(f"\n{'=' * 60}")
        print("FILES THAT DIFFER MOST ACROSS MIRRORS")
        print("=" * 60)
        sorted_files = sorted(file_mismatch_count.items(), key=lambda x: x[1], reverse=True)
        for fname, count in sorted_files[:20]:
            print(f"  {count} mirrors differ: {fname}")

    # Print detail for mismatched mirrors
    print(f"\n{'=' * 60}")
    print("MISMATCH DETAIL")
    print("=" * 60)
    for m in mirror_summaries:
        if not m["mismatched"]:
            continue
        print(f"\n  {m['name']}")
        print(f"  Files matched: {m['matched']}  Mismatched: {len(m['mismatched'])}  Missing: {len(m['missing'])}")
        for f in m["mismatched"][:10]:
            print(f"    {f['file']}")
            print(f"      auth:   {f['authoritative']}")
            print(f"      mirror: {f['mirror']}")
        if len(m["mismatched"]) > 10:
            print(f"    ... and {len(m['mismatched']) - 10} more")


if __name__ == "__main__":
    analyze()