v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
N 220 -120 220 -90 {lab=VDD}
N 220 -30 220 20 {lab=CORE}
N 220 0 270 0 {lab=CORE}
N 170 0 220 0 {lab=CORE}
N 330 -0 380 -0 {lab=PAD}
N 300 -120 300 -20 {lab=VDD}
N 220 -120 300 -120 {lab=VDD}
N 220 80 220 130 {lab=VSS}
C {symbols/diode_pd2nw_06v0.sym} 220 -60 2 0 {name=D1
model=diode_pd2nw_06v0
r_w=10u
r_l=10u
m=4}
C {symbols/ppolyf_u.sym} 300 0 1 0 {name=R1
W=40e-6
L=10e-6
model=ppolyf_u
spiceprefix=X
m=1}
C {iopin.sym} 220 130 2 0 {name=p1 lab=VSS}
C {iopin.sym} 220 -120 2 0 {name=p2 lab=VDD}
C {iopin.sym} 170 0 2 0 {name=p3 lab=CORE}
C {iopin.sym} 380 0 0 0 {name=p4 lab=PAD}
C {symbols/diode_nd2ps_06v0.sym} 220 50 2 0 {name=D2
model=diode_nd2ps_06v0
r_w=10u
r_l=10u
m=4}
T {A44 physical secondary ESD
Official M2 layout: poly W=40 um, L=10 um; body tied to VDD.
Each diode symbol has m=4: four 10 x 10 um diodes per rail.} 20 -230 0 0 0.25 0.25 {}
