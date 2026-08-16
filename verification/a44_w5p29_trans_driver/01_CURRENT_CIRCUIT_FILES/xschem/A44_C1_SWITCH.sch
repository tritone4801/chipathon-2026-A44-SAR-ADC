v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N -10 90 -10 170 {lab=CTRL}
N -10 -130 -10 -70 {lab=V_BOT}
N -80 -90 -80 -20 {lab=REF_N}
N -80 40 -80 120 {lab=REF_P}
N 60 0 210 -0 {lab=VDD}
N 60 20 210 20 {lab=GND}
N -10 -200 -10 -130 {lab=V_BOT}
N -10 -330 -10 -260 {lab=#net1}
C {A44_CAP_SWITCH.sym} 10 60 0 0 {name=x1
schematic=A44_CAP_SWITCH.sch}
C {lab_wire.sym} 170 0 0 0 {name=p1 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 170 20 0 0 {name=p2 sig_type=std_logic lab=GND}
C {lab_wire.sym} -10 -130 0 0 {name=p3 sig_type=std_logic lab=V_BOT}
C {lab_wire.sym} -80 -90 0 0 {name=p4 sig_type=std_logic lab=REF_N}
C {lab_wire.sym} -80 120 0 0 {name=p5 sig_type=std_logic lab=REF_P}
C {lab_wire.sym} -10 170 0 0 {name=p6 sig_type=std_logic lab=CTRL}
C {iopin.sym} -380 -100 0 0 {name=p7 lab=REF_N}
C {iopin.sym} -380 -60 0 0 {name=p8 lab=REF_P}
C {iopin.sym} -380 -10 0 0 {name=p9 lab=VDD}
C {iopin.sym} -380 30 0 0 {name=p10 lab=GND}
C {ipin.sym} -320 160 0 0 {name=p11 lab=CTRL}
C {opin.sym} -380 110 0 0 {name=p12 lab=UNIT_OUT}
C {symbols/cap_mim_analog.sym} -10 -230 0 0 {name=C1
W=6.855e-6
L=6.855e-6
model=cap_mim_2f0_m4m5_noshield
spiceprefix=X
m=18}
C {lab_wire.sym} -10 -290 0 0 {name=p13 sig_type=std_logic lab=UNIT_OUT}
