PYTHON ?= python
RUN_ALL ?= reproducibility/run_all_current.py
RESULTS ?= results
REFERENCE ?= reproducibility/reference

.PHONY: reproduce run verify verify-exact verify-reference verify-freeze verify-level3 figures \
        test test-ci audit check check-ci reproduce-fast reproduce-full reproduce-full-tolerant \
        reproduce-level1 reproduce-all reference-manifest level3-manifest analysis-from-hardware \
        analysis-from-hardware-update level3-analysis check-env determinism-check \
        level2-foundation level2-sampling

reproduce: reproduce-full

run:
	$(PYTHON) $(RUN_ALL) --mode full --output $(RESULTS)

verify:
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS)

verify-exact:
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS) --exact-numeric

verify-reference:
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(REFERENCE) --exact-numeric

verify-freeze:
	$(PYTHON) pap/verify_freeze.py

verify-level3:
	$(PYTHON) scripts/verify_level3_archives.py

reference-manifest:
	$(PYTHON) scripts/refresh_reference_manifest.py

level3-manifest:
	$(PYTHON) scripts/write_level3_archive_manifest.py

figures:
	$(PYTHON) scripts/generate_all_figures.py

test:
	$(PYTHON) -m pytest tests/ -q

test-ci:
	$(PYTHON) -m pytest tests/ -q --ignore=tests/test_freeze_integrity.py

audit:
	$(PYTHON) -m pip_audit -r requirements.lock

check: test verify verify-reference verify-level3 verify-freeze

check-ci: check-env determinism-check reproduce-full-tolerant test-ci verify-reference verify-level3

reproduce-all: check-env reproduce-level1 test-ci verify-reference verify-level3 verify-freeze figures
	@echo "REPRODUCE_ALL_PASS: Level 1 exact, tests, PAP freeze, Level 3 archived-count verification, and figures completed"

reproduce-fast:
	$(PYTHON) $(RUN_ALL) --mode fast --output $(RESULTS)
	$(PYTHON) reproducibility/verify_current.py \
		--reference $(RESULTS) \
		--generated $(RESULTS) \
		--exact-numeric \
		--skip-reference-checksums

reproduce-full:
	$(PYTHON) $(RUN_ALL) --mode full --output $(RESULTS)
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS) --exact-numeric

reproduce-full-tolerant:
	$(PYTHON) $(RUN_ALL) --mode full --output $(RESULTS)
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS)

reproduce-level1:
	$(PYTHON) $(RUN_ALL) --mode full --level 1 --output $(RESULTS)
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS) --exact-numeric

analysis-from-hardware:
	@echo "analysis-from-hardware is read-only; use analysis-from-hardware-update to refresh committed Level 3 JSON summaries"
	$(PYTHON) $(RUN_ALL) --level 3 --from-archived-counts

analysis-from-hardware-update:
	$(PYTHON) scripts/reanalyze_level3_archives.py --update

level3-analysis:
	$(PYTHON) $(RUN_ALL) --level 3 --from-archived-counts

check-env:
	$(PYTHON) $(RUN_ALL) --check-env-only --strict-env

level2-foundation:
	$(PYTHON) -m level2.circuits

level2-sampling:
	$(PYTHON) -m level2.sampling

determinism-check:
	$(PYTHON) $(RUN_ALL) --mode full --output results/determinism-run-1
	$(PYTHON) $(RUN_ALL) --mode full --output results/determinism-run-2
	$(PYTHON) $(RUN_ALL) --mode full --output results/determinism-run-3
	$(PYTHON) reproducibility/verify_current.py \
		--reference results/determinism-run-1 \
		--generated results/determinism-run-2 \
		--exact-numeric \
		--skip-reference-checksums
	$(PYTHON) reproducibility/verify_current.py \
		--reference results/determinism-run-1 \
		--generated results/determinism-run-3 \
		--exact-numeric \
		--skip-reference-checksums
