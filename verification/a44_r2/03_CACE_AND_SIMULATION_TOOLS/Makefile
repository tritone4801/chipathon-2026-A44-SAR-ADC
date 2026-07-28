PYTHON ?= python3

.PHONY: preflight quick-verify full full-dry-run audit

preflight:
	$(PYTHON) scripts/a44_repro.py preflight

quick-verify:
	$(PYTHON) scripts/a44_repro.py quick-verify

full:
	$(PYTHON) scripts/a44_repro.py full

full-dry-run:
	$(PYTHON) scripts/a44_repro.py full-dry-run

audit:
	$(PYTHON) scripts/build_package_audit.py
	$(PYTHON) scripts/a44_repro.py audit
