// A44_A official project-slot wrapper.  DOUT input readback is intentionally unused.
module A44_A (
  inout GND, VDD,
  output CLKS_PU, CLKS_PD,
  input CLKS,
  output [7:0] DOUT_CS, DOUT_SL, DOUT_IE, DOUT_OE, DOUT_PU, DOUT_PD, DOUT_OUT, DOUT_PDRV0, DOUT_PDRV1,
  input [7:0] DOUT_IN,
  inout VREFN, VINN, VINP, VREFP
);
  assign CLKS_PU = 1'b0;
  assign CLKS_PD = 1'b0;
  assign DOUT_CS = 8'h00;
  assign DOUT_SL = 8'h00;
  assign DOUT_IE = 8'h00;
  assign DOUT_OE = 8'hff;
  assign DOUT_PU = 8'h00;
  assign DOUT_PD = 8'h00;
  assign DOUT_PDRV0 = 8'h00;
  assign DOUT_PDRV1 = 8'h00;
  A44_SAR_ADC_CORE_1000_R3_DUMMY_FILL_REPAIR XCORE (
    .VDD(VDD), .GND(GND), .VREFP(VREFP), .VREFN(VREFN),
    .VINP(VINP), .VINN(VINN), .CLKS(CLKS), .DOUT(DOUT_OUT)
  );
endmodule
