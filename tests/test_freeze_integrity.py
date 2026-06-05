from pathlib import Path

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
