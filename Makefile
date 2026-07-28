PY ?= python

.PHONY: ideal-sar-preflight ideal-sar-test ideal-sar-report ideal-sar-all ideal-sar-clean

ideal-sar-preflight:
	$(PY) verification/ideal_sar/scripts/run_all.py preflight

ideal-sar-test:
	$(PY) verification/ideal_sar/scripts/run_all.py unit
	$(PY) verification/ideal_sar/scripts/run_all.py functional
	$(PY) verification/ideal_sar/scripts/run_all.py timing
	$(PY) verification/ideal_sar/scripts/run_all.py static
	$(PY) verification/ideal_sar/scripts/run_all.py dynamic
	$(PY) verification/ideal_sar/scripts/run_all.py dac
	$(PY) verification/ideal_sar/scripts/run_all.py power-harness
	$(PY) verification/ideal_sar/scripts/run_all.py fault-injection

ideal-sar-report:
	$(PY) verification/ideal_sar/scripts/run_all.py report

ideal-sar-all:
	$(PY) verification/ideal_sar/scripts/run_all.py all

ideal-sar-clean:
	$(PY) verification/ideal_sar/scripts/run_all.py clean

