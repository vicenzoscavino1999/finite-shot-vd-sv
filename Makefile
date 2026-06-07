.PHONY: reproduce run verify verify-freeze figures test check reproduce-fast reproduce-full \
        reproduce-level1 analysis-from-hardware check-env determinism-check \
        level2-foundation level2-sampling

reproduce: run verify

run:
	python reproducibility/run_all.py

verify:
	python reproducibility/verify.py --reference reproducibility/reference/

verify-freeze:
	python pap/verify_freeze.py

figures:
	python scripts/generate_all_figures.py

test:
	pytest tests/ -v

check: test verify

reproduce-fast:
	python reproducibility/run_all.py --mode fast
	python reproducibility/verify.py --reference reproducibility/reference/

reproduce-full:
	python reproducibility/run_all.py --mode full
	python reproducibility/verify.py --reference reproducibility/reference/

reproduce-level1:
	python reproducibility/run_all.py --level 1
	python reproducibility/verify.py --reference reproducibility/reference/

analysis-from-hardware:
	python reproducibility/run_all.py --level 3 --from-archived-counts
	python reproducibility/verify.py --reference reproducibility/reference/

check-env:
	python reproducibility/run_all.py --check-env-only

level2-foundation:
	python -m level2.circuits

level2-sampling:
	python -m level2.sampling

determinism-check:
	python reproducibility/run_all.py --mode fast --output results/determinism-run-1
	python reproducibility/run_all.py --mode fast --output results/determinism-run-2
	python reproducibility/verify.py \
		--reference results/determinism-run-1 \
		--generated results/determinism-run-2 \
		--exact-numeric
