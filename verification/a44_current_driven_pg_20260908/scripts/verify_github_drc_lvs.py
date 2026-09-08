#!/usr/bin/env python3
"""Run DRC/LVS from a clean GitHub-derived checkout and its YAML/LVS binding."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

import yaml


PDK = Path('/foss/pdks/gf180mcuD')
TOOLS = Path('/foss/tools/bin')


def expand_repo_path(value: str, repo: Path) -> Path:
    value = value.replace('$UPRJ_ROOT', str(repo)).replace('$PDK', 'gf180mcuD')
    return Path(value)


def run_logged(command: list[str], cwd: Path, log_path: Path, env: dict[str, str]) -> int:
    with log_path.open('x') as log:
        result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--expected-commit', required=True)
    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)

    head = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    status = subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True)
    if head != args.expected_commit or status:
        raise ValueError({'HEAD': head, 'expected': args.expected_commit, 'status': status})

    info_path = repo / 'info.yaml'
    info = yaml.safe_load(info_path.read_text(encoding='utf-8'))
    lvs_relative = info['project']['lvs_config']
    if lvs_relative != 'lvs_config.json':
        raise ValueError(f'unexpected info.yaml lvs_config: {lvs_relative}')
    lvs_path = repo / lvs_relative
    config = json.loads(lvs_path.read_text(encoding='utf-8'))
    top = config['TOP_SOURCE']
    if top != 'A44_A' or config['TOP_LAYOUT'] != '$TOP_SOURCE':
        raise ValueError('unexpected TOP binding')
    gds = expand_repo_path(config['LAYOUT_FILE'], repo)
    spice_files = [expand_repo_path(value, repo) for value in config['LVS_SPICE_FILES']]
    verilog_files = [expand_repo_path(value, repo) for value in config['LVS_VERILOG_FILES']]
    std_lib = config['STD_CELL_LIBRARY']
    std_spice = PDK / f'libs.ref/{std_lib}/spice/{std_lib}.spice'
    setup = PDK / 'libs.tech/netgen/gf180mcuD_setup.tcl'
    restore = repo / 'verification/a44_def_alignment/scripts/restore_A44_A_ports.tcl'
    required = [info_path, lvs_path, gds, std_spice, setup, restore, *spice_files, *verilog_files]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(missing)

    binding = {
        'status': 'PASS_GITHUB_YAML_AND_LVS_BINDING',
        'github_derived_checkout_commit': head,
        'git_worktree_clean': True,
        'info_yaml': info_path.relative_to(repo).as_posix(),
        'lvs_config_from_info_yaml': lvs_relative,
        'top_source': top,
        'layout_file': gds.relative_to(repo).as_posix(),
        'lvs_spice_files': [path.relative_to(repo).as_posix() for path in spice_files],
        'lvs_verilog_files': [path.relative_to(repo).as_posix() for path in verilog_files],
        'std_cell_library': std_lib,
        'all_declared_inputs_exist': True,
        'hash_manifest_used': False,
    }
    (out / 'CONFIG_BINDING.json').write_text(json.dumps(binding, indent=2) + '\n', encoding='utf-8')

    env = dict(
        os.environ,
        DISPLAY=':1', QT_QPA_PLATFORM='offscreen',
        OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
        PATH=f'/foss/tools/bin:/foss/tools/klayout:{os.environ.get("PATH", "")}',
    )
    magic_dir = out / 'MAGIC_NETGEN'
    magic_dir.mkdir()
    run_tcl = magic_dir / 'run.tcl'
    run_tcl.write_text('\n'.join([
        'drc off', 'locking disable', 'crashbackups stop',
        'gds rescale false', 'gds readonly true', f'gds read {{{gds}}}',
        f'load {top}', f'source {{{restore}}}', 'select top cell',
        'box -20um -20um 1200um 1200um', 'drc on', 'drc euclidean on',
        'drc style drc(full)', 'drc check', 'drc catchup',
        f'set f [open {{{magic_dir / "DRC_COUNT.txt"}}} w]',
        'puts $f [drc list count total]', 'close $f',
        f'set f [open {{{magic_dir / "DRC_WHY.txt"}}} w]',
        'puts $f [drc listall why]', 'close $f',
        'extract do local', 'extract no capacitance', 'extract no coupling',
        'extract no resistance', 'extract no adjust', 'extract unique',
        f'extract path {{{magic_dir}}}', 'extract all', 'ext2spice lvs',
        f'ext2spice -p {{{magic_dir}}} -o {{{magic_dir / "A44_A.spice"}}} {top}',
        'quit -noprompt',
    ]) + '\n', encoding='utf-8')
    magic_rc = run_logged([
        str(TOOLS / 'magic'), '-dnull', '-noconsole',
        '-rcfile', str(PDK / 'libs.tech/magic/gf180mcuD.magicrc'), str(run_tcl),
    ], magic_dir, magic_dir / 'MAGIC.log', env)
    drc_count = int((magic_dir / 'DRC_COUNT.txt').read_text().strip())

    lvs_lines = [
        f'set layout [readnet spice {{{magic_dir / "A44_A.spice"}}}]',
        'set source [readnet spice /dev/null]',
        f'readnet spice {{{std_spice}}} $source',
    ]
    lvs_lines.extend(f'readnet spice {{{path}}} $source' for path in spice_files)
    lvs_lines.extend(f'readnet verilog {{{path}}} $source' for path in verilog_files)
    lvs_lines.append(
        f'lvs "$layout {top}" "$source {top}" {{{setup}}} {{{magic_dir / "LVS.log"}}} -json'
    )
    lvs_tcl = magic_dir / 'lvs.tcl'
    lvs_tcl.write_text('\n'.join(lvs_lines) + '\n', encoding='utf-8')
    netgen_rc = run_logged(
        [str(TOOLS / 'netgen'), '-batch', 'source', str(lvs_tcl)],
        magic_dir, magic_dir / 'NETGEN.log', env,
    )
    lvs_log = (magic_dir / 'LVS.log').read_text(errors='replace')
    lvs_json = json.loads((magic_dir / 'LVS.json').read_text())
    bad = [
        row for row in lvs_json
        if row.get('badnets') or row.get('badelements') or row.get('properties')
    ]
    lvs_unique = 'Circuits match uniquely.' in lvs_log and not bad

    klayout_dir = out / 'KLAYOUT'
    klayout_dir.mkdir()
    klayout_rc = run_logged([
        'python3', str(PDK / 'libs.tech/klayout/tech/drc/run_drc.py'),
        f'--path={gds}', '--variant=D', f'--topcell={top}', '--mp=1', '--thr=1',
        '--run_mode=deep', f'--run_dir={klayout_dir}', '--antenna',
    ], klayout_dir, klayout_dir / 'KLAYOUT.log', env)
    reports = [
        {'name': path.name, 'items': len(ET.parse(path).findall('./items/item'))}
        for path in sorted(klayout_dir.glob('*.lyrdb'))
    ]
    klayout_clean = klayout_rc == 0 and len(reports) >= 2 and not any(row['items'] for row in reports)

    passed = magic_rc == 0 and drc_count == 0 and netgen_rc == 0 and lvs_unique and klayout_clean
    result = {
        'status': 'PASS_GITHUB_CONFIG_BOUND_DRC_LVS' if passed else 'FAIL_GITHUB_CONFIG_BOUND_DRC_LVS',
        'pass': passed,
        'github_derived_checkout_commit': head,
        'yaml_and_lvs_binding': binding['status'],
        'magic': {'returncode': magic_rc, 'DRC_errors': drc_count},
        'netgen': {'returncode': netgen_rc, 'LVS_unique_match': lvs_unique, 'bad_sections': len(bad)},
        'klayout': {'returncode': klayout_rc, 'reports': reports, 'clean': klayout_clean},
        'scope': 'GitHub-bound A44_A GDS, info.yaml/lvs_config.json inputs, GF180MCU-D DRC and mixed-signal LVS.',
        'not_PEX_performance_density_ESD_stress_or_foundry_signoff': True,
    }
    (out / 'SUMMARY.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
