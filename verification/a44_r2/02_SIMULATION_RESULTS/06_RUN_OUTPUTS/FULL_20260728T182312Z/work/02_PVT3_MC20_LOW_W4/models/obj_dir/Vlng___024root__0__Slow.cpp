// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vlng.h for the primary calling header

#include "Vlng__pch.h"

VL_ATTR_COLD void Vlng___024root___eval_static(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_static\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vtrigprevexpr___TOP__CLKS__0 = vlSelfRef.CLKS;
    do {
        vlSelfRef.__VactTriggeredAcc[vlSelfRef.__Vi] 
            = vlSelfRef.__VactTriggered[vlSelfRef.__Vi];
        vlSelfRef.__Vi = ((IData)(1U) + vlSelfRef.__Vi);
    } while ((0U >= vlSelfRef.__Vi));
}

VL_ATTR_COLD void Vlng___024root___eval_initial(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_initial\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation = 0U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 0U;
    vlSelfRef.CMPCK = 0U;
    vlSelfRef.DOUT = 0U;
    vlSelfRef.EOC_INT = 0U;
    vlSelfRef.INVALID_DECISION_COUNT = 0U;
    vlSelfRef.TIMEOUT_COUNT = 0U;
    vlSelfRef.CONVERSION_COMPLETE = 0U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state = 0x40U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state = 0x40U;
}

VL_ATTR_COLD void Vlng___024root___eval_initial__TOP(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_initial__TOP\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation = 0U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = 0U;
    vlSelfRef.CMPCK = 0U;
    vlSelfRef.DOUT = 0U;
    vlSelfRef.EOC_INT = 0U;
    vlSelfRef.INVALID_DECISION_COUNT = 0U;
    vlSelfRef.TIMEOUT_COUNT = 0U;
    vlSelfRef.CONVERSION_COMPLETE = 0U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state = 0x40U;
    vlSelfRef.SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state = 0x40U;
}

VL_ATTR_COLD void Vlng___024root___eval_final(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_final\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

#ifdef VL_DEBUG
VL_ATTR_COLD void Vlng___024root___dump_triggers__stl(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag);
#endif  // VL_DEBUG
VL_ATTR_COLD bool Vlng___024root___eval_phase__stl(Vlng___024root* vlSelf);

VL_ATTR_COLD void Vlng___024root___eval_settle(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_settle\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    IData/*31:0*/ __VstlIterCount;
    // Body
    __VstlIterCount = 0U;
    vlSelfRef.__VstlFirstIteration = 1U;
    do {
        if (VL_UNLIKELY(((0x00000064U < __VstlIterCount)))) {
#ifdef VL_DEBUG
            Vlng___024root___dump_triggers__stl(vlSelfRef.__VstlTriggered, "stl"s);
#endif
            VL_FATAL_MT("SAR_LOGIC_BEH_TT_3P3_27C.v", 3, "", "DIDNOTCONVERGE: Settle region did not converge after '--converge-limit' of 100 tries");
        }
        __VstlIterCount = ((IData)(1U) + __VstlIterCount);
        vlSelfRef.__VstlPhaseResult = Vlng___024root___eval_phase__stl(vlSelf);
        vlSelfRef.__VstlFirstIteration = 0U;
    } while (vlSelfRef.__VstlPhaseResult);
}

VL_ATTR_COLD void Vlng___024root___eval_triggers_vec__stl(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_triggers_vec__stl\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__VstlTriggered[0U] = ((0xfffffffffffffffeULL 
                                      & vlSelfRef.__VstlTriggered[0U]) 
                                     | (IData)((IData)(vlSelfRef.__VstlFirstIteration)));
}

VL_ATTR_COLD bool Vlng___024root___trigger_anySet__stl(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void Vlng___024root___dump_triggers__stl(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___dump_triggers__stl\n"); );
    // Body
    if ((1U & (~ (IData)(Vlng___024root___trigger_anySet__stl(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: Internal 'stl' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD bool Vlng___024root___trigger_anySet__stl(const VlUnpacked<QData/*63:0*/, 1> &in) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___trigger_anySet__stl\n"); );
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

void Vlng___024root___act_sequent__TOP__0(Vlng___024root* vlSelf);

VL_ATTR_COLD void Vlng___024root___eval_stl(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_stl\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VstlTriggered[0U])) {
        Vlng___024root___act_sequent__TOP__0(vlSelf);
    }
}

VL_ATTR_COLD bool Vlng___024root___eval_phase__stl(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___eval_phase__stl\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Locals
    CData/*0:0*/ __VstlExecute;
    // Body
    Vlng___024root___eval_triggers_vec__stl(vlSelf);
#ifdef VL_DEBUG
    if (VL_UNLIKELY(vlSymsp->_vm_contextp__->debug())) {
        Vlng___024root___dump_triggers__stl(vlSelfRef.__VstlTriggered, "stl"s);
    }
#endif
    __VstlExecute = Vlng___024root___trigger_anySet__stl(vlSelfRef.__VstlTriggered);
    if (__VstlExecute) {
        Vlng___024root___eval_stl(vlSelf);
    }
    return (__VstlExecute);
}

bool Vlng___024root___trigger_anySet__act(const VlUnpacked<QData/*63:0*/, 1> &in);

#ifdef VL_DEBUG
VL_ATTR_COLD void Vlng___024root___dump_triggers__act(const VlUnpacked<QData/*63:0*/, 1> &triggers, const std::string &tag) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___dump_triggers__act\n"); );
    // Body
    if ((1U & (~ (IData)(Vlng___024root___trigger_anySet__act(triggers))))) {
        VL_DBG_MSGS("         No '" + tag + "' region triggers active\n");
    }
    if ((1U & (IData)(triggers[0U]))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 0 is active: @(posedge CLKS)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 1U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 1 is active: @(negedge CLKS)\n");
    }
    if ((1U & (IData)((triggers[0U] >> 2U)))) {
        VL_DBG_MSGS("         '" + tag + "' region trigger index 2 is active: @([true] __VdlySched.awaitingCurrentTime())\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void Vlng___024root___ctor_var_reset(Vlng___024root* vlSelf) {
    VL_DEBUG_IF(VL_DBG_MSGF("+    Vlng___024root___ctor_var_reset\n"); );
    Vlng__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    const uint64_t __VscopeHash = VL_MURMUR64_HASH(vlSelf->vlNamep);
    vlSelf->CLKS = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17292302523016146338ull);
    vlSelf->DCMPP = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 458323366561547762ull);
    vlSelf->DCMPN = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 975617068486959382ull);
    vlSelf->CMPCK = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 4923815086917925862ull);
    vlSelf->DCTRLP7 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 7790197393322483814ull);
    vlSelf->DCTRLP6 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 15128430294915327357ull);
    vlSelf->DCTRLP5 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 18089508020573115183ull);
    vlSelf->DCTRLP4 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 13467074434425302397ull);
    vlSelf->DCTRLP3 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 16753063872510089067ull);
    vlSelf->DCTRLP2 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 5319640987966428726ull);
    vlSelf->DCTRLP1 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 10230188988185386563ull);
    vlSelf->DCTRLN7 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 17364970576151824260ull);
    vlSelf->DCTRLN6 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3828774502661065946ull);
    vlSelf->DCTRLN5 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3285230246740759543ull);
    vlSelf->DCTRLN4 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 8424637237550004911ull);
    vlSelf->DCTRLN3 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1623874386250938343ull);
    vlSelf->DCTRLN2 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 12791640981848692445ull);
    vlSelf->DCTRLN1 = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 1358218097304933987ull);
    vlSelf->DOUT = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 5815938063623818353ull);
    vlSelf->EOC_INT = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 3990532211471604261ull);
    vlSelf->INVALID_DECISION_COUNT = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 5673096591113962376ull);
    vlSelf->TIMEOUT_COUNT = VL_SCOPED_RAND_RESET_I(8, __VscopeHash, 15139756327778373986ull);
    vlSelf->CONVERSION_COMPLETE = VL_SCOPED_RAND_RESET_I(1, __VscopeHash, 2544870787828662822ull);
    vlSelf->SAR_LOGIC_BEH_TT_3P3_27C__DOT__generation = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 6444729557354540047ull);
    vlSelf->SAR_LOGIC_BEH_TT_3P3_27C__DOT__conversion_active = VL_SCOPED_RAND_RESET_I(32, __VscopeHash, 2884549313822912699ull);
    vlSelf->SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrlp_state = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 9288844908529226769ull);
    vlSelf->SAR_LOGIC_BEH_TT_3P3_27C__DOT__dctrln_state = VL_SCOPED_RAND_RESET_I(7, __VscopeHash, 2320071825029101628ull);
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VstlTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggered[__Vi0] = 0;
    }
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VactTriggeredAcc[__Vi0] = 0;
    }
    vlSelf->__Vtrigprevexpr___TOP__CLKS__0 = 0;
    for (int __Vi0 = 0; __Vi0 < 1; ++__Vi0) {
        vlSelf->__VnbaTriggered[__Vi0] = 0;
    }
    vlSelf->__Vi = 0;
}
