v {xschem version=3.4.8RC file_version=1.3}
G {}
K {type=subcircuit
format="@name @pinlist A44_SAR_ADC_TOP_FIXED"
template="name=XTOP"}
V {}
S {}
F {}
E {}
N 1250 60 1500 60 {lab=CMPCK}
N 1250 -40 1250 60 {lab=CMPCK}
N 1370 -130 1500 -130 {lab=DCMPP}
N 1370 -140 1370 -130 {lab=DCMPP}
N 1330 -140 1370 -140 {lab=DCMPP}
N 970 30 970 110 {lab=DCTRLN[7:1]}
N 970 -360 970 -290 {lab=DCTRLP[7:1]}
N 970 -240 970 -140 {lab=VRESP}
N 970 -140 1110 -140 {lab=VRESP}
N 970 -100 970 -20 {lab=VRESN}
N 970 -100 1110 -100 {lab=VRESN}
N 1430 -170 1500 -170 {lab=CLKS_CORE}
N 1900 -110 1970 -110 {lab=DOUT[7:0]}
N 810 60 810 110 {lab=GND}
N 860 60 860 110 {lab=VDD}
N 800 -90 800 -40 {lab=VREFP}
N 860 -90 860 -40 {lab=VREFN}
N 800 -220 800 -160 {lab=VREFP}
N 860 -220 860 -160 {lab=VREFN}
N 810 -370 810 -320 {lab=GND}
N 860 -370 860 -320 {lab=VDD}
N 630 -290 670 -290 {lab=CLKS_CORE}
N 630 30 670 30 {lab=CLKS_CORE}
N 510 -20 670 -20 {lab=VINN}
N 520 -240 670 -240 {lab=VINP}
N 1240 -260 1240 -210 {lab=VDD}
N 1270 -260 1270 -210 {lab=GND}
N 1720 -310 1720 -270 {lab=GND}
N 1800 -310 1800 -270 {lab=VDD}
N 1500 -50 1500 60 {lab=CMPCK}
N 1370 -90 1500 -90 {lab=DCMPN}
N 1370 -100 1370 -90 {lab=DCMPN}
N 1330 -100 1370 -100 {lab=DCMPN}
N 1620 50 1620 110 {lab=DCTRLN[7:1]}
N 1620 -360 1620 -270 {lab=DCTRLP[7:1]}
N 970 -360 1620 -360 {lab=DCTRLP[7:1]}
N 970 110 1620 110 {lab=DCTRLN[7:1]}
N -90 -50 -20 -50 {lab=CLKS}
N 140 -160 140 -110 {lab=VDD}
N 200 -50 330 -50 {lab=CLKS_CORE}
N 140 20 140 60 {lab=GND}
C {iopin.sym} 370 -390 0 0 {name=p1 lab=VDD}
C {iopin.sym} 370 -360 0 0 {name=p2 lab=GND}
C {iopin.sym} 360 -320 0 0 {name=p3 lab=VREFP}
C {iopin.sym} 360 -290 0 0 {name=p4 lab=VREFN}
C {ipin.sym} 120 -290 0 0 {name=p5 lab=CLKS}
C {ipin.sym} 120 -360 0 0 {name=p7 lab=VINP}
C {ipin.sym} 120 -330 0 0 {name=p8 lab=VINN}
C {opin.sym} 180 -340 0 0 {name=p9 lab=DOUT[7:0]}
C {A44_Comparator_StrongARM.sym} 1240 -120 0 0 {name=x1
schematic=A44_Comparator_StrongARM.sch}
C {A44_CDAC_UNIT_TRANS_DRIVER.sym} 820 -270 0 0 {name=x2
schematic=A44_CDAC_UNIT_TRANS_DRIVER.sch}
C {A44_CDAC_UNIT_TRANS_DRIVER.sym} 820 10 2 1 {name=x3
schematic=A44_CDAC_UNIT_TRANS_DRIVER.sch}
C {lab_wire.sym} 580 -240 0 0 {name=p6 sig_type=std_logic lab=VINP}
C {lab_wire.sym} 570 -20 0 0 {name=p10 sig_type=std_logic lab=VINN}
C {lab_wire.sym} 660 -290 0 0 {name=p11 sig_type=std_logic lab=CLKS_CORE}
C {lab_wire.sym} 660 30 0 0 {name=p12 sig_type=std_logic lab=CLKS_CORE}
C {lab_wire.sym} 800 -60 0 0 {name=p13 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 860 -60 0 0 {name=p14 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 800 -180 0 0 {name=p15 sig_type=std_logic lab=VREFP}
C {lab_wire.sym} 860 -180 0 0 {name=p16 sig_type=std_logic lab=VREFN}
C {lab_wire.sym} 810 -340 0 0 {name=p17 sig_type=std_logic lab=GND}
C {lab_wire.sym} 860 -340 0 0 {name=p18 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 810 100 0 0 {name=p19 sig_type=std_logic lab=GND}
C {lab_wire.sym} 860 100 0 0 {name=p20 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1720 -300 0 0 {name=p21 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1800 -300 0 0 {name=p22 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1960 -110 0 0 {name=p23 sig_type=std_logic lab=DOUT[7:0]}
C {lab_wire.sym} 1470 -170 0 0 {name=p24 sig_type=std_logic lab=CLKS_CORE}
C {lab_wire.sym} 1430 -130 0 0 {name=p25 sig_type=std_logic lab=DCMPP}
C {lab_wire.sym} 1440 -90 0 0 {name=p26 sig_type=std_logic lab=DCMPN}
C {lab_wire.sym} 1050 -140 0 0 {name=p27 sig_type=std_logic lab=VRESP}
C {lab_wire.sym} 1050 -100 0 0 {name=p28 sig_type=std_logic lab=VRESN}
C {lab_wire.sym} 1240 -230 0 0 {name=p29 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 1270 -230 0 0 {name=p30 sig_type=std_logic lab=GND}
C {lab_wire.sym} 1380 60 0 0 {name=p31 sig_type=std_logic lab=CMPCK}
C {lab_wire.sym} 1300 -360 0 0 {name=p32 sig_type=std_logic lab=DCTRLP[7:1]}
C {lab_wire.sym} 1290 110 0 0 {name=p33 sig_type=std_logic lab=DCTRLN[7:1]}
C {A44_SAR_LOGIC_ACTUAL_RTL_REPAIR.sym} 1700 -110 0 0 {name=Xsar_logic_actual_RTL}
C {A44_CLKS_BUFFER.sym} 100 -40 0 0 {name=xclks_buffer
schematic=A44_CLKS_BUFFER.sch}
C {lab_wire.sym} -70 -50 0 1 {name=p34 sig_type=std_logic lab=CLKS}
C {lab_wire.sym} 280 -50 0 0 {name=p35 sig_type=std_logic lab=CLKS_CORE}
C {lab_wire.sym} 140 -130 0 0 {name=p36 sig_type=std_logic lab=VDD}
C {lab_wire.sym} 140 40 0 0 {name=p37 sig_type=std_logic lab=GND}
