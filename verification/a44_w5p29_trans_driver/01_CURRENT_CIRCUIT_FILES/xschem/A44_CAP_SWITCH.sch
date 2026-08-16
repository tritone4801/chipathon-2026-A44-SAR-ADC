v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 160 170 210 170 {lab=CTRL}
N 160 170 160 360 {lab=CTRL}
N 160 360 210 360 {lab=CTRL}
N 100 260 160 260 {lab=CTRL}
N 250 200 250 330 {lab=CAP_BOTTOM}
N 250 80 250 140 {lab=VREFP}
N 250 390 250 460 {lab=VREFN}
N 250 260 420 260 {lab=CAP_BOTTOM}
N 250 170 320 170 {lab=VDD}
N 250 360 330 360 {lab=GND}
C {symbols/nfet_03v3.sym} 230 360 0 0 {name=CAP_REFN_SWITCH_NMOS
L=0.28u
W=1.56u
nf=1
m=18
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=nfet_03v3
spiceprefix=X
}
C {symbols/pfet_03v3.sym} 230 170 0 0 {name=CAP_REFP_SWITCH_PMOS
L=0.28u
W=1.56u
nf=1
m=18
ad="'int((nf+1)/2) * W/nf * 0.18u'"
pd="'2*int((nf+1)/2) * (W/nf + 0.18u)'"
as="'int((nf+2)/2) * W/nf * 0.18u'"
ps="'2*int((nf+2)/2) * (W/nf + 0.18u)'"
nrd="'0.18u / W'" nrs="'0.18u / W'"
sa=0 sb=0 sd=0
model=pfet_03v3
spiceprefix=X
}
C {lab_wire.sym} 250 110 0 0 {name=p8 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 250 440 0 0 {name=p9 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 330 360 0 0 {name=p10 sig_type=std_logic lab=GND}
C {lab_wire.sym} 310 170 0 0 {name=p11 sig_type=std_logic lab=VDD}
C {iopin.sym} -140 190 0 0 {name=p2 lab=VREFP}
C {iopin.sym} -140 230 0 0 {name=p3 lab=VREFN}
C {ipin.sym} 100 260 0 0 {name=p4 lab=CTRL}
C {opin.sym} 420 260 0 0 {name=p5 lab=CAP_BOTTOM}
C {iopin.sym} -140 280 0 0 {name=p1 lab=VDD}
C {iopin.sym} -140 320 0 0 {name=p6 lab=GND}
