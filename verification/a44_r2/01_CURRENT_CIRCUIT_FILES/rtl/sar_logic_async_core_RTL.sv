`timescale 1ns/1ps

`include "sar_logic_defs_RTL.svh"

module sar_logic_async_core_RTL (
    input  logic       CLKS,
    input  logic       DCMPP,
    input  logic       DCMPN,
    output logic       CMPCK,
    output logic [7:1] DCTRLP,
    output logic [7:1] DCTRLN,
    output logic [7:0] DOUT
);

    // DCTRLP/DCTRLN are active-low physical CDAC selector pins:
    //   0 -> VREFP
    //   1 -> VREFN
    // DOUT remains straight-binary: DOUT[k] = latched DCMPP.
    localparam logic [7:1] DCTRL_ACTIVE_LOW_RESET = `SAR_LOGIC_DCTRL_ACTIVE_LOW_RESET;

    logic [2:0] bit_index;
    logic [7:0] decision_reg;
    logic       done;
    logic       fault_hold;
    logic       sample_edge;
    logic       valid_state_clk;
    logic [7:1] dctrlp_q;
    logic [7:1] dctrln_q;
    logic [7:0] dout_q;
    logic       dcmpp_event_toggle;
    logic       dcmpn_event_toggle;
    logic       seen_dcmpp_toggle;
    logic       seen_dcmpn_toggle;

    wire in_hold      = ~CLKS;
    wire valid        = DCMPP | DCMPN;
    wire sampled_dcmpp = dcmpp_event_toggle ^ seen_dcmpp_toggle;
    wire sampled_dcmpn = dcmpn_event_toggle ^ seen_dcmpn_toggle;
    wire sampled_valid = sampled_dcmpp | sampled_dcmpn;
    wire sampled_fault = sampled_dcmpp & sampled_dcmpn;

`ifdef RTL_SIM
    assign #6 sample_edge = valid;
    assign #1 valid_state_clk = ~valid;
`else
    localparam int STATE_DLYB_STAGES = 6;
    localparam int HOLDOFF_DLYB_STAGES = 3;
    (* keep = "true", dont_touch = "true" *) logic [STATE_DLYB_STAGES:0] valid_dly;
    (* keep = "true", dont_touch = "true" *) logic [HOLDOFF_DLYB_STAGES:0] holdoff_dly;

    assign valid_dly[0] = valid;
    genvar valid_dly_i;
    generate
        for (valid_dly_i = 0; valid_dly_i < STATE_DLYB_STAGES; valid_dly_i = valid_dly_i + 1) begin : gen_valid_state_delay
            (* keep = "true", dont_touch = "true" *)
            gf180mcu_fd_sc_mcu7t5v0__dlyb_1 u_valid_state_delay (
                .I(valid_dly[valid_dly_i]),
                .Z(valid_dly[valid_dly_i + 1])
            );
        end
    endgenerate

    assign valid_state_clk = ~valid_dly[STATE_DLYB_STAGES];

    assign holdoff_dly[0] = sampled_valid;
    genvar holdoff_dly_i;
    generate
        for (holdoff_dly_i = 0; holdoff_dly_i < HOLDOFF_DLYB_STAGES; holdoff_dly_i = holdoff_dly_i + 1) begin : gen_holdoff_delay
            (* keep = "true", dont_touch = "true" *)
            gf180mcu_fd_sc_mcu7t5v0__dlyb_1 u_holdoff_delay (
                .I(holdoff_dly[holdoff_dly_i]),
                .Z(holdoff_dly[holdoff_dly_i + 1])
            );
        end
    endgenerate

    assign sample_edge = valid | sampled_valid | (|valid_dly) | (|holdoff_dly);
`endif

`ifdef RTL_SIM
    assign DCTRLP = dctrlp_q;
    assign DCTRLN = dctrln_q;
    assign DOUT   = dout_q;
`else
    genvar out_i;
    generate
        for (out_i = 1; out_i <= 7; out_i = out_i + 1) begin : gen_dctrl_outbuf
            (* keep = "true", dont_touch = "true" *)
            gf180mcu_fd_sc_mcu7t5v0__buf_4 u_dctrlp_buf (.I(dctrlp_q[out_i]), .Z(DCTRLP[out_i]));
            (* keep = "true", dont_touch = "true" *)
            gf180mcu_fd_sc_mcu7t5v0__buf_4 u_dctrln_buf (.I(dctrln_q[out_i]), .Z(DCTRLN[out_i]));
        end
        for (out_i = 0; out_i <= 7; out_i = out_i + 1) begin : gen_dout_outbuf
            (* keep = "true", dont_touch = "true" *)
            gf180mcu_fd_sc_mcu7t5v0__buf_2 u_dout_buf (.I(dout_q[out_i]), .Z(DOUT[out_i]));
        end
    endgenerate
`endif

    // Catch short StrongARM output pulses as event toggles. The SAR state
    // consumes the delta between the current and last-seen toggles on a
    // delayed VALID falling edge, so the event-toggle flops settle during
    // the StrongARM output pulse before the SAR state bank samples them.
    // A separate sampled-valid holdoff chain keeps CMPCK low after the
    // state update while DCTRL and the CDAC settle.
    always_ff @(posedge CLKS or posedge DCMPP) begin
        if (CLKS) begin
            dcmpp_event_toggle <= 1'b0;
        end else begin
            dcmpp_event_toggle <= ~dcmpp_event_toggle;
        end
    end

    always_ff @(posedge CLKS or posedge DCMPN) begin
        if (CLKS) begin
            dcmpn_event_toggle <= 1'b0;
        end else begin
            dcmpn_event_toggle <= ~dcmpn_event_toggle;
        end
    end

    assign CMPCK = in_hold & ~done & ~fault_hold & ~valid & ~sample_edge & ~sampled_valid;

    always_ff @(posedge CLKS or posedge valid_state_clk) begin
        if (CLKS) begin
            bit_index    <= 3'd0;
            decision_reg <= 8'h00;
            done         <= 1'b0;
            fault_hold   <= 1'b0;
            dctrlp_q     <= DCTRL_ACTIVE_LOW_RESET;
            dctrln_q     <= DCTRL_ACTIVE_LOW_RESET;
            seen_dcmpp_toggle <= 1'b0;
            seen_dcmpn_toggle <= 1'b0;
        end else begin
            if (sampled_fault) begin
                fault_hold <= 1'b1;
            end else if (sampled_valid & ~done) begin
                // A binary bit index avoids same-edge one-hot shift races in
                // transistor-level PEX while preserving the 7 DCTRL updates
                // followed by the D0-only DOUT/EOC update.
                unique case (bit_index)
                    3'd0: begin
                        decision_reg[7] <= sampled_dcmpp;
                        dctrlp_q[7]     <= sampled_dcmpp;
                        dctrln_q[7]     <= sampled_dcmpn;
                    end
                    3'd1: begin
                        decision_reg[6] <= sampled_dcmpp;
                        dctrlp_q[6]     <= sampled_dcmpp;
                        dctrln_q[6]     <= sampled_dcmpn;
                    end
                    3'd2: begin
                        decision_reg[5] <= sampled_dcmpp;
                        dctrlp_q[5]     <= sampled_dcmpp;
                        dctrln_q[5]     <= sampled_dcmpn;
                    end
                    3'd3: begin
                        decision_reg[4] <= sampled_dcmpp;
                        dctrlp_q[4]     <= sampled_dcmpp;
                        dctrln_q[4]     <= sampled_dcmpn;
                    end
                    3'd4: begin
                        decision_reg[3] <= sampled_dcmpp;
                        dctrlp_q[3]     <= sampled_dcmpp;
                        dctrln_q[3]     <= sampled_dcmpn;
                    end
                    3'd5: begin
                        decision_reg[2] <= sampled_dcmpp;
                        dctrlp_q[2]     <= sampled_dcmpp;
                        dctrln_q[2]     <= sampled_dcmpn;
                    end
                    3'd6: begin
                        decision_reg[1] <= sampled_dcmpp;
                        dctrlp_q[1]     <= sampled_dcmpp;
                        dctrln_q[1]     <= sampled_dcmpn;
                    end
                    default: begin
                        decision_reg[0] <= sampled_dcmpp;
                        dout_q          <= {dctrlp_q[7:1], sampled_dcmpp};
                        done            <= 1'b1;
                    end
                endcase
                if (bit_index != 3'd7) begin
                    bit_index <= bit_index + 3'd1;
                end
                seen_dcmpp_toggle <= dcmpp_event_toggle;
                seen_dcmpn_toggle <= dcmpn_event_toggle;
            end
        end
    end

endmodule
