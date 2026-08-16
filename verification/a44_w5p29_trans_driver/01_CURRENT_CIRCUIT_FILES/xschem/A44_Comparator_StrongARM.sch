v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 150 120 260 120 {lab=CLK}
N 300 40 300 90 {lab=#net1}
N 120 40 300 40 {lab=#net1}
N 120 20 120 40 {lab=#net1}
N 120 -110 120 -40 {lab=XP}
N 110 -110 120 -110 {lab=XP}
N 110 -120 110 -110 {lab=XP}
N 400 -120 400 -100 {lab=XN}
N -210 -120 -210 -90 {lab=XP}
N -210 -90 120 -90 {lab=XP}
N 660 -130 660 -80 {lab=XN}
N 410 -80 660 -80 {lab=XN}
N -210 -410 -210 -330 {lab=VDD}
N 650 -410 650 -320 {lab=VDD}
N -210 -410 650 -410 {lab=VDD}
N 110 -410 110 -320 {lab=VDD}
N 390 -410 390 -310 {lab=VDD}
N 110 -260 110 -180 {lab=LP}
N 390 -250 390 -180 {lab=LN}
N 390 -180 400 -180 {lab=LN}
N -300 -300 -250 -300 {lab=CLK}
N -300 -300 -300 -150 {lab=CLK}
N -300 -150 -250 -150 {lab=CLK}
N 690 -290 750 -290 {lab=CLK}
N 750 -290 750 -160 {lab=CLK}
N 700 -160 750 -160 {lab=CLK}
N 750 -290 820 -290 {lab=CLK}
N -370 -300 -300 -300 {lab=CLK}
N 150 -290 190 -290 {lab=LN}
N 190 -290 190 -150 {lab=LN}
N 150 -150 190 -150 {lab=LN}
N 290 -280 350 -280 {lab=LP}
N 290 -280 290 -150 {lab=LP}
N 290 -150 360 -150 {lab=LP}
N 190 -240 390 -240 {lab=LN}
N 110 -210 290 -210 {lab=LP}
N -210 -270 -210 -200 {lab=LP}
N -210 -200 110 -200 {lab=LP}
N 650 -260 650 -230 {lab=LN}
N 390 -230 650 -230 {lab=LN}
N 540 -190 660 -190 {lab=VDD}
N 540 -410 540 -190 {lab=VDD}
N -210 -180 -80 -180 {lab=VDD}
N -80 -410 -80 -180 {lab=VDD}
N 300 150 300 210 {lab=GND}
N -210 -150 -150 -150 {lab=VDD}
N -150 -410 -150 -150 {lab=VDD}
N -210 -300 -150 -300 {lab=VDD}
N 50 -150 110 -150 {lab=GND}
N 50 -290 110 -290 {lab=VDD}
N 400 -150 470 -150 {lab=GND}
N 390 -280 470 -280 {lab=VDD}
N 540 -160 660 -160 {lab=VDD}
N 540 -190 540 -160 {lab=VDD}
N 540 -290 650 -290 {lab=VDD}
N 300 120 320 120 {lab=GND}
N 320 120 320 180 {lab=GND}
N 300 180 320 180 {lab=GND}
N 400 -100 400 -50 {lab=XN}
N 400 -80 410 -80 {lab=XN}
N 400 10 400 40 {lab=#net1}
N 300 40 400 40 {lab=#net1}
N 330 -20 400 -20 {lab=GND}
N 320 -20 330 -20 {lab=GND}
N 320 -20 320 120 {lab=GND}
N 120 -10 320 -10 {lab=GND}
N 980 190 1030 190 {lab=LN}
N 980 190 980 290 {lab=LN}
N 980 290 1030 290 {lab=LN}
N 1070 220 1070 260 {lab=DCMPN}
N 1070 240 1180 240 {lab=DCMPN}
N 1070 110 1070 160 {lab=VDD}
N 1070 320 1070 370 {lab=GND}
N 1070 290 1120 290 {lab=GND}
N 1120 290 1120 340 {lab=GND}
N 1070 340 1120 340 {lab=GND}
N 1070 190 1130 190 {lab=VDD}
N 1130 140 1130 190 {lab=VDD}
N 1070 140 1130 140 {lab=VDD}
N 910 230 980 230 {lab=LN}
N 990 -180 1040 -180 {lab=LP}
N 990 -180 990 -80 {lab=LP}
N 990 -80 1040 -80 {lab=LP}
N 1080 -150 1080 -110 {lab=DCMPP}
N 1080 -130 1190 -130 {lab=DCMPP}
N 1080 -260 1080 -210 {lab=VDD}
N 1080 -50 1080 0 {lab=GND}
N 1080 -80 1130 -80 {lab=GND}
N 1130 -80 1130 -30 {lab=GND}
N 1080 -30 1130 -30 {lab=GND}
N 1080 -180 1140 -180 {lab=VDD}
N 1140 -230 1140 -180 {lab=VDD}
N 1080 -230 1140 -230 {lab=VDD}
N 920 -140 990 -140 {lab=LP}
N 10 -10 80 -10 {lab=VINP}
N 440 -20 540 -20 {lab=VINN}
N 50 -410 50 -290 {lab=VDD}
N 470 -410 470 -280 {lab=VDD}
C {symbols/nfet_03v3.sym} 280 120 0 0 {name=COMP_TAIL
L=0.28u
W=1.56u
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
C {symbols/pfet_03v3.sym} -230 -150 0 0 {name=COMP_RESET_L_BOT
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
model=pfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 100 -10 0 0 {name=COMP_INPUT_P
L=0.28u
W=55.8u
nf=1
m=4
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 420 -20 2 0 {name=COMP_INPUT_N
L=0.28u
W=55.8u
nf=1
m=4
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/nfet_03v3.sym} 130 -150 2 0 {name=COMP_LATCH_L_BOT
L=0.28u
W=8.2524u
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
C {symbols/nfet_03v3.sym} 380 -150 0 0 {name=COMP_LATCH_R_BOT
L=0.28u
W=8.2524u
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
C {symbols/pfet_03v3.sym} -230 -300 0 0 {name=COMP_RESET_L_UP
L=0.28u
W=16.8587u
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
C {symbols/pfet_03v3.sym} 130 -290 2 0 {name=COMP_LATCH_L_UP
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
C {symbols/pfet_03v3.sym} 370 -280 0 0 {name=COMP_LATCH_R_UP
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
C {symbols/pfet_03v3.sym} 680 -160 2 0 {name=COMP_RESET_R_BOT
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
model=pfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 670 -290 2 0 {name=COMP_RESET_R_UP
L=0.28u
W=16.8587u
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
C {symbols/pfet_03v3.sym} 1050 190 0 0 {name=COMP_LN_INV_PMOS
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
C {symbols/nfet_03v3.sym} 1050 290 0 0 {name=COMP_LN_INV_NMOS
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
C {ipin.sym} -300 150 0 0 {name=p1 lab=CLK}
C {ipin.sym} -300 190 0 0 {name=p2 lab=VINP}
C {ipin.sym} -300 230 0 0 {name=p3 lab=VINN}
C {opin.sym} -220 150 0 0 {name=p6 lab=DCMPP}
C {opin.sym} -220 190 0 0 {name=p7 lab=DCMPN}
C {iopin.sym} -250 290 0 0 {name=p8 lab=VDD}
C {iopin.sym} -250 320 0 0 {name=p9 lab=GND}
C {symbols/pfet_03v3.sym} 1060 -180 0 0 {name=COMP_LP_INV_PMOS
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
C {symbols/nfet_03v3.sym} 1060 -80 0 0 {name=COMP_LP_INV_NMOS
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
C {lab_wire.sym} 220 120 0 0 {name=p4 sig_type=std_logic lab=CLK}
C {lab_wire.sym} 300 210 0 0 {name=p5 sig_type=std_logic lab=GND}
C {lab_wire.sym} 50 -10 0 0 {name=p10 sig_type=std_logic lab=VINP}
C {lab_wire.sym} 500 -20 0 0 {name=p11 sig_type=std_logic lab=VINN}
C {lab_wire.sym} -340 -300 0 0 {name=p12 sig_type=std_logic lab=CLK}
C {lab_wire.sym} 790 -290 0 0 {name=p13 sig_type=std_logic lab=CLK}
C {lab_wire.sym} 250 -410 0 0 {name=p14 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 110 -220 0 0 {name=p15 sig_type=std_logic lab=LP}
C {lab_wire.sym} 390 -210 0 0 {name=p16 sig_type=std_logic lab=LN}
C {lab_wire.sym} -60 -90 0 0 {name=p17 sig_type=std_logic lab=XP}
C {lab_wire.sym} 540 -80 0 0 {name=p18 sig_type=std_logic lab=XN}
C {lab_wire.sym} 940 230 0 0 {name=p19 sig_type=std_logic lab=LN}
C {lab_wire.sym} 1070 120 0 0 {name=p20 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1070 370 0 0 {name=p21 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1150 240 0 0 {name=p22 sig_type=std_logic lab=DCMPN}
C {lab_wire.sym} 1140 -130 0 0 {name=p23 sig_type=std_logic lab=DCMPP}
C {lab_wire.sym} 1080 -10 0 0 {name=p24 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1080 -250 0 0 {name=p25 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 950 -140 0 0 {name=p26 sig_type=std_logic lab=LP}
C {lab_wire.sym} 80 -150 0 0 {name=p27 sig_type=std_logic lab=GND}
C {lab_wire.sym} 460 -150 0 0 {name=p28 sig_type=std_logic lab=GND}
