// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Model implementation (design independent parts)

#include "Vlng__pch.h"

//============================================================
// Constructors

Vlng::Vlng(VerilatedContext* _vcontextp__, const char* _vcname__)
    : VerilatedModel{*_vcontextp__}
    , vlSymsp{new Vlng__Syms(contextp(), _vcname__, this)}
    , CLKS{vlSymsp->TOP.CLKS}
    , DCMPP{vlSymsp->TOP.DCMPP}
    , DCMPN{vlSymsp->TOP.DCMPN}
    , CMPCK{vlSymsp->TOP.CMPCK}
    , DCTRLP7{vlSymsp->TOP.DCTRLP7}
    , DCTRLP6{vlSymsp->TOP.DCTRLP6}
    , DCTRLP5{vlSymsp->TOP.DCTRLP5}
    , DCTRLP4{vlSymsp->TOP.DCTRLP4}
    , DCTRLP3{vlSymsp->TOP.DCTRLP3}
    , DCTRLP2{vlSymsp->TOP.DCTRLP2}
    , DCTRLP1{vlSymsp->TOP.DCTRLP1}
    , DCTRLN7{vlSymsp->TOP.DCTRLN7}
    , DCTRLN6{vlSymsp->TOP.DCTRLN6}
    , DCTRLN5{vlSymsp->TOP.DCTRLN5}
    , DCTRLN4{vlSymsp->TOP.DCTRLN4}
    , DCTRLN3{vlSymsp->TOP.DCTRLN3}
    , DCTRLN2{vlSymsp->TOP.DCTRLN2}
    , DCTRLN1{vlSymsp->TOP.DCTRLN1}
    , DOUT{vlSymsp->TOP.DOUT}
    , EOC_INT{vlSymsp->TOP.EOC_INT}
    , INVALID_DECISION_COUNT{vlSymsp->TOP.INVALID_DECISION_COUNT}
    , TIMEOUT_COUNT{vlSymsp->TOP.TIMEOUT_COUNT}
    , CONVERSION_COMPLETE{vlSymsp->TOP.CONVERSION_COMPLETE}
    , rootp{&(vlSymsp->TOP)}
{
    // Register model with the context
    contextp()->addModel(this);
}

Vlng::Vlng(const char* _vcname__)
    : Vlng(Verilated::threadContextp(), _vcname__)
{
}

//============================================================
// Destructor

Vlng::~Vlng() {
    delete vlSymsp;
}

//============================================================
// Evaluation function

#ifdef VL_DEBUG
void Vlng___024root___eval_debug_assertions(Vlng___024root* vlSelf);
#endif  // VL_DEBUG
void Vlng___024root___eval_static(Vlng___024root* vlSelf);
void Vlng___024root___eval_initial(Vlng___024root* vlSelf);
void Vlng___024root___eval_settle(Vlng___024root* vlSelf);
void Vlng___024root___eval(Vlng___024root* vlSelf);

void Vlng::eval_step() {
    VL_DEBUG_IF(VL_DBG_MSGF("+++++TOP Evaluate Vlng::eval_step\n"); );
#ifdef VL_DEBUG
    // Debug assertions
    Vlng___024root___eval_debug_assertions(&(vlSymsp->TOP));
#endif  // VL_DEBUG
    vlSymsp->__Vm_deleter.deleteAll();
    if (VL_UNLIKELY(!vlSymsp->__Vm_didInit)) {
        VL_DEBUG_IF(VL_DBG_MSGF("+ Initial\n"););
        Vlng___024root___eval_static(&(vlSymsp->TOP));
        Vlng___024root___eval_initial(&(vlSymsp->TOP));
        Vlng___024root___eval_settle(&(vlSymsp->TOP));
        vlSymsp->__Vm_didInit = true;
    }
    VL_DEBUG_IF(VL_DBG_MSGF("+ Eval\n"););
    Vlng___024root___eval(&(vlSymsp->TOP));
    // Evaluate cleanup
    Verilated::endOfEval(vlSymsp->__Vm_evalMsgQp);
}

//============================================================
// Events and timing
bool Vlng::eventsPending() { return !vlSymsp->TOP.__VdlySched.empty() && !contextp()->gotFinish(); }

uint64_t Vlng::nextTimeSlot() { return vlSymsp->TOP.__VdlySched.nextTimeSlot(); }

//============================================================
// Utilities

const char* Vlng::name() const {
    return vlSymsp->name();
}

//============================================================
// Invoke final blocks

void Vlng___024root___eval_final(Vlng___024root* vlSelf);

VL_ATTR_COLD void Vlng::final() {
    Vlng___024root___eval_final(&(vlSymsp->TOP));
}

//============================================================
// Implementations of abstract methods from VerilatedModel

const char* Vlng::hierName() const { return vlSymsp->name(); }
const char* Vlng::modelName() const { return "Vlng"; }
unsigned Vlng::threads() const { return 1; }
void Vlng::prepareClone() const { contextp()->prepareClone(); }
void Vlng::atClone() const {
    contextp()->threadPoolpOnClone();
}
