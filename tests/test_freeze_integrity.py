from pathlib import Path
import json

from tools.verify_freeze_integrity import verify_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_registered_freeze_manifests_match_their_declared_commits():
    checks = [
        ("freeze_manifest.json", "PAP_HASH.txt"),
        ("freeze_manifest_v2.json", "PAP_HASH_v2.txt"),
    ]
    for manifest_name, hash_name in checks:
        result = verify_manifest(REPO_ROOT / manifest_name, hash_file=REPO_ROOT / hash_name)
        assert result.passed, result.mismatches
        assert result.target_count > 0


def test_v2_manifest_preserves_v1_helper_entries_append_only():
    v1 = json.loads((REPO_ROOT / "freeze_manifest.json").read_text(encoding="utf-8"))
    v2 = json.loads((REPO_ROOT / "freeze_manifest_v2.json").read_text(encoding="utf-8"))
    v1_entries = {entry["path"]: entry for entry in v1["targets"]}
    v2_entries = {entry["path"]: entry for entry in v2["targets"]}

    for path in ("pap/hash_pap.py", "reproducibility/run_all.py"):
        assert v2_entries[path]["bytes"] == v1_entries[path]["bytes"]
        assert v2_entries[path]["sha256"] == v1_entries[path]["sha256"]

    assert "pap/hash_pap_v2.py" in v2_entries
    assert "reproducibility/run_all_v2.py" in v2_entries
