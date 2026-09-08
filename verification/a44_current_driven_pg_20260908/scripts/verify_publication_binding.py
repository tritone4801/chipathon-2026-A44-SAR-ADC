#!/usr/bin/env python3
"""Lightweight structural check for the current repository layout binding."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import klayout.db as k
import yaml


def close_list(left: list[float], right: list[float], tolerance: float = 1e-6) -> bool:
    return len(left) == len(right) and all(abs(a - b) <= tolerance for a, b in zip(left, right))


def inspect_gds(path: Path, top_name: str) -> dict:
    layout = k.Layout()
    layout.read(str(path))
    cell = layout.cell(top_name)
    if cell is None:
        raise ValueError(f'{top_name} missing from {path}')
    top_names = sorted(cell.name for cell in layout.top_cells())
    box = cell.bbox()
    return {
        'path': path.as_posix(),
        'top': top_name,
        'stream_top_cells': top_names,
        'cells': layout.cells(),
        'bbox_um': [box.left * layout.dbu, box.bottom * layout.dbu,
                    box.right * layout.dbu, box.top * layout.dbu],
        'bytes': path.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--out-json', required=True, type=Path)
    args = parser.parse_args()
    repo = args.repo.resolve()
    current = json.loads((repo / 'layout/CURRENT_LAYOUT.json').read_text(encoding='utf-8'))
    info = yaml.safe_load((repo / 'info.yaml').read_text(encoding='utf-8'))
    lvs = json.loads((repo / info['project']['lvs_config']).read_text(encoding='utf-8'))

    entries = [
        ('PROJECT_TOP', current['repository_top']['gds'], current['repository_top']['design'],
         current['repository_top']['bbox_um']),
        ('CORE', current['embedded_core']['public_gds'], current['embedded_core']['contract_cell'],
         current['embedded_core']['bbox_um']),
    ]
    entries.extend((item['role'], item['gds'], item['top'], item.get('bbox_um') or item['visible_size_um'])
                   for item in current['components'])
    records = []
    for role, relative, top, expected in entries:
        row = inspect_gds(repo / relative, top)
        row['role'] = role
        if role == 'SECONDARY_ESD':
            actual_size = [row['bbox_um'][2] - row['bbox_um'][0], row['bbox_um'][3] - row['bbox_um'][1]]
            row['bbox_matches_binding'] = close_list(actual_size, expected)
        else:
            row['bbox_matches_binding'] = close_list(row['bbox_um'], expected)
        records.append(row)

    images = [repo / item['image'] for item in current['view_measurements']]
    binding_files = [repo / item for item in current['binding_files']]
    expected_lvs_spice = '$UPRJ_ROOT/' + current['lvs_reference']
    checks = {
        'selected_case_DRIVER_R2': current['selected_case'] == 'DRIVER_R2_CURRENT_DRIVEN_PG_REPAIR',
        'top_143_cells': records[0]['cells'] == current['gds_cell_count'] == 143,
        'all_GDS_bboxes_match': all(row['bbox_matches_binding'] for row in records),
        'all_images_exist': all(path.is_file() for path in images),
        'all_binding_files_exist': all(path.is_file() for path in binding_files),
        'info_yaml_selects_lvs_config': info['project']['lvs_config'] == 'lvs_config.json',
        'lvs_top_A44_A': lvs['TOP_SOURCE'] == current['repository_top']['design'] == 'A44_A',
        'lvs_layout_is_current_top_GDS': lvs['LAYOUT_FILE'] == '$UPRJ_ROOT/' + current['repository_top']['gds'],
        'lvs_spice_matches_current_binding': lvs['LVS_SPICE_FILES'] == [expected_lvs_spice],
        'powered_SAR_gate_Verilog_declared': lvs['LVS_VERILOG_FILES'] == [
            '$UPRJ_ROOT/verification/a44_q2_analog_esd/verilog/SAR_LOGIC_ACTUAL_RTL_SS.pnl.v'
        ],
        'official_interface_retained': current['repository_top']['logical_pins'] == 89
        and current['repository_top']['metal2_pin_shapes'] == 127,
    }
    result = {
        'status': 'PASS_DRIVER_R2_PUBLICATION_BINDING' if all(checks.values()) else 'FAIL_DRIVER_R2_PUBLICATION_BINDING',
        'pass': all(checks.values()),
        'checks': checks,
        'gds_records': records,
        'image_count': len(images),
        'binding_file_count': len(binding_files),
        'hash_manifest_used': False,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['pass'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
