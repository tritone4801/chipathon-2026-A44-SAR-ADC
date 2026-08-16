v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 2060 -560 2060 0 {lab=VTOP}
N 1600 -560 1600 0 {lab=VTOP}
N 1080 -560 1080 0 {lab=VTOP}
N 630 -560 630 0 {lab=VTOP}
N 170 -560 170 0 {lab=VTOP}
N -350 -560 -350 0 {lab=VTOP}
N 2940 -560 2940 -370 {lab=VTOP}
N -800 -560 2940 -560 {lab=VTOP}
N 2940 -310 2940 -170 {lab=GND}
N -980 -670 -980 -610 {lab=VDD}
N -910 -670 -910 -610 {lab=GND}
N -1190 -550 -1100 -550 {lab=VIN}
N -1140 -570 -1100 -570 {lab=CLKS}
N -1140 -620 -1140 -570 {lab=CLKS}
N 2940 -560 3150 -560 {lab=VTOP}
N 2580 260 2580 340 {lab=DCTRL_DRV[1]}
N 2660 110 2710 110 {lab=VDD}
N 2660 150 2710 150 {lab=GND}
N 2430 70 2490 70 {lab=VREFP}
N 2430 170 2490 170 {lab=VREFN}
N 2060 260 2060 340 {lab=DCTRL_DRV[2]}
N 2140 110 2190 110 {lab=VDD}
N 2140 150 2190 150 {lab=GND}
N 1910 70 1970 70 {lab=VREFP}
N 1910 170 1970 170 {lab=VREFN}
N 1600 260 1600 340 {lab=DCTRL_DRV[3]}
N 1680 110 1730 110 {lab=VDD}
N 1680 150 1730 150 {lab=GND}
N 1450 70 1510 70 {lab=VREFP}
N 1450 170 1510 170 {lab=VREFN}
N 1080 260 1080 340 {lab=DCTRL_DRV[4]}
N 1160 110 1210 110 {lab=VDD}
N 1160 150 1210 150 {lab=GND}
N 930 70 990 70 {lab=VREFP}
N 930 170 990 170 {lab=VREFN}
N 630 260 630 340 {lab=DCTRL_DRV[5]}
N 710 110 760 110 {lab=VDD}
N 710 150 760 150 {lab=GND}
N 480 70 540 70 {lab=VREFP}
N 480 170 540 170 {lab=VREFN}
N 170 260 170 340 {lab=DCTRL_DRV[6]}
N 250 110 300 110 {lab=VDD}
N 250 150 300 150 {lab=GND}
N 20 70 80 70 {lab=VREFP}
N 20 170 80 170 {lab=VREFN}
N -350 260 -350 340 {lab=DCTRL_DRV[7]}
N -270 110 -220 110 {lab=VDD}
N -270 150 -220 150 {lab=GND}
N -500 70 -440 70 {lab=VREFP}
N -500 170 -440 170 {lab=VREFN}
N 2580 -560 2580 0 {lab=VTOP}
C {ipin.sym} -1170 -310 0 0 {name=p1 lab=VIN}
C {ipin.sym} -1170 -280 0 0 {name=p2 lab=CLKS}
C {iopin.sym} -1280 -160 0 0 {name=p3 lab=VDD}
C {iopin.sym} -1280 -140 0 0 {name=p4 lab=GND}
C {iopin.sym} -1200 -160 0 0 {name=p5 lab=VREFP}
C {iopin.sym} -1200 -130 0 0 {name=p6 lab=VREFN}
C {iopin.sym} -1070 -280 0 0 {name=p7 lab=VTOP}
C {lab_wire.sym} 2470 70 0 0 {name=p8 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 2470 170 0 0 {name=p9 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 2690 150 0 0 {name=p10 sig_type=std_logic lab=GND}
C {lab_wire.sym} 2690 110 0 0 {name=p11 sig_type=std_logic lab=VDD}
C {ipin.sym} -1170 -240 0 0 {name=p12 lab=DCTRL[7:1]}
C {lab_wire.sym} 2580 310 0 0 {name=p13 sig_type=std_logic lab=DCTRL_DRV[1]}
C {symbols/cap_mim_analog.sym} 2940 -340 0 0 {name=C8
W=6.855e-6
L=6.855e-6
model=cap_mim_2f0_m4m5_noshield
spiceprefix=X
m=18}
C {lab_wire.sym} 2940 -230 0 0 {name=p51 sig_type=std_logic lab=GND}
C {lab_wire.sym} -980 -640 0 0 {name=p52 sig_type=std_logic lab=VDD}
C {lab_wire.sym} -910 -640 0 0 {name=p53 sig_type=std_logic lab=GND}
C {lab_wire.sym} -1140 -590 0 0 {name=p54 sig_type=std_logic lab=CLKS}
C {lab_wire.sym} -1150 -550 0 0 {name=p55 sig_type=std_logic lab=VIN}
C {lab_wire.sym} 3070 -560 0 0 {name=p56 sig_type=std_logic lab=VTOP}
C {A44_C1_SWITCH.sym} 2600 180 0 0 {name=x2}
C {lab_wire.sym} 1950 70 0 0 {name=p15 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 1950 170 0 0 {name=p16 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 2170 150 0 0 {name=p17 sig_type=std_logic lab=GND}
C {lab_wire.sym} 2170 110 0 0 {name=p18 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 2060 310 0 0 {name=p19 sig_type=std_logic lab=DCTRL_DRV[2]}
C {lab_wire.sym} 1490 70 0 0 {name=p21 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 1490 170 0 0 {name=p22 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 1710 150 0 0 {name=p23 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1710 110 0 0 {name=p24 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1600 310 0 0 {name=p25 sig_type=std_logic lab=DCTRL_DRV[3]}
C {lab_wire.sym} 970 70 0 0 {name=p27 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 970 170 0 0 {name=p28 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 1190 150 0 0 {name=p29 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1190 110 0 0 {name=p30 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1080 310 0 0 {name=p31 sig_type=std_logic lab=DCTRL_DRV[4]}
C {lab_wire.sym} 520 70 0 0 {name=p33 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 520 170 0 0 {name=p34 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 740 150 0 0 {name=p35 sig_type=std_logic lab=GND}
C {lab_wire.sym} 740 110 0 0 {name=p36 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 630 310 0 0 {name=p37 sig_type=std_logic lab=DCTRL_DRV[5]}
C {lab_wire.sym} 60 70 0 0 {name=p39 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 60 170 0 0 {name=p40 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 280 150 0 0 {name=p41 sig_type=std_logic lab=GND}
C {lab_wire.sym} 280 110 0 0 {name=p42 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 170 310 0 0 {name=p43 sig_type=std_logic lab=DCTRL_DRV[6]}
C {lab_wire.sym} -460 70 0 0 {name=p45 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} -460 170 0 0 {name=p46 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} -240 150 0 0 {name=p47 sig_type=std_logic lab=GND}
C {lab_wire.sym} -240 110 0 0 {name=p48 sig_type=std_logic lab=VDD}
C {lab_wire.sym} -350 310 0 0 {name=p49 sig_type=std_logic lab=DCTRL_DRV[7]}
C {A44_C2_SWITCH.sym} 2080 180 0 0 {name=x3}
C {A44_C4_SWITCH.sym} 1620 180 0 0 {name=x4}
C {A44_C8_SWITCH.sym} 1100 180 0 0 {name=x5}
C {A44_C16_SWITCH.sym} 650 180 0 0 {name=x6}
C {A44_C64_SWITCH.sym} -330 180 0 0 {name=x8}
C {A44_SWITCH_TRANS_TG8.sym} -950 -560 0 0 {name=xsample
schematic=A44_SWITCH_TRANS_TG8.sch}
C {A44_C32_SWITCH.sym} 190 180 0 0 {name=x1}
C {A44_CONVERSION_BUFFER.sym} 1000 600 0 0 {name=xdrv
schematic=A44_CONVERSION_BUFFER.sch}
C {lab_wire.sym} 1060 490 0 0 {name=p57 sig_type=std_logic lab=DCTRL[1]}
C {lab_wire.sym} 1040 490 0 0 {name=p58 sig_type=std_logic lab=DCTRL[2]}
C {lab_wire.sym} 1020 490 0 0 {name=p59 sig_type=std_logic lab=DCTRL[3]}
C {lab_wire.sym} 1000 490 0 0 {name=p60 sig_type=std_logic lab=DCTRL[4]}
C {lab_wire.sym} 980 490 0 0 {name=p61 sig_type=std_logic lab=DCTRL[5]}
C {lab_wire.sym} 960 490 0 0 {name=p62 sig_type=std_logic lab=DCTRL[6]}
C {lab_wire.sym} 940 490 0 0 {name=p63 sig_type=std_logic lab=DCTRL[7]}
C {lab_wire.sym} 1060 710 0 0 {name=p64 sig_type=std_logic lab=DCTRL_DRV[1]}
C {lab_wire.sym} 1040 710 0 0 {name=p65 sig_type=std_logic lab=DCTRL_DRV[2]}
C {lab_wire.sym} 1020 710 0 0 {name=p66 sig_type=std_logic lab=DCTRL_DRV[3]}
C {lab_wire.sym} 1000 710 0 0 {name=p67 sig_type=std_logic lab=DCTRL_DRV[4]}
C {lab_wire.sym} 980 710 0 0 {name=p68 sig_type=std_logic lab=DCTRL_DRV[5]}
C {lab_wire.sym} 960 710 0 0 {name=p69 sig_type=std_logic lab=DCTRL_DRV[6]}
C {lab_wire.sym} 940 710 0 0 {name=p70 sig_type=std_logic lab=DCTRL_DRV[7]}
C {lab_wire.sym} 1150 570 0 0 {name=p71 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1150 620 0 0 {name=p72 sig_type=std_logic lab=GND}
