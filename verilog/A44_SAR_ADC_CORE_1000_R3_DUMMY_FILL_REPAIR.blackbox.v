// SPDX-License-Identifier: Apache-2.0
// Physical black-box contract for the hash-bound R3B prefill macro.

`default_nettype none

(* blackbox *)
module A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR (
    inout  wire       VDD,
    inout  wire       GND,
    input  wire       VREFP,
    input  wire       VREFN,
    input  wire       VINP,
    input  wire       VINN,
    input  wire       CLKS,
    output wire [7:0] DOUT
);
endmodule

`default_nettype wire
