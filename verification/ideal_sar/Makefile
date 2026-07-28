PY ?= python

.PHONY: preflight unit functional timing static histogram dynamic dac power-harness fault-injection repeatability report all clean

preflight:
	$(PY) scripts/run_all.py preflight

unit:
	$(PY) scripts/run_all.py unit

functional:
	$(PY) scripts/run_all.py functional

timing:
	$(PY) scripts/run_all.py timing

static:
	$(PY) scripts/run_all.py static

histogram:
	$(PY) scripts/run_all.py histogram

dynamic:
	$(PY) scripts/run_all.py dynamic

dac:
	$(PY) scripts/run_all.py dac

power-harness:
	$(PY) scripts/run_all.py power-harness

fault-injection:
	$(PY) scripts/run_all.py fault-injection

repeatability:
	$(PY) scripts/run_all.py repeatability

report:
	$(PY) scripts/run_all.py report

all:
	$(PY) scripts/run_all.py all

clean:
	$(PY) scripts/run_all.py clean
