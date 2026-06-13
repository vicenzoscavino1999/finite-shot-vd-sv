# Release Reproducibility Record

Current status: reproducibility snapshot for the submitted manuscript. This
record documents the canonical environment, reference data, and archive boundary
claimed by this repository snapshot.

## Canonical Container

- Platform: `linux/amd64`
- Base image: `python:3.12.4-slim`
- Base digest:
  `sha256:a074fac67aa01841fee592d00bae14d25dcaf98ef6e12a683ecceb7e0147e2d1`
- Dependency lock: `requirements.lock`
- Install command:
  `python -m pip install --require-hashes -r requirements.lock`

The local validation image tag used during this hardening pass is
`finite-shot-vd-sv:linux-canonical`. No container registry digest is claimed in
this snapshot.

## Reference Data

`reproducibility/reference/` is the canonical Linux/amd64 Docker Level 1
reference package. It was regenerated in `--mode full` and records platform,
dependency, lock, RNG, and deterministic-env metadata in
`reproducibility/reference/reference_manifest.json`.

Canonical exact verifier:

```bash
python reproducibility/verify_current.py \
  --reference reproducibility/reference \
  --generated reproducibility/reference \
  --exact-numeric
```

Expected line:

```text
VERIFY PASS: 18260 numeric comparisons within tolerance across 7 files; reference checksums OK
```

## Level 3 Archive Manifest

`level3/archive/level3_archive_manifest.json` and
`level3/archive/checksums.sha256` register the committed raw-count `.json.gz`
archives and consolidated analysis `.json` files. External archive copies should
preserve or supersede these checksums.

## Release Identifiers

- Version: `v1.0.1`.
- Zenodo DOI: `10.5281/zenodo.20682998`.
- Container registry digest: not claimed in this snapshot.
- Byte-identical manuscript/figure PDFs: not claimed.
