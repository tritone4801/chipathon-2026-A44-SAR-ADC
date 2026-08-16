v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
T {TRUE CLOCK: 4 stages, CLKS -> N_CLK} -330 610 0 0 0.2 0.2 {}
T {1.56/3.11 -> 2.34/4.67 -> 3.11/6.22 -> 4.67/9.33 um} -330 640 0 0 0.18 0.18 {}
T {COMPLEMENT CLOCK: 3 stages, CLKS -> P_CLK} -330 200 0 0 0.2 0.2 {}
T {1.56/3.11 -> 3.11/6.22 -> 6.22/12.44 um} -330 230 0 0 0.18 0.18 {}
T {TG_M7: 7 matched unit TG per side} 610 -520 0 0 0.2 0.2 {}
T {unit MN=3.11/0.28, MP=6.22/0.28; total 21.77/43.54 um} 610 -490 0 0 0.18 0.18 {}
N -160 360 -160 430 {lab=#net1}
N -260 330 -200 330 {lab=CLKS}
N -160 250 -160 300 {lab=VDD}
N -160 490 -160 560 {lab=GND}
N -260 330 -260 460 {lab=CLKS}
N -260 460 -200 460 {lab=CLKS}
N -320 390 -260 390 {lab=CLKS}
N -160 330 -130 330 {lab=VDD}
N -130 280 -130 330 {lab=VDD}
N -160 280 -130 280 {lab=VDD}
N -160 460 -130 460 {lab=GND}
N -130 460 -130 520 {lab=GND}
N -160 520 -130 520 {lab=GND}
N -160 390 -70 390 {lab=#net1}
N 90 360 90 430 {lab=#net2}
N -10 330 50 330 {lab=#net1}
N 90 250 90 300 {lab=VDD}
N 90 490 90 560 {lab=GND}
N -10 330 -10 460 {lab=#net1}
N -10 460 50 460 {lab=#net1}
N -70 390 -10 390 {lab=#net1}
N 90 330 120 330 {lab=VDD}
N 120 280 120 330 {lab=VDD}
N 90 280 120 280 {lab=VDD}
N 90 460 120 460 {lab=GND}
N 120 460 120 520 {lab=GND}
N 90 520 120 520 {lab=GND}
N 90 390 180 390 {lab=#net2}
N 340 360 340 430 {lab=#net3}
N 240 330 300 330 {lab=#net2}
N 340 250 340 300 {lab=VDD}
N 340 490 340 560 {lab=GND}
N 240 330 240 460 {lab=#net2}
N 240 460 300 460 {lab=#net2}
N 180 390 240 390 {lab=#net2}
N 340 330 370 330 {lab=VDD}
N 370 280 370 330 {lab=VDD}
N 340 280 370 280 {lab=VDD}
N 340 460 370 460 {lab=GND}
N 370 460 370 520 {lab=GND}
N 340 520 370 520 {lab=GND}
N 340 390 430 390 {lab=#net3}
N 590 360 590 430 {lab=N_CLK}
N 490 330 550 330 {lab=#net3}
N 590 250 590 300 {lab=VDD}
N 590 490 590 560 {lab=GND}
N 490 330 490 460 {lab=#net3}
N 490 460 550 460 {lab=#net3}
N 430 390 490 390 {lab=#net3}
N 590 330 620 330 {lab=VDD}
N 620 280 620 330 {lab=VDD}
N 590 280 620 280 {lab=VDD}
N 590 460 620 460 {lab=GND}
N 620 460 620 520 {lab=GND}
N 590 520 620 520 {lab=GND}
N 590 390 680 390 {lab=N_CLK}
N -150 -40 -150 30 {lab=#net4}
N -250 -70 -190 -70 {lab=CLKS}
N -150 -150 -150 -100 {lab=VDD}
N -150 90 -150 160 {lab=GND}
N -250 -70 -250 60 {lab=CLKS}
N -250 60 -190 60 {lab=CLKS}
N -310 -10 -250 -10 {lab=CLKS}
N -150 -70 -120 -70 {lab=VDD}
N -120 -120 -120 -70 {lab=VDD}
N -150 -120 -120 -120 {lab=VDD}
N -150 60 -120 60 {lab=GND}
N -120 60 -120 120 {lab=GND}
N -150 120 -120 120 {lab=GND}
N -150 -10 -60 -10 {lab=#net4}
N 100 -40 100 30 {lab=#net5}
N 20 -70 60 -70 {lab=#net4}
N 100 -150 100 -100 {lab=VDD}
N 100 90 100 160 {lab=GND}
N 20 -70 20 60 {lab=#net4}
N 20 60 60 60 {lab=#net4}
N -60 -10 20 -10 {lab=#net4}
N 100 -70 130 -70 {lab=VDD}
N 130 -120 130 -70 {lab=VDD}
N 100 -120 130 -120 {lab=VDD}
N 100 60 130 60 {lab=GND}
N 130 60 130 120 {lab=GND}
N 100 120 130 120 {lab=GND}
N 100 -10 190 -10 {lab=#net5}
N 350 -40 350 30 {lab=P_CLK}
N 270 -70 310 -70 {lab=#net5}
N 350 -150 350 -100 {lab=VDD}
N 350 90 350 160 {lab=GND}
N 270 -70 270 60 {lab=#net5}
N 270 60 310 60 {lab=#net5}
N 190 -10 270 -10 {lab=#net5}
N 350 -70 380 -70 {lab=VDD}
N 380 -120 380 -70 {lab=VDD}
N 350 -120 380 -120 {lab=VDD}
N 350 60 380 60 {lab=GND}
N 380 60 380 120 {lab=GND}
N 350 120 380 120 {lab=GND}
N 350 -10 440 -10 {lab=P_CLK}
N -390 -10 -310 -10 {lab=CLKS}
N -390 -10 -390 390 {lab=CLKS}
N -390 390 -320 390 {lab=CLKS}
N -570 170 -390 170 {lab=CLKS}
N 700 -360 770 -360 {lab=VIN}
N 700 -360 700 -160 {lab=VIN}
N 700 -160 770 -160 {lab=VIN}
N 830 -360 890 -360 {lab=VOUT}
N 890 -360 890 -160 {lab=VOUT}
N 830 -160 890 -160 {lab=VOUT}
N 800 -360 800 -310 {lab=VDD}
N 800 -220 800 -160 {lab=GND}
N 800 -430 800 -400 {lab=P_CLK}
N 800 -120 800 -60 {lab=N_CLK}
N 600 -270 700 -270 {lab=VIN}
N 890 -270 990 -270 {lab=VOUT}
C {symbols/nfet_03v3.sym} -180 460 0 0 {name=TG_CLK_INV1_NMOS
L=0.28u
W=1.56u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} -180 330 0 0 {name=TG_CLK_INV1_PMOS
L=0.28u
W=3.11u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 70 460 0 0 {name=TG_CLK_INV2_NMOS
L=0.28u
W=2.34u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 70 330 0 0 {name=TG_CLK_INV2_PMOS
L=0.28u
W=4.67u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 320 460 0 0 {name=TG_CLK_INV3_NMOS
L=0.28u
W=3.11u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 320 330 0 0 {name=TG_CLK_INV3_PMOS
L=0.28u
W=6.22u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 570 460 0 0 {name=TG_CLK_INV4_NMOS
L=0.28u
W=4.67u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 570 330 0 0 {name=TG_CLK_INV4_PMOS
L=0.28u
W=9.33u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} -170 60 0 0 {name=TG_PCLK_INV1_NMOS
L=0.28u
W=1.56u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} -170 -70 0 0 {name=TG_PCLK_INV1_PMOS
L=0.28u
W=3.11u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 80 60 0 0 {name=TG_PCLK_INV2_NMOS
L=0.28u
W=3.11u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 80 -70 0 0 {name=TG_PCLK_INV2_PMOS
L=0.28u
W=6.22u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 330 60 0 0 {name=TG_PCLK_INV3_NMOS
L=0.28u
W=6.22u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 330 -70 0 0 {name=TG_PCLK_INV3_PMOS
L=0.28u
W=12.44u
nf=1
m=1
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 800 -140 3 0 {name=TG_TRANS_NMOS
L=0.28u
W=3.11u
nf=1
m=8
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 800 -380 1 0 {name=TG_TRANS_PMOS
L=0.28u
W=6.22u
nf=1
m=8
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {lab_wire.sym} -160 260 0 0 {name=p4 sig_type=std_logic lab=VDD}
C {lab_wire.sym} -160 550 0 0 {name=p5 sig_type=std_logic lab=GND}
C {lab_wire.sym} 90 260 0 0 {name=p6 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 90 550 0 0 {name=p7 sig_type=std_logic lab=GND}
C {lab_wire.sym} 340 260 0 0 {name=p8 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 340 550 0 0 {name=p9 sig_type=std_logic lab=GND}
C {lab_wire.sym} 590 260 0 0 {name=p10 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 590 550 0 0 {name=p11 sig_type=std_logic lab=GND}
C {lab_wire.sym} -150 -140 0 0 {name=p12 sig_type=std_logic lab=VDD}
C {lab_wire.sym} -150 150 0 0 {name=p13 sig_type=std_logic lab=GND}
C {lab_wire.sym} 100 -140 0 0 {name=p14 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 100 150 0 0 {name=p15 sig_type=std_logic lab=GND}
C {lab_wire.sym} 350 -140 0 0 {name=p16 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 350 150 0 0 {name=p17 sig_type=std_logic lab=GND}
C {lab_wire.sym} 650 390 0 0 {name=p18 sig_type=std_logic lab=N_CLK}
C {lab_wire.sym} 410 -10 0 0 {name=p19 sig_type=std_logic lab=P_CLK}
C {lab_wire.sym} 800 -420 0 0 {name=p20 sig_type=std_logic lab=P_CLK}
C {lab_wire.sym} 800 -80 0 0 {name=p21 sig_type=std_logic lab=N_CLK}
C {lab_wire.sym} 800 -320 0 0 {name=p22 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 800 -200 0 0 {name=p23 sig_type=std_logic lab=GND}
C {iopin.sym} -830 40 0 0 {name=p24 lab=VDD}
C {iopin.sym} -830 80 0 0 {name=p25 lab=GND}
C {ipin.sym} 600 -270 0 0 {name=p26 lab=VIN}
C {ipin.sym} -570 170 0 0 {name=p27 lab=CLKS}
C {opin.sym} 990 -270 0 0 {name=p28 lab=VOUT}
