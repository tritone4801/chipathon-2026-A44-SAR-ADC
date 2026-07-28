#!/usr/bin/env python3
"""Attach the host NVMe probe to the measured resource-admission decision."""

import json

from v7_common import CONFIG_DIR, RESULT_DIR, write_json_atomic


def main():
    cache_path = CONFIG_DIR / "qualification_cache.json"
    cache = json.loads(cache_path.read_text(encoding="ascii"))
    probe_path = RESULT_DIR / "host_storage_probe.json"
    probe = json.loads(probe_path.read_text(encoding="ascii"))
    storage_pass = all(
        (
            bool(probe.get("local_fixed_disk")),
            probe.get("disk_health_status") == "Healthy",
            probe.get("physical_health_status") == "Healthy",
            probe.get("physical_media_type") == "SSD",
            probe.get("disk_bus_type") in {"NVMe", "SATA", "SAS"},
        )
    )
    measured_pass = bool(cache.get("resource", {}).get("admission_pass"))
    complete_pass = measured_pass and storage_pass
    fallback_accepted = all(
        (
            cache.get("session_equivalence_complete", False),
            cache.get("session_fallback_documented", False),
            cache.get("session_execution_mode") == "SEPARATE_PROCESS_FALLBACK",
            cache.get("numerical_qualification_pass", False),
        )
    )
    cache["session_fallback_accepted_per_section_5_3"] = fallback_accepted
    cache["session_equivalence_disposition"] = (
        "PASS"
        if cache.get("session_equivalence_pass", False)
        else "FAIL_USE_SEPARATE_PROCESS_FALLBACK"
    )
    cache["resource"]["host_storage_probe"] = probe
    cache["resource"]["local_ssd_nvme_output_path_pass"] = storage_pass
    cache["resource_admission_pass"] = complete_pass
    if not fallback_accepted:
        cache["blocked_status"] = "BLOCKED_MEASUREMENT_CHAIN_NOT_QUALIFIED"
    elif not complete_pass:
        cache["blocked_status"] = "BLOCKED_32GB_ONE_DAY_RESOURCE_ADMISSION"
    elif cache.get("blocked_status") in {
        "BLOCKED_32GB_ONE_DAY_RESOURCE_ADMISSION",
        "BLOCKED_MEASUREMENT_CHAIN_NOT_QUALIFIED",
    }:
        cache["blocked_status"] = ""
    write_json_atomic(cache_path, cache)
    write_json_atomic(RESULT_DIR / "qualification_audit.json", cache)
    print(
        f"RESOURCE_ADMISSION measured={measured_pass} storage={storage_pass} "
        f"complete={complete_pass} fallback_accepted={fallback_accepted}"
    )
    if not complete_pass or not fallback_accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
