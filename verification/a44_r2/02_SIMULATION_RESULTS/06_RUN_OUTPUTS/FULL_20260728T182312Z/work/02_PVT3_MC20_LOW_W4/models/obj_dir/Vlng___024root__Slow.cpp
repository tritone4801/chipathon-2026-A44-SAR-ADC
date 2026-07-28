// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See Vlng.h for the primary calling header

#include "Vlng__pch.h"

void Vlng___024root___ctor_var_reset(Vlng___024root* vlSelf);

Vlng___024root::Vlng___024root(Vlng__Syms* symsp, const char* namep)
    : __VdlySched{*symsp->_vm_contextp__}
 {
    vlSymsp = symsp;
    vlNamep = strdup(namep);
    // Reset structure values
    Vlng___024root___ctor_var_reset(this);
}

void Vlng___024root::__Vconfigure(bool first) {
    (void)first;  // Prevent unused variable warning
}

Vlng___024root::~Vlng___024root() {
    VL_DO_DANGLING(std::free(const_cast<char*>(vlNamep)), vlNamep);
}
