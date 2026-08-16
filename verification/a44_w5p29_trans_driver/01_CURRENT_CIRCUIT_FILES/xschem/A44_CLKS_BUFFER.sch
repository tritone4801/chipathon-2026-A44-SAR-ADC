v {xschem version=3.4.8RC file_version=1.3}
G {}
K {type=subcircuit
format="@name @pinlist A44_CLKS_BUFFER"
template="name=x1"
}
V {}
S {}
F {}
E {}
N 300 130 300 200 {lab=INTER_PAD}
N 200 100 260 100 {lab=PAD_CLK}
N 300 20 300 70 {lab=VDD}
N 300 260 300 330 {lab=GND}
N 200 100 200 230 {lab=PAD_CLK}
N 200 230 260 230 {lab=PAD_CLK}
N 140 160 200 160 {lab=PAD_CLK}
N 300 100 330 100 {lab=VDD}
N 330 50 330 100 {lab=VDD}
N 300 50 330 50 {lab=VDD}
N 300 230 330 230 {lab=GND}
N 330 230 330 290 {lab=GND}
N 300 290 330 290 {lab=GND}
N 300 160 390 160 {lab=INTER_PAD}
N 600 130 600 200 {lab=CLKS_CORE}
N 500 100 560 100 {lab=INTER_PAD}
N 600 20 600 70 {lab=VDD}
N 600 260 600 330 {lab=GND}
N 500 100 500 230 {lab=INTER_PAD}
N 500 230 560 230 {lab=INTER_PAD}
N 440 160 500 160 {lab=INTER_PAD}
N 600 100 630 100 {lab=VDD}
N 630 50 630 100 {lab=VDD}
N 600 50 630 50 {lab=VDD}
N 600 230 630 230 {lab=GND}
N 630 230 630 290 {lab=GND}
N 600 290 630 290 {lab=GND}
N 600 160 690 160 {lab=CLKS_CORE}
N 390 160 440 160 {lab=INTER_PAD}
C {symbols/nfet_03v3.sym} 280 230 0 0 {name=CLK_INV1_NMOS
L=0.28u
W=0.78u
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
C {symbols/pfet_03v3.sym} 280 100 0 0 {name=CLK_INV1_PMOS
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
C {lab_wire.sym} 300 30 0 0 {name=p8 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 300 320 0 0 {name=p9 sig_type=std_logic lab=GND}
C {symbols/nfet_03v3.sym} 580 230 0 0 {name=CLK_INV2_NMOS
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
C {symbols/pfet_03v3.sym} 580 100 0 0 {name=CLK_INV2_PMOS
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
C {lab_wire.sym} 600 30 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 600 320 0 0 {name=p2 sig_type=std_logic lab=GND}
C {ipin.sym} 140 160 0 0 {name=p5 lab=PAD_CLK}
C {opin.sym} 690 160 0 0 {name=p6 lab=CLKS_CORE}
C {iopin.sym} -170 110 0 0 {name=p3 lab=VDD}
C {iopin.sym} -170 150 0 0 {name=p4 lab=GND}
C {lab_wire.sym} 430 160 0 0 {name=p7 sig_type=std_logic lab=INTER_PAD}
