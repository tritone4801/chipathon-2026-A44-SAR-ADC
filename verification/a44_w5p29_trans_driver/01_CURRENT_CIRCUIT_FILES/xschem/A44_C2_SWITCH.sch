v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 230 -220 230 -130 {lab=UNIT_OUT}
N 230 130 230 250 {lab=CTRL}
N 310 -420 310 -20 {lab=VDD}
N 310 20 310 420 {lab=GND}
N 510 -220 510 -130 {lab=UNIT_OUT}
N 510 130 510 250 {lab=CTRL}
N 590 -420 590 -20 {lab=VDD}
N 590 20 590 420 {lab=GND}
N 230 -220 930 -220 {lab=UNIT_OUT}
N -170 250 510 250 {lab=CTRL}
N -170 -60 140 -60 {lab=REF_P}
N 60 -210 60 -60 {lab=REF_P}
N 60 -210 420 -210 {lab=REF_P}
N -170 40 140 40 {lab=REF_N}
N 50 40 50 240 {lab=REF_N}
N 50 240 420 240 {lab=REF_N}
N 420 -210 420 -60 {lab=REF_P}
N 420 40 420 240 {lab=REF_N}
N 310 -420 590 -420 {lab=VDD}
N 310 420 590 420 {lab=GND}
C {iopin.sym} -380 -100 0 0 {name=p7 lab=REF_N}
C {iopin.sym} -380 -140 0 0 {name=p8 lab=REF_P}
C {iopin.sym} -380 -10 0 0 {name=p9 lab=VDD}
C {iopin.sym} -380 30 0 0 {name=p10 lab=GND}
C {ipin.sym} -170 250 0 0 {name=p11 lab=CTRL}
C {opin.sym} 930 -220 0 0 {name=p12 lab=UNIT_OUT}
C {A44_C1_SWITCH.sym} 250 50 0 0 {name=x1}
C {A44_C1_SWITCH.sym} 530 50 0 0 {name=x2}
C {lab_wire.sym} -120 -60 0 0 {name=p_refp_r1 sig_type=std_logic lab=REF_P}
C {lab_wire.sym} -120 40 0 0 {name=p_refn_r1 sig_type=std_logic lab=REF_N}
C {lab_wire.sym} 450 -420 0 0 {name=p_vdd_r1 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 450 420 0 0 {name=p_gnd_r1 sig_type=std_logic lab=GND}
