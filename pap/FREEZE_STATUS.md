# Freeze Status

Status: audit_provenance_note. Additive documentation; not a freeze, not an
adjudication, and not a re-freeze.

## Registered Freezes

### v1 original PAP

The original pre-registered design is recorded as:

- Manifest: `freeze_manifest.json`
- Hash file: `PAP_HASH.txt`
- Frozen commit: `0814ba796b7d8819e709780ffa01e9f94be7a727`
- PAP hash: `31e92d21e0faf32ded9aad84a189fa7ae447afa1fdd9d835f16b74fb8bc443bd`

The v1 tree is recoverable byte-for-byte with:

```text
git checkout 0814ba796b7d8819e709780ffa01e9f94be7a727
```

### v2 P1 amendment PAP

The operational amended freeze for the P1 negative-control amendment is recorded
as:

- Manifest: `freeze_manifest_v2.json`
- Hash file: `PAP_HASH_v2.txt`
- Frozen commit: `555d3dc1032991ae38cb8ff2a5570f5a0f8bf1a1`
- PAP hash: `8ca588e73f32ba021cb4611460cf7e33fb0e3da754b80c1874a3fdd91a34055a`

This is the clean append-only v2 history. The earlier non-append-only v2 hash is
not the active state of this repository.

## Helper Drift

The current-tree v1 audit reports `pap/hash_pap.py` and
`reproducibility/run_all.py` as expected drift for v1 only. Their git content is
identical to commit `0814ba7...`, and v2 preserves the exact v1 hashes for both
files append-only. The current-tree v1 drift flag is caused by raw working-tree
line endings: this Windows checkout materializes CRLF bytes while the registered
v1 hashes used LF bytes.

In the current clean v2, amendment logic lives in new files:

- `pap/hash_pap_v2.py`
- `reproducibility/run_all_v2.py`

`freeze_manifest_v2.json` preserves the v1 hashes for `pap/hash_pap.py` and
`reproducibility/run_all.py` and adds the v2 helpers append-only.

## Which Freeze Governs What

- The original v1 adjudication is governed by `freeze_manifest.json` /
  `PAP_HASH.txt`.
- The amended P1 negative-control run is governed by `freeze_manifest_v2.json` /
  `PAP_HASH_v2.txt` and the amendment document
  `pap/amendment_v2_p1_control_negative.md`.
- The post-adjudication ensemble analyses and secondary endpoints after the
  freeze are additive analysis layers. They are not new pre-registered freezes.

## Hash Check Caveat

`pap/hash_pap.py --check-only` and `pap/hash_pap_v2.py --check-only` validate
that the current clean tree can produce a hash. They do not compare the current
tree against the registered PAP hashes.

The real registered-freeze audit is:

```text
python pap/verify_freeze.py
```

## Audit Semantics

`pap/verify_freeze.py` audits the committed git state, with explicit tolerance
for checkout EOL differences. It first checks raw working-tree bytes, then falls
back to the committed `HEAD` blob and tolerated LF/CRLF representations. An
uncommitted edit to a frozen file can therefore still report OK if `HEAD` still
matches the manifest. Interpret the audit only with `git status --short` clean.

## Evidence

```text
| manifest | frozen_commit | pap_hash | targets | OK | EXPECTED-DRIFT | CHANGED | MISSING | aggregate | hash_file | verdict |
|---|---|---|---:|---:|---:|---:|---:|---|---|---|
| freeze_manifest.json (v1) | 0814ba796b7d | 31e92d21e0fa | 57 | 55 | 2 | 0 | 0 | OK | OK | INTACT_WITH_EXPECTED_DRIFT |
| freeze_manifest_v2.json (v2) | 555d3dc10329 | 8ca588e73f32 | 62 | 62 | 0 | 0 | 0 | OK | OK | INTACT_ZERO_DRIFT |
```
