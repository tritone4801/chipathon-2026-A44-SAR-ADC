// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See Vlng.h for the primary calling header

#ifndef VERILATED_VLNG___024ROOT_H_
#define VERILATED_VLNG___024ROOT_H_  // guard

#include "verilated.h"
#include "verilated_timing.h"


class Vlng__Syms;

class alignas(VL_CACHE_LINE_BYTES) Vlng___024root final {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(CLKS,0,0);
    VL_IN8(DCMPP,0,0);
    VL_IN8(DCMPN,0,0);
    VL_OUT8(CMPCK,0,0);
    VL_OUT8(DCTRLP7,0,0);
    VL_OUT8(DCTRLP6,0,0);
    VL_OUT8(DCTRLP5,0,0);
    VL_OUT8(DCTRLP4,0,0);
    VL_OUT8(DCTRLP3,0,0);
    VL_OUT8(DCTRLP2,0,0);
    VL_OUT8(DCTRLP1,0,0);
    VL_OUT8(DCTRLN7,0,0);
    VL_OUT8(DCTRLN6,0,0);
    VL_OUT8(DCTRLN5,0,0);
    VL_OUT8(DCTRLN4,0,0);
    VL_OUT8(DCTRLN3,0,0);
    VL_OUT8(DCTRLN2,0,0);
    VL_OUT8(DCTRLN1,0,0);
    VL_OUT8(DOUT,7,0);
    VL_OUT8(EOC_INT,0,0);
    VL_OUT8(INVALID_DECISION_COUNT,7,0);
    VL_OUT8(TIMEOUT_COUNT,7,0);
    VL_OUT8(CONVERSION_COMPLETE,0,0);
    CData/*6:0*/ SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state;
    CData/*6:0*/ SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state;
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __VstlPhaseResult;
    CData/*0:0*/ __Vtrigprevexpr___TOP__CLKS__0;
    CData/*0:0*/ __VactPhaseResult;
    CData/*0:0*/ __VinactPhaseResult;
    CData/*0:0*/ __VnbaPhaseResult;
    IData/*31:0*/ SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation;
    IData/*31:0*/ SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active;
    IData/*31:0*/ __VactIterCount;
    IData/*31:0*/ __VinactIterCount;
    IData/*31:0*/ __Vi;
    VlUnpacked<QData/*63:0*/, 1> __VstlTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VactTriggered;
    VlUnpacked<QData/*63:0*/, 1> __VactTriggeredAcc;
    VlUnpacked<QData/*63:0*/, 1> __VnbaTriggered;
    VlDelayScheduler __VdlySched;

    // INTERNAL VARIABLES
    Vlng__Syms* vlSymsp;
    const char* vlNamep;

    // CONSTRUCTORS
    Vlng___024root(Vlng__Syms* symsp, const char* namep);
    ~Vlng___024root();
    VL_UNCOPYABLE(Vlng___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
