* Reduced no-R6 equivalent loads. Values retain accepted-fixture impedances.
* VIN: RDRV 50 + RISO 50 + RLINE 5 ohm per leg.
.param VIN_R_EQ=105 VIN_CP_EQ=1p VIN_CN_EQ=1p VIN_CDM_EQ=200f VIN_CCM_EQ=500f
* VREF: RBUF 1 + RLINE 1 ohm; local decoupling and line load retained.
.param REF_R_EQ=2 REF_CLOCAL_EQ=200p REF_ESR_EQ=0.2 REF_CLINE_EQ=500f
* CLKS: RDRV 100 + RLINE 5 ohm; line and receiver loads retained.
.param CLK_R_EQ=105 CLK_C_EQ=1.5p CLK_TR_EQ=0.25n CLK_TF_EQ=0.25n
* Comparator outputs see the accepted logic-input equivalent capacitance.
.param CLOGIC_IN_P=20f CLOGIC_IN_N=20f
* TT electrical logic evidence: 10 fF-loaded DCTRL 10-90% edges 0.256-0.339 ns.
* A conservative 15 kohm Thevenin output resistance is used with 0.05 ns intrinsic edges.
.param DCTRL_R_EQ=15k DCTRL_TR_EQ=0.05n DCTRL_TF_EQ=0.05n
* TT electrical logic evidence: 10 fF-loaded CMPCK rise/fall 0.78/0.48 ns.
* A conservative 35 kohm Thevenin resistance is used with 0.05 ns intrinsic edges.
.param CMPCK_R_EQ=35k CMPCK_TR_EQ=0.05n CMPCK_TF_EQ=0.05n
* DOUT accepted-fixture path: RDRV 150 + RLINE 10 ohm, CRX + CLINE = 1 pF.
.param DOUT_R_EQ=160 DOUT_C_EQ=1p DOUT_TR_EQ=0.25n DOUT_TF_EQ=0.25n
