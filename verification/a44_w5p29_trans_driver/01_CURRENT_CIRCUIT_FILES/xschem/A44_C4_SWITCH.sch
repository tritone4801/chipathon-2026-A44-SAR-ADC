v {xschem version=3.4.8RC file_version=1.3}
G {}
K {}
V {}
S {}
F {}
E {}
N 230 -220 230 -130 {lab=UNIT_OUT}
N 230 -220 1440 -220 {lab=UNIT_OUT}
N 1020 130 1020 250 {lab=CTRL}
N -170 250 1020 250 {lab=CTRL}
N -170 -60 140 -60 {lab=REF_P}
N -170 40 140 40 {lab=REF_N}
N 510 -220 510 -130 {lab=UNIT_OUT}
N 770 -220 770 -130 {lab=UNIT_OUT}
N 1020 -220 1020 -130 {lab=UNIT_OUT}
N 230 130 230 250 {lab=CTRL}
N 510 130 510 250 {lab=CTRL}
N 770 130 770 250 {lab=CTRL}
N 930 -210 930 -60 {lab=REF_P}
N 60 -210 930 -210 {lab=REF_P}
N 60 -210 60 -60 {lab=REF_P}
N 680 -210 680 -60 {lab=REF_P}
N 420 -210 420 -60 {lab=REF_P}
N 930 40 930 240 {lab=REF_N}
N 50 240 930 240 {lab=REF_N}
N 50 40 50 240 {lab=REF_N}
N 420 40 420 240 {lab=REF_N}
N 680 40 680 240 {lab=REF_N}
N 310 -420 310 -20 {lab=VDD}
N 1100 -420 1100 -20 {lab=VDD}
N 310 -420 1100 -420 {lab=VDD}
N 310 20 310 420 {lab=GND}
N 1100 20 1100 420 {lab=GND}
N 310 420 1100 420 {lab=GND}
N 590 20 590 420 {lab=GND}
N 850 20 850 420 {lab=GND}
N 590 -420 590 -20 {lab=VDD}
N 850 -420 850 -20 {lab=VDD}
C {iopin.sym} -380 -100 0 0 {name=p7 lab=REF_N}
C {iopin.sym} -380 -140 0 0 {name=p8 lab=REF_P}
C {iopin.sym} -380 -10 0 0 {name=p9 lab=VDD}
C {iopin.sym} -380 30 0 0 {name=p10 lab=GND}
C {ipin.sym} -170 250 0 0 {name=p11 lab=CTRL}
C {opin.sym} 1440 -220 0 0 {name=p12 lab=UNIT_OUT}
C {A44_C1_SWITCH.sym} 250 50 0 0 {name=x1}
C {A44_C1_SWITCH.sym} 530 50 0 0 {name=x2}
C {A44_C1_SWITCH.sym} 790 50 0 0 {name=x3}
C {A44_C1_SWITCH.sym} 1040 50 0 0 {name=x4}
C {lab_wire.sym} -120 -60 0 0 {name=p1 sig_type=std_logic lab=REF_P}
C {lab_wire.sym} -120 40 0 0 {name=p2 sig_type=std_logic lab=REF_N}
C {lab_wire.sym} 720 -420 0 0 {name=p3 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 710 420 0 0 {name=p4 sig_type=std_logic lab=GND}
