// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vlng.h for the primary calling header

#include "Vlng__pch.h"

void Vlng___024root___eval_triggers_vec__act(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_triggers_vec__act\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__VactTriggered[0U] = (QData)((IData)(
                                                    ((vlSelfRef.__VdlySched.awaitingCurrentTime() 
                                                      << 2U) 
                                                     | ((((~ (IData)(vlSelfRef.CLKS)) 
                                                          & (IData)(vlSelfRef.__Vtrigprevexpr___TOP__CLKS__0)) 
                                                         << 1U) 
                                                        | ((IData)(vlSelfRef.CLKS) 
                                                           & (~ (IData)(vlSelfRef.__Vtrigprevexpr___TOP__CLKS__0)))))));
    vlSelfRef.__Vtrigprevexpr___TOP__CLKS__0 = vlSelfRef.CLKS;
}

bool Vlng___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___trigger_anySet__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        if (in[n]) {
            return (1U);
        }
        n = ((IData)(1U) + n);
    } while ((1U > n));
    return (0U);
}

void Vlng___024root___act_sequent__TOP__0(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___act_sequent__TOP__0\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.DCTRLP7 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state) 
                               >> 6U));
    vlSelfRef.DCTRLP6 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state) 
                               >> 5U));
    vlSelfRef.DCTRLP5 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state) 
                               >> 4U));
    vlSelfRef.DCTRLP4 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state) 
                               >> 3U));
    vlSelfRef.DCTRLP3 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state) 
                               >> 2U));
    vlSelfRef.DCTRLP2 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state) 
                               >> 1U));
    vlSelfRef.DCTRLP1 = (1U & (IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state));
    vlSelfRef.DCTRLN7 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state) 
                               >> 6U));
    vlSelfRef.DCTRLN6 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state) 
                               >> 5U));
    vlSelfRef.DCTRLN5 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state) 
                               >> 4U));
    vlSelfRef.DCTRLN4 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state) 
                               >> 3U));
    vlSelfRef.DCTRLN3 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state) 
                               >> 2U));
    vlSelfRef.DCTRLN2 = (1U & ((IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state) 
                               >> 1U));
    vlSelfRef.DCTRLN1 = (1U & (IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state));
}

void Vlng___024root___eval_act(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_act\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((4ULL & vlSelfRef.__VactTriggered[0U])) {
        Vlng___024root___act_sequent__TOP__0(vlSelf);
    }
}

void Vlng___024root___nba_sequent__TOP__0(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___nba_sequent__TOP__0\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.CMPCK = 0U;
    vlSelfRef.EOC_INT = 0U;
    vlSelfRef.CONVERSION_COMPLETE = 0U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation 
        = ((IData)(1U) + vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation);
    if ((0U != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active)) {
        vlSelfRef.TIMEOUT_COUNT = (0x000000ffU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.TIMEOUT_COUNT)));
    }
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 0U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state = 0x40U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state = 0x40U;
}

VlCoroutine Vlng___024root___nba_sequent__TOP__1____Vfork_1__0(Vlng___024root* vlSelf);

void Vlng___024root___nba_sequent__TOP__1(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___nba_sequent__TOP__1\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation 
        = ((IData)(1U) + vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation);
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 1U;
    vlSelfRef.CMPCK = 0U;
    vlSelfRef.EOC_INT = 0U;
    vlSelfRef.CONVERSION_COMPLETE = 0U;
    vlSelfRef.INVALID_DECISION_COUNT = 0U;
    vlSelfRef.TIMEOUT_COUNT = 0U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state = 0x40U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state = 0x40U;
    Vlng___024root___nba_sequent__TOP__1____Vfork_1__0(vlSelf);
}

VlCoroutine Vlng___024root___nba_sequent__TOP__1____Vfork_1__0(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___nba_sequent__TOP__1____Vfork_1__0\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h64040530__0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h64040530__0 = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h53fcb1fc__0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h53fcb1fc__0 = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps = 0;
    CData/*7:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__code_work;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__code_work = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__my_generation = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__aborted;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__aborted = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__Vfuncout;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__Vfuncout = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__Vfuncout;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__Vfuncout = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__my_generation = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__aborted;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__aborted = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__my_generation = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__aborted;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__aborted = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__Vfuncout;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__Vfuncout = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__Vfuncout;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__Vfuncout = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__my_generation = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__aborted;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__aborted = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__my_generation = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__aborted;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__aborted = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__Vfuncout;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__Vfuncout = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__Vfuncout;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__Vfuncout = 0;
    IData/*31:0*/ __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index;
    __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index = 0;
    IData/*31:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__my_generation = 0;
    CData/*0:0*/ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__aborted;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__aborted = 0;
    // Body
    co_await vlSelfRef.__VdlySched.delay(0xffffffffffffffffULL, 
                                         nullptr, "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                         230);
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation 
        = vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h64040530__0 = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h53fcb1fc__0 = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__code_work = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__code_work = 0U;
    co_await vlSelfRef.__VdlySched.delay(0x0000000000002b2aULL, 
                                         nullptr, "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                         119);
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__my_generation 
        = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__aborted = 0;
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__aborted 
        = ((__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__my_generation 
            != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation) 
           | (IData)(vlSelfRef.CLKS));
    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted 
        = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__4__aborted;
    if ((1U & (~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)))) {
        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index = 7U;
        while (VL_LTES_III(32, 0U, __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index)) {
            vlSelfRef.CMPCK = 1U;
            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps = 0U;
            co_await vlSelfRef.__VdlySched.delay(VL_EXTEND_QI(64,32, 
                                                              ([&]() {
                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index 
                                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index;
                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__Vfuncout = 0;
                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__Vfuncout 
                                = ((7U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index)
                                    ? 0x00000392U : 
                                   ((6U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index)
                                     ? 0x00000338U : 
                                    ((5U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index)
                                      ? 0x00000392U
                                      : ((4U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index)
                                          ? 0x00000392U
                                          : ((3U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index)
                                              ? 0x00000339U
                                              : ((2U 
                                                  == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index)
                                                  ? 0x00000339U
                                                  : 
                                                 ((1U 
                                                   == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__bit_index)
                                                   ? 0x00000392U
                                                   : 0x00000338U)))))));
                        }(), __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__5__Vfuncout)), 
                                                 nullptr, 
                                                 "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                                 126);
            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index 
                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index;
            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__Vfuncout = 0;
            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__Vfuncout 
                = ((7U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index)
                    ? 0x00000392U : ((6U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index)
                                      ? 0x00000338U
                                      : ((5U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index)
                                          ? 0x00000392U
                                          : ((4U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index)
                                              ? 0x00000392U
                                              : ((3U 
                                                  == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index)
                                                  ? 0x00000339U
                                                  : 
                                                 ((2U 
                                                   == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index)
                                                   ? 0x00000339U
                                                   : 
                                                  ((1U 
                                                    == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__bit_index)
                                                    ? 0x00000392U
                                                    : 0x00000338U)))))));
            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps 
                = __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__decision_aperture_ps__6__Vfuncout;
            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__my_generation 
                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation;
            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__aborted = 0;
            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__aborted 
                = ((__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__my_generation 
                    != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation) 
                   | (IData)(vlSelfRef.CLKS));
            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted 
                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__7__aborted;
            if (__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted) {
                __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index = 0xffffffffU;
            } else {
                if (((IData)(vlSelfRef.DCMPP) & (~ (IData)(vlSelfRef.DCMPN)))) {
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit = 1U;
                } else if (((~ (IData)(vlSelfRef.DCMPP)) 
                            & (IData)(vlSelfRef.DCMPN))) {
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit = 0U;
                } else {
                    co_await vlSelfRef.__VdlySched.delay(0x0000000000001388ULL, 
                                                         nullptr, 
                                                         "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                                         137);
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps 
                        = ((IData)(0x00001388U) + __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps);
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__my_generation 
                        = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation;
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__aborted = 0;
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__aborted 
                        = ((__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__my_generation 
                            != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation) 
                           | (IData)(vlSelfRef.CLKS));
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted 
                        = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__8__aborted;
                    if ((((~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)) 
                          & (IData)(vlSelfRef.DCMPP)) 
                         & (~ (IData)(vlSelfRef.DCMPN)))) {
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit = 1U;
                    } else if ((((~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)) 
                                 & (~ (IData)(vlSelfRef.DCMPP))) 
                                & (IData)(vlSelfRef.DCMPN))) {
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit = 0U;
                    } else {
                        if ((((~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)) 
                              & (IData)(vlSelfRef.DCMPP)) 
                             & (IData)(vlSelfRef.DCMPN))) {
                            vlSelfRef.INVALID_DECISION_COUNT 
                                = (0x000000ffU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.INVALID_DECISION_COUNT)));
                        } else if ((1U & (~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)))) {
                            vlSelfRef.TIMEOUT_COUNT 
                                = (0x000000ffU & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.TIMEOUT_COUNT)));
                        }
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted = 1U;
                        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation 
                            = ((IData)(1U) + vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation);
                        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 0U;
                        vlSelfRef.CMPCK = 0U;
                        vlSelfRef.EOC_INT = 0U;
                        vlSelfRef.CONVERSION_COMPLETE = 0U;
                    }
                }
                if ((1U & (~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)))) {
                    __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__code_work 
                        = (((~ ((IData)(1U) << (7U 
                                                & __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index))) 
                            & (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__code_work)) 
                           | (0x00ffU & ((1U & __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit) 
                                         << (7U & __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index))));
                    if (VL_LTS_III(32, 0U, __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index)) {
                        co_await vlSelfRef.__VdlySched.delay(
                                                             VL_EXTEND_QI(64,32, 
                                                                          (([&]() {
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index 
                                                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index;
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__Vfuncout = 0;
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__Vfuncout 
                                                = (
                                                   (7U 
                                                    == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index)
                                                    ? 0x00001ee7U
                                                    : 
                                                   ((6U 
                                                     == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index)
                                                     ? 0x00001efbU
                                                     : 
                                                    ((5U 
                                                      == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index)
                                                      ? 0x00001f56U
                                                      : 
                                                     ((4U 
                                                       == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index)
                                                       ? 0x00001f57U
                                                       : 
                                                      ((3U 
                                                        == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index)
                                                        ? 0x00001efeU
                                                        : 
                                                       ((2U 
                                                         == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__bit_index)
                                                         ? 0x00001effU
                                                         : 0x00001f59U))))));
                                        }(), __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__9__Vfuncout) 
                                                                           - __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps)), 
                                                             nullptr, 
                                                             "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                                             162);
                        __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index 
                            = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index;
                        __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__Vfuncout = 0;
                        __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__Vfuncout 
                            = ((7U == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index)
                                ? 0x00001ee7U : ((6U 
                                                  == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index)
                                                  ? 0x00001efbU
                                                  : 
                                                 ((5U 
                                                   == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index)
                                                   ? 0x00001f56U
                                                   : 
                                                  ((4U 
                                                    == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index)
                                                    ? 0x00001f57U
                                                    : 
                                                   ((3U 
                                                     == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index)
                                                     ? 0x00001efeU
                                                     : 
                                                    ((2U 
                                                      == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__bit_index)
                                                      ? 0x00001effU
                                                      : 0x00001f59U))))));
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps 
                            = __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrl_from_rise_ps__10__Vfuncout;
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__my_generation 
                            = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation;
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__aborted = 0;
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__aborted 
                            = ((__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__my_generation 
                                != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation) 
                               | (IData)(vlSelfRef.CLKS));
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted 
                            = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__11__aborted;
                        if ((1U & (~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)))) {
                            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h53fcb1fc__0 
                                = (1U & __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit);
                            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h64040530__0 
                                = (1U & (~ __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__decision_bit));
                            if (VL_LIKELY(((6U >= (7U 
                                                   & (__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index 
                                                      - (IData)(1U))))))) {
                                vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state 
                                    = (((~ ((IData)(1U) 
                                            << (7U 
                                                & (__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index 
                                                   - (IData)(1U))))) 
                                        & (IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state)) 
                                       | (0x7fU & ((IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h53fcb1fc__0) 
                                                   << 
                                                   (7U 
                                                    & (__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index 
                                                       - (IData)(1U))))));
                                vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state 
                                    = (((~ ((IData)(1U) 
                                            << (7U 
                                                & (__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index 
                                                   - (IData)(1U))))) 
                                        & (IData)(vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state)) 
                                       | (0x7fU & ((IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3____Vlvbound_h64040530__0) 
                                                   << 
                                                   (7U 
                                                    & (__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index 
                                                       - (IData)(1U))))));
                            }
                        }
                    } else {
                        co_await vlSelfRef.__VdlySched.delay((QData)((IData)(
                                                                             ((IData)(0x00002989U) 
                                                                              - __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps))), 
                                                             nullptr, 
                                                             "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                                             170);
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps = 0x00002989U;
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__my_generation 
                            = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation;
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__aborted = 0;
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__aborted 
                            = ((__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__my_generation 
                                != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation) 
                               | (IData)(vlSelfRef.CLKS));
                        __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted 
                            = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__12__aborted;
                        if ((1U & (~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)))) {
                            vlSelfRef.DOUT = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__code_work;
                            vlSelfRef.EOC_INT = 1U;
                            vlSelfRef.CONVERSION_COMPLETE = 1U;
                        }
                    }
                    if ((1U & (~ (IData)(__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted)))) {
                        co_await vlSelfRef.__VdlySched.delay(
                                                             VL_EXTEND_QI(64,32, 
                                                                          (([&]() {
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index 
                                                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index;
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__Vfuncout = 0;
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__Vfuncout 
                                                = (
                                                   (7U 
                                                    == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index)
                                                    ? 0x00003642U
                                                    : 
                                                   ((6U 
                                                     == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index)
                                                     ? 0x00003636U
                                                     : 
                                                    ((5U 
                                                      == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index)
                                                      ? 0x00003643U
                                                      : 
                                                     ((4U 
                                                       == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index)
                                                       ? 0x00003643U
                                                       : 
                                                      ((3U 
                                                        == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index)
                                                        ? 0x00003636U
                                                        : 
                                                       ((2U 
                                                         == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index)
                                                         ? 0x00003637U
                                                         : 
                                                        ((1U 
                                                          == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__bit_index)
                                                          ? 0x00003644U
                                                          : 0x00003636U)))))));
                                        }(), __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__cmpck_high_ps__13__Vfuncout) 
                                                                           - __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__elapsed_ps)), 
                                                             nullptr, 
                                                             "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                                             181);
                        vlSelfRef.CMPCK = 0U;
                        if (VL_LTS_III(32, 0U, __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index)) {
                            co_await vlSelfRef.__VdlySched.delay(
                                                                 VL_EXTEND_QI(64,32, 
                                                                              ([&]() {
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index 
                                                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index;
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__Vfuncout = 0;
                                            __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__Vfuncout 
                                                = (
                                                   (7U 
                                                    == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index)
                                                    ? 0x00002d28U
                                                    : 
                                                   ((6U 
                                                     == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index)
                                                     ? 0x00002d37U
                                                     : 
                                                    ((5U 
                                                      == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index)
                                                      ? 0x00002d38U
                                                      : 
                                                     ((4U 
                                                       == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index)
                                                       ? 0x00002d28U
                                                       : 
                                                      ((3U 
                                                        == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index)
                                                        ? 0x00002d28U
                                                        : 
                                                       ((2U 
                                                         == __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__bit_index)
                                                         ? 0x00002d39U
                                                         : 0x00002d36U))))));
                                        }(), __Vfunc_SAR_LOGIC_BEH_TT_3P3_27C__DOT__low_guard_ps__14__Vfuncout)), 
                                                                 nullptr, 
                                                                 "SAR_LOGIC_BEH_TT_3P3_27C.v", 
                                                                 184);
                            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__my_generation 
                                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__my_generation;
                            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__aborted = 0;
                            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__aborted 
                                = ((__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__my_generation 
                                    != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation) 
                                   | (IData)(vlSelfRef.CLKS));
                            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__aborted 
                                = __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__abort_if_stale__15__aborted;
                        } else {
                            vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 0U;
                        }
                    }
                }
            }
            __Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index 
                = (__Vtask_SAR_LOGIC_BEH_TT_3P3_27C__DOT__run_conversion__3__bit_index 
                   - (IData)(1U));
        }
    }
    co_return;
}

void Vlng___024root___eval_nba(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_nba\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VnbaTriggered[0U])) {
        vlSelfRef.CMPCK = 0U;
        vlSelfRef.EOC_INT = 0U;
        vlSelfRef.CONVERSION_COMPLETE = 0U;
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation 
            = ((IData)(1U) + vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation);
        if ((0U != vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active)) {
            vlSelfRef.TIMEOUT_COUNT = (0x000000ffU 
                                       & ((IData)(1U) 
                                          + (IData)(vlSelfRef.TIMEOUT_COUNT)));
        }
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 0U;
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state = 0x40U;
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state = 0x40U;
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered[0U])) {
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation 
            = ((IData)(1U) + vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation);
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 1U;
        vlSelfRef.CMPCK = 0U;
        vlSelfRef.EOC_INT = 0U;
        vlSelfRef.CONVERSION_COMPLETE = 0U;
        vlSelfRef.INVALID_DECISION_COUNT = 0U;
        vlSelfRef.TIMEOUT_COUNT = 0U;
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state = 0x40U;
        vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state = 0x40U;
        Vlng___024root___nba_sequent__TOP__1____Vfork_1__0(vlSelf);
    }
    if ((7ULL & vlSelfRef.__VnbaTriggered[0U])) {
        Vlng___024root___act_sequent__TOP__0(vlSelf);
    }
}

void Vlng___024root___timing_resume(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___timing_resume\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((4ULL & vlSelfRef.__VactTriggered[0U])) {
        vlSelfRef.__VdlySched.resume();
    }
}

void Vlng___024root___trigger_orInto__act_vec_vec(VlUnpacked<QData/*63:0*/, 1> &out, const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___trigger_orInto__act_vec_vec\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = (out[n] | in[n]);
        n = ((IData)(1U) + n);
    } while ((0U >= n));
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vlng___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG

bool Vlng___024root___eval_phase__act(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_phase__act\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VactExecute;
    // Body
    Vlng___024root___eval_triggers_vec__act(vlSelf);
    Vlng___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VactTriggered, vlSelfRef.__VactTriggeredAcc);
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vlng___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
    }
#endif
    Vlng___024root___trigger_orInto__act_vec_vec(vlSelfRef.__VnbaTriggered, vlSelfRef.__VactTriggered);
    __VactExecute = Vlng___024root___trigger_anySet__act(vlSelfRef.__VactTriggered);
    if (__VactExecute) {
        vlSelfRef.__VactTriggeredAcc.fill(0ULL);
        Vlng___024root___timing_resume(vlSelf);
        Vlng___024root___eval_act(vlSelf);
    }
    return (__VactExecute);
}

bool Vlng___024root___eval_phase__inact(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_phase__inact\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VinactExecute;
    // Body
    __VinactExecute = vlSelfRef.__VdlySched.awaitingZeroDelay();
    if (__VinactExecute) {
        VL_FATAL_MT("SAR_LOGIC_BEH_TT_3P3_27C.v", 3, "", "ZERODLY: Design Verilated with '--no-sched-zero-delay', but #0 delay executed at runtime");
    }
    return (__VinactExecute);
}

void Vlng___024root___trigger_clear__act(VlUnpacked<QData/*63:0*/, 1> &out) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___trigger_clear__act\n"); );
    // Locals
    IData/*31:0*/ n;
    // Body
    n = 0U;
    do {
        out[n] = 0ULL;
        n = ((IData)(1U) + n);
    } while ((1U > n));
}

bool Vlng___024root___eval_phase__nba(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_phase__nba\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = Vlng___024root___trigger_anySet__act(vlSelfRef.__VnbaTriggered);
    if (__VnbaExecute) {
        Vlng___024root___eval_nba(vlSelf);
        Vlng___024root___trigger_clear__act(vlSelfRef.__VnbaTriggered);
    }
    return (__VnbaExecute);
}

void Vlng___024root___eval(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VnbaIterCount;
    // Body
    __VnbaIterCount = 0U;
    do {
        if (VL_UNLIKELY(((0x00000064U < __VnbaIterCount)))) {
#ifdef VL_DEBUG
            Vlng___024root___dump_triggers__act(vlSelfRef.__VnbaTriggered, "nba"s);
#endif
            VL_FATAL_MT("SAR_LOGIC_BEH_TT_3P3_27C.v", 3, "", "DIDNOTCONVERGE: NBA region did not converge after '--converge-limit' of 100 tries");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        vlSelfRef.__VinactIterCount = 0U;
        do {
            if (VL_UNLIKELY(((0x00000064U < vlSelfRef.__VinactIterCount)))) {
                VL_FATAL_MT("SAR_LOGIC_BEH_TT_3P3_27C.v", 3, "", "DIDNOTCONVERGE: Inactive region did not converge after '--converge-limit' of 100 tries");
            }
            vlSelfRef.__VinactIterCount = ((IData)(1U) 
                                           + vlSelfRef.__VinactIterCount);
            vlSelfRef.__VactIterCount = 0U;
            do {
                if (VL_UNLIKELY(((0x00000064U < vlSelfRef.__VactIterCount)))) {
#ifdef VL_DEBUG
                    Vlng___024root___dump_triggers__act(vlSelfRef.__VactTriggered, "act"s);
#endif
                    VL_FATAL_MT("SAR_LOGIC_BEH_TT_3P3_27C.v", 3, "", "DIDNOTCONVERGE: Active region did not converge after '--converge-limit' of 100 tries");
                }
                vlSelfRef.__VactIterCount = ((IData)(1U) 
                                             + vlSelfRef.__VactIterCount);
                vlSelfRef.__VactPhaseResult = Vlng___024root___eval_phase__act(vlSelf);
            } while (vlSelfRef.__VactPhaseResult);
            vlSelfRef.__VinactPhaseResult = Vlng___024root___eval_phase__inact(vlSelf);
        } while (vlSelfRef.__VinactPhaseResult);
        vlSelfRef.__VnbaPhaseResult = Vlng___024root___eval_phase__nba(vlSelf);
    } while (vlSelfRef.__VnbaPhaseResult);
}

#ifdef VL_DEBUG
void Vlng___024root___eval_debug_assertions(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_debug_assertions\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if (VL_UNLIKELY(((vlSelfRef.CLKS & 0xfeU)))) {
        Verilated::overWidthError("CLKS");
    }
    if (VL_UNLIKELY(((vlSelfRef.DCMPP & 0xfeU)))) {
        Verilated::overWidthError("DCMPP");
    }
    if (VL_UNLIKELY(((vlSelfRef.DCMPN & 0xfeU)))) {
        Verilated::overWidthError("DCMPN");
    }
}
#endif  // VL_DEBUG
