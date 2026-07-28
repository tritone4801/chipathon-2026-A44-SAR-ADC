v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 660 -690 660 -530 {lab=CLKS}
N 660 -530 700 -530 {lab=CLKS}
N 590 -620 660 -620 {lab=CLKS}
N 740 -730 740 -560 {lab=#net1}
N 740 -510 740 -450 {lab=#net2}
N 740 -450 740 -410 {lab=#net2}
N 740 -410 740 -400 {lab=#net2}
N 740 -400 1150 -400 {lab=#net2}
N 680 -320 830 -320 {lab=CLKSB}
N 870 -400 870 -350 {lab=#net2}
N 870 -290 870 -200 {lab=GND}
N 1200 -400 1300 -400 {lab=VIN}
N 1300 -400 1300 -140 {lab=VIN}
N 1300 -140 1370 -140 {lab=VIN}
N 550 -140 1300 -140 {lab=VIN}
N 1400 -870 1400 -180 {lab=BOTTOM_GATE}
N 1170 -470 1170 -440 {lab=BOTTOM_GATE}
N 1170 -470 1400 -470 {lab=BOTTOM_GATE}
N 1170 -650 1400 -650 {lab=BOTTOM_GATE}
N 1250 -870 1400 -870 {lab=BOTTOM_GATE}
N 1130 -740 1130 -680 {lab=#net1}
N 1130 -740 1220 -740 {lab=#net1}
N 1220 -830 1220 -740 {lab=#net1}
N 660 -760 660 -690 {lab=CLKS}
N 660 -760 700 -760 {lab=CLKS}
N 740 -710 1130 -710 {lab=#net1}
N 870 -870 1190 -870 {lab=#net3}
N 740 -850 740 -790 {lab=VDD}
N 660 -870 810 -870 {lab=VDD}
N 740 -870 740 -850 {lab=VDD}
N 1050 -620 1130 -620 {lab=#net2}
N 1050 -620 1050 -400 {lab=#net2}
N 1400 -980 1400 -860 {lab=BOTTOM_GATE}
N 1400 -870 1610 -870 {lab=BOTTOM_GATE}
N 1670 -870 1790 -870 {lab=#net4}
N 1790 -870 1860 -870 {lab=#net4}
N 1920 -870 2010 -870 {lab=GND}
N 1640 -1000 1640 -910 {lab=VDD}
N 840 -980 970 -980 {lab=BOTTOM_GATE}
N 840 -980 840 -910 {lab=BOTTOM_GATE}
N 220 -670 270 -670 {lab=CLKS}
N 220 -670 220 -520 {lab=CLKS}
N 220 -520 270 -520 {lab=CLKS}
N 150 -610 220 -610 {lab=CLKS}
N 310 -640 310 -550 {lab=CLKSB}
N 310 -600 410 -600 {lab=CLKSB}
N 310 -490 310 -440 {lab=GND}
N 310 -760 310 -700 {lab=VDD}
N 1430 -140 1540 -140 {lab=VOUT}
N 1170 -400 1170 -270 {lab=GND}
N 310 -670 360 -670 {lab=VDD}
N 360 -720 360 -670 {lab=VDD}
N 310 -720 360 -720 {lab=VDD}
N 310 -520 360 -520 {lab=GND}
N 360 -520 360 -480 {lab=GND}
N 310 -480 360 -480 {lab=GND}
N 1400 -140 1400 -30 {lab=GND}
N 740 -530 820 -530 {lab=GND}
N 740 -760 770 -760 {lab=VDD}
N 770 -830 770 -760 {lab=VDD}
N 740 -830 770 -830 {lab=VDD}
N 970 -980 1400 -980 {lab=BOTTOM_GATE}
N 840 -870 840 -820 {lab=#net3}
N 840 -820 920 -820 {lab=#net3}
N 920 -870 920 -820 {lab=#net3}
N 1220 -920 1220 -870 {lab=#net3}
N 1140 -920 1220 -920 {lab=#net3}
N 1140 -920 1140 -870 {lab=#net3}
N 1030 -650 1130 -650 {lab=GND}
N 870 -320 950 -320 {lab=GND}
N 1640 -870 1640 -810 {lab=GND}
N 1640 -810 1890 -810 {lab=GND}
N 1890 -870 1890 -810 {lab=GND}
N 1890 -810 1950 -810 {lab=GND}
N 1950 -870 1950 -810 {lab=GND}
N 950 -320 950 -270 {lab=GND}
N 870 -270 950 -270 {lab=GND}
N 950 -550 950 -400 {lab=#net2}
N 950 -830 950 -610 {lab=#net3}
N 950 -830 1010 -830 {lab=#net3}
N 1010 -870 1010 -830 {lab=#net3}
N 1890 -1000 1890 -910 {lab=CLKSB}
C {ipin.sym} 190 -280 0 0 {name=p1 lab=CLKS}
C {ipin.sym} 550 -140 0 0 {name=p2 lab=VIN}
C {opin.sym} 1540 -140 0 0 {name=p3 lab=VOUT}
C {iopin.sym} 220 -230 0 0 {name=p4 lab=VDD}
C {iopin.sym} 220 -190 0 0 {name=p5 lab=GND}
C {symbols/nfet_06v0.sym} 290 -520 0 0 {name=M1
L=0.70u
W=3.11u
nf=1
m= 2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/pfet_06v0.sym} 290 -670 0 0 {name=M2
L=0.70u
W=3.11u
nf=1
m=2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_06v0
spiceprefix=X
}
C {symbols/nfet_06v0.sym} 720 -530 2 1 {name=M3
L=0.70u
W=3.11u
nf=1
m= 2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/nfet_06v0.sym} 850 -320 0 0 {name=M4
L=0.70u
W=3.11u
nf=1
m= 2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/nfet_06v0.sym} 1170 -420 1 0 {name=M5
L=0.70u
W=3.11u
nf=1
m= 2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/nfet_06v0.sym} 1400 -160 1 0 {name=M7
L=0.70u
W=1.56u
nf=1
m= 10
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/nfet_06v0.sym} 1640 -890 1 0 {name=M8
L=0.70u
W=3.11u
nf=1
m= 2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/nfet_06v0.sym} 1890 -890 1 0 {name=M9
L=0.70u
W=3.11u
nf=1
m= 2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/nfet_06v0.sym} 1150 -650 0 1 {name=M10
L=0.70u
W=3.11u
nf=1
m= 2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_06v0
spiceprefix=X
}
C {symbols/pfet_06v0.sym} 720 -760 0 0 {name=M11
L=0.70u
W=3.11u
nf=1
m=2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_06v0
spiceprefix=X
}
C {symbols/pfet_06v0.sym} 840 -890 1 0 {name=M12
L=0.70u
W=3.11u
nf=1
m=2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_06v0
spiceprefix=X
}
C {symbols/pfet_06v0.sym} 1220 -850 3 0 {name=M13
L=0.70u
W=3.11u
nf=1
m=2
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_06v0
spiceprefix=X
}
C {symbols/cap_mim_analog.sym} 950 -580 0 0 {name=C1
W=3.15e-5
L=3.15e-5
model=cap_mim_2f0_m4m5_noshield
spiceprefix=X
m=1}
C {lab_wire.sym} 190 -610 0 0 {name=p6 sig_type=std_logic lab=CLKS}
C {lab_wire.sym} 310 -730 0 0 {name=p7 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 370 -600 0 0 {name=p8 sig_type=std_logic lab=CLKSB}
C {lab_wire.sym} 310 -460 0 0 {name=p9 sig_type=std_logic lab=GND}
C {lab_wire.sym} 760 -320 0 0 {name=p10 sig_type=std_logic lab=CLKSB}
C {lab_wire.sym} 870 -240 0 0 {name=p11 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1400 -340 0 0 {name=p14 sig_type=std_logic lab=BOTTOM_GATE}
C {lab_wire.sym} 1400 -60 0 0 {name=p15 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1170 -330 0 0 {name=p16 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1070 -650 0 0 {name=p17 sig_type=std_logic lab=GND}
C {lab_wire.sym} 630 -620 0 0 {name=p18 sig_type=std_logic lab=CLKS}
C {lab_wire.sym} 700 -870 0 0 {name=p19 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1640 -950 0 0 {name=p20 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1980 -870 0 0 {name=p24 sig_type=std_logic lab=GND}
C {lab_wire.sym} 790 -530 0 0 {name=p12 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1890 -950 0 0 {name=p13 sig_type=std_logic lab=CLKSB}
