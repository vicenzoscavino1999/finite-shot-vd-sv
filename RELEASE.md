# Release record

| Item | Value |
| --- | --- |
| Version | `v1.0.1` |
| Zenodo DOI | `10.5281/zenodo.20682998` |
| Paper | *Finite-Shot Operating Windows for Virtual Distillation and Symmetry Verification*, arXiv:2606.15464 |

## Environment

- Platform: `linux/amd64`
- Base image: `python:3.12.4-slim`, digest
  `sha256:a074fac67aa01841fee592d00bae14d25dcaf98ef6e12a683ecceb7e0147e2d1`
- Dependencies: `requirements.lock`, installed with
  `python -m pip install --require-hashes -r requirements.lock`
- The built image is not published to a container registry; build it from `Dockerfile`.

## Archived outputs

- Level 1 reference outputs: `reproducibility/reference/`, generated in the Docker image
  in `--mode full`, with their metadata in
  `reproducibility/reference/reference_manifest.json`.
- Level 1 runs reported in the paper: `results/confirmatory_v2/` (v2) and
  `results/confirmatory_full/` (v1).
- Level 3 hardware counts and analyses: `level3/archive/`, registered in
  `level3/archive/level3_archive_manifest.json` and `level3/archive/checksums.sha256`.
  Copies of the archive elsewhere should keep these checksums.
