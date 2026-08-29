# Restore exact corrected-official-DEF ports after a fresh GDS readback.
proc a44_restore_port {name layer x1 y1 x2 y2 number class use side} {
    box ${x1}um ${y1}um ${x2}um ${y2}um
    # The final GDS already carries one ordinary label on this pin
    # shape.  Reuse it; adding a duplicate would allocate two ports.
    select area label
    port make $number $side
    port $number class $class
    port $number use $use
    port $number connections $side
    select clear
}
a44_restore_port {GND} metal2 0 69.14 1 78.64 0 inout ground w
a44_restore_port {VDD} metal2 0 169.14 1 178.64 1 inout power w
a44_restore_port {CLKS_PU} metal2 0 273.655 1 274.035 2 output signal w
a44_restore_port {CLKS_PD} metal2 0 269.29 1 269.67 3 output signal w
a44_restore_port {CLKS} metal2 0 208.76 1 209.14 4 input signal w
a44_restore_port {DOUT_CS[7]} metal2 0 376.26 1 376.64 5 output signal w
a44_restore_port {DOUT_SL[7]} metal2 0 310.95 1 311.33 6 output signal w
a44_restore_port {DOUT_IE[7]} metal2 0 368.235 1 368.615 7 output signal w
a44_restore_port {DOUT_OE[7]} metal2 0 309.49 1 309.87 8 output signal w
a44_restore_port {DOUT_PU[7]} metal2 0 373.655 1 374.035 9 output signal w
a44_restore_port {DOUT_PD[7]} metal2 0 369.29 1 369.67 10 output signal w
a44_restore_port {DOUT_OUT[7]} metal2 0 310.22 1 310.6 11 output signal w
a44_restore_port {DOUT_PDRV0[7]} metal2 0 372.51 1 372.89 12 output signal w
a44_restore_port {DOUT_PDRV1[7]} metal2 0 371.8 1 372.18 13 output signal w
a44_restore_port {DOUT_IN[7]} metal2 0 308.76 1 309.14 14 input signal w
a44_restore_port {DOUT_CS[6]} metal2 0 476.26 1 476.64 15 output signal w
a44_restore_port {DOUT_SL[6]} metal2 0 410.95 1 411.33 16 output signal w
a44_restore_port {DOUT_IE[6]} metal2 0 468.235 1 468.615 17 output signal w
a44_restore_port {DOUT_OE[6]} metal2 0 409.49 1 409.87 18 output signal w
a44_restore_port {DOUT_PU[6]} metal2 0 473.655 1 474.035 19 output signal w
a44_restore_port {DOUT_PD[6]} metal2 0 469.29 1 469.67 20 output signal w
a44_restore_port {DOUT_OUT[6]} metal2 0 410.22 1 410.6 21 output signal w
a44_restore_port {DOUT_PDRV0[6]} metal2 0 472.51 1 472.89 22 output signal w
a44_restore_port {DOUT_PDRV1[6]} metal2 0 471.8 1 472.18 23 output signal w
a44_restore_port {DOUT_IN[6]} metal2 0 408.76 1 409.14 24 input signal w
a44_restore_port {DOUT_CS[5]} metal2 0 576.26 1 576.64 25 output signal w
a44_restore_port {DOUT_SL[5]} metal2 0 510.95 1 511.33 26 output signal w
a44_restore_port {DOUT_IE[5]} metal2 0 568.235 1 568.615 27 output signal w
a44_restore_port {DOUT_OE[5]} metal2 0 509.49 1 509.87 28 output signal w
a44_restore_port {DOUT_PU[5]} metal2 0 573.655 1 574.035 29 output signal w
a44_restore_port {DOUT_PD[5]} metal2 0 569.29 1 569.67 30 output signal w
a44_restore_port {DOUT_OUT[5]} metal2 0 510.22 1 510.6 31 output signal w
a44_restore_port {DOUT_PDRV0[5]} metal2 0 572.51 1 572.89 32 output signal w
a44_restore_port {DOUT_PDRV1[5]} metal2 0 571.8 1 572.18 33 output signal w
a44_restore_port {DOUT_IN[5]} metal2 0 508.76 1 509.14 34 input signal w
a44_restore_port {DOUT_CS[4]} metal2 0 676.26 1 676.64 35 output signal w
a44_restore_port {DOUT_SL[4]} metal2 0 610.95 1 611.33 36 output signal w
a44_restore_port {DOUT_IE[4]} metal2 0 668.235 1 668.615 37 output signal w
a44_restore_port {DOUT_OE[4]} metal2 0 609.49 1 609.87 38 output signal w
a44_restore_port {DOUT_PU[4]} metal2 0 673.655 1 674.035 39 output signal w
a44_restore_port {DOUT_PD[4]} metal2 0 669.29 1 669.67 40 output signal w
a44_restore_port {DOUT_OUT[4]} metal2 0 610.22 1 610.6 41 output signal w
a44_restore_port {DOUT_PDRV0[4]} metal2 0 672.51 1 672.89 42 output signal w
a44_restore_port {DOUT_PDRV1[4]} metal2 0 671.8 1 672.18 43 output signal w
a44_restore_port {DOUT_IN[4]} metal2 0 608.76 1 609.14 44 input signal w
a44_restore_port {DOUT_CS[3]} metal2 0 776.26 1 776.64 45 output signal w
a44_restore_port {DOUT_SL[3]} metal2 0 710.95 1 711.33 46 output signal w
a44_restore_port {DOUT_IE[3]} metal2 0 768.235 1 768.615 47 output signal w
a44_restore_port {DOUT_OE[3]} metal2 0 709.49 1 709.87 48 output signal w
a44_restore_port {DOUT_PU[3]} metal2 0 773.655 1 774.035 49 output signal w
a44_restore_port {DOUT_PD[3]} metal2 0 769.29 1 769.67 50 output signal w
a44_restore_port {DOUT_OUT[3]} metal2 0 710.22 1 710.6 51 output signal w
a44_restore_port {DOUT_PDRV0[3]} metal2 0 772.51 1 772.89 52 output signal w
a44_restore_port {DOUT_PDRV1[3]} metal2 0 771.8 1 772.18 53 output signal w
a44_restore_port {DOUT_IN[3]} metal2 0 708.76 1 709.14 54 input signal w
a44_restore_port {DOUT_CS[2]} metal2 0 876.26 1 876.64 55 output signal w
a44_restore_port {DOUT_SL[2]} metal2 0 810.95 1 811.33 56 output signal w
a44_restore_port {DOUT_IE[2]} metal2 0 868.235 1 868.615 57 output signal w
a44_restore_port {DOUT_OE[2]} metal2 0 809.49 1 809.87 58 output signal w
a44_restore_port {DOUT_PU[2]} metal2 0 873.655 1 874.035 59 output signal w
a44_restore_port {DOUT_PD[2]} metal2 0 869.29 1 869.67 60 output signal w
a44_restore_port {DOUT_OUT[2]} metal2 0 810.22 1 810.6 61 output signal w
a44_restore_port {DOUT_PDRV0[2]} metal2 0 872.51 1 872.89 62 output signal w
a44_restore_port {DOUT_PDRV1[2]} metal2 0 871.8 1 872.18 63 output signal w
a44_restore_port {DOUT_IN[2]} metal2 0 808.76 1 809.14 64 input signal w
a44_restore_port {DOUT_CS[1]} metal2 0 976.26 1 976.64 65 output signal w
a44_restore_port {DOUT_SL[1]} metal2 0 910.95 1 911.33 66 output signal w
a44_restore_port {DOUT_IE[1]} metal2 0 968.235 1 968.615 67 output signal w
a44_restore_port {DOUT_OE[1]} metal2 0 909.49 1 909.87 68 output signal w
a44_restore_port {DOUT_PU[1]} metal2 0 973.655 1 974.035 69 output signal w
a44_restore_port {DOUT_PD[1]} metal2 0 969.29 1 969.67 70 output signal w
a44_restore_port {DOUT_OUT[1]} metal2 0 910.22 1 910.6 71 output signal w
a44_restore_port {DOUT_PDRV0[1]} metal2 0 972.51 1 972.89 72 output signal w
a44_restore_port {DOUT_PDRV1[1]} metal2 0 971.8 1 972.18 73 output signal w
a44_restore_port {DOUT_IN[1]} metal2 0 908.76 1 909.14 74 input signal w
a44_restore_port {DOUT_CS[0]} metal2 0 1076.26 1 1076.64 75 output signal w
a44_restore_port {DOUT_SL[0]} metal2 0 1010.95 1 1011.33 76 output signal w
a44_restore_port {DOUT_IE[0]} metal2 0 1068.235 1 1068.615 77 output signal w
a44_restore_port {DOUT_OE[0]} metal2 0 1009.49 1 1009.87 78 output signal w
a44_restore_port {DOUT_PU[0]} metal2 0 1073.655 1 1074.035 79 output signal w
a44_restore_port {DOUT_PD[0]} metal2 0 1069.29 1 1069.67 80 output signal w
a44_restore_port {DOUT_OUT[0]} metal2 0 1010.22 1 1010.6 81 output signal w
a44_restore_port {DOUT_PDRV0[0]} metal2 0 1072.51 1 1072.89 82 output signal w
a44_restore_port {DOUT_PDRV1[0]} metal2 0 1071.8 1 1072.18 83 output signal w
a44_restore_port {DOUT_IN[0]} metal2 0 1008.76 1 1009.14 84 input signal w
a44_restore_port {VREFN} metal2 87.12 1109 89.66 1110 85 inout signal n
a44_restore_port {VINN} metal2 187.12 1109 189.66 1110 86 inout signal n
a44_restore_port {VINP} metal2 287.12 1109 289.66 1110 87 inout signal n
a44_restore_port {VREFP} metal2 387.12 1109 389.66 1110 88 inout signal n
property FIXED_BBOX {0 0 22200 22200}
save A44_A
