// CLKS-only ideal 8-bit asynchronous SAR core for verification.
//
// The test-only analog input is represented as signed fixed-point LSB-Q units:
//   vdiff_q_lsb = round((v_diff - v_min) / LSB)
// Normal conversion starts on the CLKS falling edge. EOC_INT is exposed only as
// an internal observation point; it is not a frozen external ADC pin.

module ideal_sar_core #(
    parameter int BITS = 8
) (
    input  logic clks,
    input  logic rst_n,
    input  logic signed [31:0] vdiff_q_lsb,
    output logic [BITS-1:0] dout,
    output logic eoc_int,
    output logic cmpck,
    output logic [BITS-1:0] clk_bit,
    output logic [BITS-1:1] dctrlp,
    output logic [BITS-1:1] dctrln,
    output logic [BITS-1:0] trial_code,
    output logic [3:0] bit_index,
    output logic dcmpp,
    output logic dcmpn,
    output logic comparator_decision
);

    logic [BITS-1:0] code_work;
    logic decision_work;

    function automatic logic [BITS-1:0] bit_mask(input int idx);
        bit_mask = '0;
        bit_mask[idx] = 1'b1;
    endfunction

    function automatic logic cmp(input logic [BITS-1:0] trial);
        cmp = (vdiff_q_lsb >= int'(trial));
    endfunction

    always @(posedge clks or negedge clks or negedge rst_n) begin
        if (!rst_n) begin
            dout <= '0;
            eoc_int <= 1'b0;
            cmpck <= 1'b0;
            clk_bit <= '0;
            dctrlp <= '0;
            dctrln <= '0;
            trial_code <= '0;
            bit_index <= '0;
            dcmpp <= 1'b0;
            dcmpn <= 1'b0;
            comparator_decision <= 1'b0;
        end else if (clks) begin
            eoc_int <= 1'b0;
            cmpck <= 1'b0;
            clk_bit <= '0;
            dctrlp <= '0;
            dctrln <= '0;
            trial_code <= '0;
            bit_index <= '0;
            dcmpp <= 1'b0;
            dcmpn <= 1'b0;
            comparator_decision <= 1'b0;
            code_work <= '0;
            decision_work <= 1'b0;
        end else begin
            code_work = '0;
            clk_bit <= '1;
            cmpck <= 1'b0;
            for (int idx = BITS - 1; idx >= 0; idx--) begin
                trial_code <= code_work | bit_mask(idx);
                bit_index <= idx[3:0];
                decision_work = cmp(code_work | bit_mask(idx));
                comparator_decision <= decision_work;
                dcmpp <= decision_work;
                dcmpn <= ~decision_work;
                if (decision_work) begin
                    code_work = code_work | bit_mask(idx);
                end
            end
            for (int idx = BITS - 1; idx >= 1; idx--) begin
                dctrln[idx] <= code_work[idx];
                dctrlp[idx] <= ~code_work[idx];
            end
            dout <= code_work;
            eoc_int <= 1'b1;
        end
    end

endmodule
