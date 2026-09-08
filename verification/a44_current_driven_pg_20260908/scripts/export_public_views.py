#!/usr/bin/env python3
"""Export the DRIVER_R2-owned public GDS views and current layout images."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import time

import klayout.db as k
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch


LAYERS = [
    (34, 'M1', '#aeb6bd'),
    (36, 'M2', '#6290bd'),
    (42, 'M3', '#ba6d98'),
    (46, 'M4', '#54a8a0'),
    (75, 'FuseTop', '#65ae70'),
    (81, 'M5', '#d6a344'),
]


def bbox_um(cell: k.Cell, dbu: float) -> list[float]:
    box = cell.bbox()
    return [box.left * dbu, box.bottom * dbu, box.right * dbu, box.top * dbu]


def export_cell(layout: k.Layout, cell_name: str, output: Path) -> dict:
    cell = layout.cell(cell_name)
    if cell is None:
        raise ValueError(f'missing source cell {cell_name}')
    options = k.SaveLayoutOptions()
    options.set_format_from_filename(str(output))
    options.select_all_layers()
    options.select_cell(cell.cell_index())
    temporary = output.with_suffix('.new.gds')
    layout.write(str(temporary), options)
    temporary.replace(output)
    check = k.Layout()
    check.read(str(output))
    top = check.top_cell()
    if top is None or top.name != cell_name:
        raise ValueError(f'bad exported top for {output}: {top.name if top else None}')
    return {
        'path': output.as_posix(),
        'top': top.name,
        'cells': check.cells(),
        'bbox_um': bbox_um(top, check.dbu),
        'bytes': output.stat().st_size,
    }


def render(layout: k.Layout, cell_name: str, role: str, output: Path) -> dict:
    start = time.perf_counter()
    cell = layout.cell(cell_name)
    if cell is None:
        raise ValueError(f'missing render cell {cell_name}')
    box = cell.bbox()
    dbu = layout.dbu
    fig, ax = plt.subplots(figsize=(10, 9))
    fig.subplots_adjust(left=.10, right=.97, bottom=.18, top=.90)
    counts = {}
    for layer, label, color in LAYERS:
        layer_index = layout.find_layer(layer, 0)
        if layer_index is None:
            continue
        region = k.Region(cell.begin_shapes_rec(layer_index))
        vertices = []
        for polygon in region.each():
            parts = polygon.decompose_trapezoids() if polygon.holes() else [polygon]
            for part in parts:
                points = part.each_point_hull() if isinstance(part, k.Polygon) else part.each_point()
                vertices.append([(point.x * dbu, point.y * dbu) for point in points])
        counts[label] = len(vertices)
        ax.add_collection(PolyCollection(vertices, facecolors=color, edgecolors='none', rasterized=True))
    margin = max(box.width(), box.height()) * dbu * .015
    ax.set_xlim(box.left * dbu - margin, box.right * dbu + margin)
    ax.set_ylim(box.bottom * dbu - margin, box.top * dbu + margin)
    ax.set_aspect('equal')
    ax.set_xlabel('Local X (µm)')
    ax.set_ylabel('Local Y (µm)')
    ax.set_title(
        f'{role} — DRIVER_R2 current-driven PG layout\n'
        f'W = {box.width() * dbu:g} µm; H = {box.height() * dbu:g} µm',
        fontsize=13,
    )
    fig.legend(
        handles=[Patch(facecolor=color, label=label) for _, label, color in LAYERS],
        loc='lower center', bbox_to_anchor=(.5, .065), ncol=6, frameon=False,
    )
    fig.text(
        .5, .025,
        'Saved DRIVER_R2 GDS · selected metal/MIM layers · holes preserved · report only',
        ha='center', fontsize=9,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=200)
    plt.close(fig)
    return {
        'role': role,
        'cell': cell_name,
        'image': output.as_posix(),
        'bbox_um': bbox_um(cell, dbu),
        'displayed_layers': [layer for layer, _, _ in LAYERS],
        'polygons': counts,
        'seconds': time.perf_counter() - start,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-gds', required=True, type=Path)
    parser.add_argument('--repo', required=True, type=Path)
    args = parser.parse_args()
    source = args.source_gds.resolve()
    repo = args.repo.resolve()
    current = json.loads((repo / 'layout/CURRENT_LAYOUT.json').read_text(encoding='utf-8'))
    layout = k.Layout()
    layout.read(str(source))
    if layout.top_cell() is None or layout.top_cell().name != 'A44_A':
        raise ValueError('source top is not A44_A')

    affected = [
        ('PROJECT_TOP', 'A44_A', repo / 'gds/A44_A.gds'),
        ('CORE', current['embedded_core']['contract_cell'], repo / current['embedded_core']['public_gds']),
        ('COMPARATOR', next(item['top'] for item in current['components'] if item['role'] == 'COMPARATOR'),
         repo / next(item['gds'] for item in current['components'] if item['role'] == 'COMPARATOR')),
    ]
    exports = []
    shutil.copyfile(source, affected[0][2])
    top_check = k.Layout()
    top_check.read(str(affected[0][2]))
    exports.append({
        'role': 'PROJECT_TOP', 'path': affected[0][2].as_posix(), 'top': top_check.top_cell().name,
        'cells': top_check.cells(), 'bbox_um': bbox_um(top_check.top_cell(), top_check.dbu),
        'bytes': affected[0][2].stat().st_size, 'exact_source_copy': True,
    })
    for role, cell_name, output in affected[1:]:
        row = export_cell(layout, cell_name, output)
        row['role'] = role
        row['exact_source_copy'] = False
        exports.append(row)

    render_specs = [
        ('PROJECT_TOP', 'A44_A', 'A44_A.png'),
        ('CORE', current['embedded_core']['contract_cell'], 'A44_SAR_ADC_CORE_1000.png'),
    ]
    for item in current['components']:
        if item['role'] == 'SECONDARY_ESD':
            continue
        render_specs.append((item['role'], item['top'], Path(item['gds']).with_suffix('.png').name))
    dated = repo / 'layout/images/current_driven_pg_20260908'
    if dated.exists():
        raise FileExistsError(dated)
    dated.mkdir(parents=True)
    views = []
    for role, cell_name, filename in render_specs:
        image = dated / filename
        views.append(render(layout, cell_name, role, image))
        if role != 'PROJECT_TOP':
            shutil.copyfile(image, repo / 'layout/images' / filename)

    unchanged = []
    for item in current['components']:
        if item['role'] == 'COMPARATOR':
            continue
        public = k.Layout()
        public.read(str(repo / item['gds']))
        top = public.top_cell()
        unchanged.append({
            'role': item['role'], 'path': item['gds'], 'top': top.name,
            'bbox_um': bbox_um(top, public.dbu), 'not_rewritten': True,
        })

    result = {
        'status': 'EXPORTED_DRIVER_R2_PUBLIC_VIEWS_AND_IMAGES',
        'source_GDS': source.as_posix(),
        'source_top': 'A44_A',
        'source_cells': layout.cells(),
        'affected_owner_cells': ['A44_A', current['embedded_core']['contract_cell'],
                                 next(item['top'] for item in current['components'] if item['role'] == 'COMPARATOR')],
        'exports': exports,
        'unchanged_public_component_checks': unchanged,
        'views': views,
        'source_modified': False,
    }
    output = repo / 'verification/a44_current_driven_pg_20260908/IMAGE_BINDING.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
