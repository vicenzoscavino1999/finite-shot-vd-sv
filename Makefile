PYTHON ?= python
RUN_ALL ?= reproducibility/run_all_current.py
RESULTS ?= results
REFERENCE ?= reproducibility/reference

.PHONY: reproduce run verify verify-reference verify-freeze verify-level3 figures test test-ci \
        check check-ci reproduce-fast reproduce-full reproduce-level1 analysis-from-hardware \
        level3-analysis check-env determinism-check level2-foundation level2-sampling

reproduce: run verify

run:
	$(PYTHON) $(RUN_ALL) --output $(RESULTS)

verify:
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS)

verify-reference:
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(REFERENCE) --exact-numeric

verify-freeze:
	$(PYTHON) pap/verify_freeze.py

verify-level3:
	$(PYTHON) scripts/verify_level3_archives.py

figures:
	$(PYTHON) scripts/generate_all_figures.py

test:
	$(PYTHON) -m pytest tests/ -q

test-ci:
	$(PYTHON) -m pytest tests/ -q --ignore=tests/test_freeze_integrity.py

check: test verify verify-reference verify-level3 verify-freeze

check-ci: reproduce-fast test-ci verify-reference verify-level3

reproduce-fast:
	$(PYTHON) $(RUN_ALL) --mode fast --output $(RESULTS)
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS)

reproduce-full:
	$(PYTHON) $(RUN_ALL) --mode full --output $(RESULTS)
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS)

reproduce-level1:
	$(PYTHON) $(RUN_ALL) --level 1 --output $(RESULTS)
	$(PYTHON) reproducibility/verify_current.py --reference $(REFERENCE) --generated $(RESULTS)

analysis-from-hardware:
	$(PYTHON) $(RUN_ALL) --level 3 --from-archived-counts

level3-analysis:
	$(PYTHON) $(RUN_ALL) --level 3 --from-archived-counts

check-env:
	$(PYTHON) $(RUN_ALL) --check-env-only --strict-env

level2-foundation:
	$(PYTHON) -m level2.circuits

level2-sampling:
	$(PYTHON) -m level2.sampling

determinism-check:
	$(PYTHON) $(RUN_ALL) --mode fast --output results/determinism-run-1
	$(PYTHON) $(RUN_ALL) --mode fast --output results/determinism-run-2
	$(PYTHON) reproducibility/verify_current.py \
		--reference results/determinism-run-1 \
		--generated results/determinism-run-2 \
		--exact-numeric \
		--skip-reference-checksums
