# A44 Q2 analog secondary ESD implementation

The current `A44_A` implementation is `Q2_LINK18_HIER_R1_ANALOG_ESD_R1`.
Four `io_secondary_5p0` cells connect the north analog pins to the Q2 CORE.

| Analog pin | Instance | Protected CORE net | Supply rails |
| --- | --- | --- | --- |
| VREFN | `XESD_VREFN` | `XCORE/VREFN` | VDD / GND |
| VINN | `XESD_VINN` | `XCORE/VINN` | VDD / GND |
| VINP | `XESD_VINP` | `XCORE/VINP` | VDD / GND |
| VREFP | `XESD_VREFP` | `XCORE/VREFP` | VDD / GND |

Each cell contains one W=40 um, L=10 um poly resistor and four diodes to each
supply rail on the protected side. Each diode occupies 100 um2 with 40 um
perimeter. The four cells add four resistors and 32 diodes to the TOP.

The source is the official
[secondary_ESD_m2.gds](https://github.com/sscs-ose/sscs-chipathon-2026/blob/f96d9434d0e258038c5c795d41caae364339eee9/resources/Analog/secondary_ESD_m2.gds).
The original file and license are in [reference/official](reference/official).
The standalone published GDS uses 1 nm database units and retains the official
cell names. `info.yaml` records `secondary_esd: true` on all four analog pins.

The full TOP circuit reference is [A44_A_lvs_reference.spice](spice/A44_A_lvs_reference.spice).
The editable ESD [schematic](schematic/A44_SECONDARY_ESD_M2_SCHEM.sch),
[symbol](schematic/A44_SECONDARY_ESD_M2_SCHEM.sym) and
[subcircuit](spice/A44_SECONDARY_ESD_M2_SCHEM.spice) are included with the source.

See [IMPLEMENTATION.json](IMPLEMENTATION.json) for instance and source-cache
bindings, [IMAGE_BINDING.json](IMAGE_BINDING.json) for image dimensions,
[the layout catalog](../../layout/README.md), and [the update record](../../layout/CHANGELOG.md).
