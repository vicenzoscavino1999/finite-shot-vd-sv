# Freeze status

This page records the two frozen versions of the analysis plan and how to audit them. It
is documentation; it is not itself part of either freeze.

## The two versions

### v1: the original plan

- Manifest: `freeze_manifest.json`
- Hash file: `PAP_HASH.txt`
- Frozen commit: `0814ba796b7d8819e709780ffa01e9f94be7a727`
- Plan hash: `31e92d21e0faf32ded9aad84a189fa7ae447afa1fdd9d835f16b74fb8bc443bd`

The v1 tree can be recovered byte for byte with
`git checkout 0814ba796b7d8819e709780ffa01e9f94be7a727`.

### v2: the amendment adding a negative control to P1

- Manifest: `freeze_manifest_v2.json`
- Hash file: `PAP_HASH_v2.txt`
- Frozen commit: `555d3dc1032991ae38cb8ff2a5570f5a0f8bf1a1`
- Plan hash: `8ca588e73f32ba021cb4611460cf7e33fb0e3da754b80c1874a3fdd91a34055a`
- Amendment: `pap/amendment_v2_p1_control_negative.md`

v2 only adds files: it keeps the v1 hashes of every v1 file and puts the amendment logic
in new files (`pap/hash_pap_v2.py`, `reproducibility/run_all_v2.py`). An earlier v2 hash,
made before v2 was restricted to adding files, is superseded and not used.

## Which version governs what

- The v1 validation table follows `freeze_manifest.json` and `PAP_HASH.txt`.
- The v2 run, reported in the paper, follows `freeze_manifest_v2.json`, `PAP_HASH_v2.txt`
  and the amendment document.
- The P1 calibration, the secondary checks and Levels 2 and 3 are analyses added after
  the freeze; they are not part of either version.

## How to audit

```text
python pap/verify_freeze.py
```

`pap/hash_pap.py --check-only` and `pap/hash_pap_v2.py --check-only` only recompute a hash
of the current tree; they do not compare it with the registered hashes, so they are not
an audit.

`verify_freeze.py` reads the working-tree bytes and, when they differ only in line
endings, falls back to the committed `HEAD` content. An uncommitted edit to a frozen file
can therefore still pass if `HEAD` matches, so read the result with a clean
`git status --short`.

## Expected result

In v1, `pap/hash_pap.py` and `reproducibility/run_all.py` are reported as expected
differences: their committed content is identical to commit `0814ba7`, but a Windows
checkout writes them with CRLF line endings, while the v1 hashes were taken with LF.

```text
| manifest | frozen_commit | pap_hash | targets | OK | EXPECTED-DRIFT | CHANGED | MISSING | aggregate | hash_file | verdict |
|---|---|---|---:|---:|---:|---:|---:|---|---|---|
| freeze_manifest.json (v1) | 0814ba796b7d | 31e92d21e0fa | 57 | 55 | 2 | 0 | 0 | OK | OK | INTACT_WITH_EXPECTED_DRIFT |
| freeze_manifest_v2.json (v2) | 555d3dc10329 | 8ca588e73f32 | 62 | 62 | 0 | 0 | 0 | OK | OK | INTACT_ZERO_DRIFT |
```
