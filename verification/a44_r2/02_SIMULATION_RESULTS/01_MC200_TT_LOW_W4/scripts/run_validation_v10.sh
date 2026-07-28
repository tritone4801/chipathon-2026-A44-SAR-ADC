#!/usr/bin/env bash
set +e

source /etc/profile
root=/foss/designs/manual_goal/verification/A44_FAST64_D3_MC10_1H_V10
export A44_VALIDATION_ID=A44_FAST64_D3_MC10_1H_V10
export A44_EXPECTED_ROOT_NAME=A44_FAST64_D3_MC10_1H_V10
export PYTHONPATH="$root/scripts"

cd "$root"
: > logs/runtime_validation_v10_console.log
/foss/tools/bin/python3 scripts/preflight_v10.py \
  >> logs/runtime_validation_v10_console.log 2>&1
preflight_rc=$?
if [[ "$preflight_rc" -ne 0 ]]; then
  printf '%s\n' "$preflight_rc" > results/runtime_validation_v10.exit
  exit "$preflight_rc"
fi

/foss/tools/bin/python3 scripts/validate_runtime_v10.py \
  >> logs/runtime_validation_v10_console.log 2>&1
rc=$?
printf '%s\n' "$rc" > results/runtime_validation_v10.exit
exit "$rc"
