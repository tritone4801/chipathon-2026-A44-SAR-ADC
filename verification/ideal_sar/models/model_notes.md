# Ideal Model Notes

This validation phase deliberately models only:

- ideal straight-binary quantization over `-1.70 V <= VINP-VINN <= +1.70 V`;
- ideal threshold and code-center DAC transfer functions;
- ideal one-bit comparator decisions;
- CLKS-falling conversion start, internal `EOC_INT`, `CLK_BIT[7:0]`, and
  output-register hold/update behavior;
- deterministic digital interface behavior.

It deliberately excludes process variation, capacitor mismatch, comparator
offset/noise, sampling noise, jitter, reference bounce,
process-voltage-temperature corners, and layout
parasitics. Those effects belong to later schematic, layout, and post-layout
verification stages.

The Python direct quantizer, Python SAR loop, and independent oracle are kept as
separate code paths. The SystemVerilog model is provided for cocotb/RTL timing
checks when an HDL simulator is installed.
