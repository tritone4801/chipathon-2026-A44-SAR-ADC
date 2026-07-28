`timescale 1ps/1ps

module SAR_LOGIC_BEH_TT_3P3_27C(
    input wire CLKS,
    input wire DCMPP,
    input wire DCMPN,
    output reg CMPCK,
    output wire DCTRLP7,
    output wire DCTRLP6,
    output wire DCTRLP5,
    output wire DCTRLP4,
    output wire DCTRLP3,
    output wire DCTRLP2,
    output wire DCTRLP1,
    output wire DCTRLN7,
    output wire DCTRLN6,
    output wire DCTRLN5,
    output wire DCTRLN4,
    output wire DCTRLN3,
    output wire DCTRLN2,
    output wire DCTRLN1,
    output reg [7:0] DOUT,
    output reg EOC_INT,
    output reg [7:0] INVALID_DECISION_COUNT,
    output reg [7:0] TIMEOUT_COUNT,
    output reg CONVERSION_COMPLETE
);
    integer generation;
    integer conversion_active;
    reg [7:1] dctrlp_state;
    reg [7:1] dctrln_state;

    assign DCTRLP7 = dctrlp_state[7];
    assign DCTRLP6 = dctrlp_state[6];
    assign DCTRLP5 = dctrlp_state[5];
    assign DCTRLP4 = dctrlp_state[4];
    assign DCTRLP3 = dctrlp_state[3];
    assign DCTRLP2 = dctrlp_state[2];
    assign DCTRLP1 = dctrlp_state[1];
    assign DCTRLN7 = dctrln_state[7];
    assign DCTRLN6 = dctrln_state[6];
    assign DCTRLN5 = dctrln_state[5];
    assign DCTRLN4 = dctrln_state[4];
    assign DCTRLN3 = dctrln_state[3];
    assign DCTRLN2 = dctrln_state[2];
    assign DCTRLN1 = dctrln_state[1];

    function automatic integer cmpck_high_ps(input integer bit_index);
        case (bit_index)
            7: cmpck_high_ps = 13890;
            6: cmpck_high_ps = 13878;
            5: cmpck_high_ps = 13891;
            4: cmpck_high_ps = 13891;
            3: cmpck_high_ps = 13878;
            2: cmpck_high_ps = 13879;
            1: cmpck_high_ps = 13892;
            default: cmpck_high_ps = 13878;
        endcase
    endfunction

    function automatic integer decision_aperture_ps(input integer bit_index);
        case (bit_index)
            7: decision_aperture_ps = 914;
            6: decision_aperture_ps = 824;
            5: decision_aperture_ps = 914;
            4: decision_aperture_ps = 914;
            3: decision_aperture_ps = 825;
            2: decision_aperture_ps = 825;
            1: decision_aperture_ps = 914;
            default: decision_aperture_ps = 824;
        endcase
    endfunction

    function automatic integer dctrl_from_rise_ps(input integer bit_index);
        case (bit_index)
            7: dctrl_from_rise_ps = 7911;
            6: dctrl_from_rise_ps = 7931;
            5: dctrl_from_rise_ps = 8022;
            4: dctrl_from_rise_ps = 8023;
            3: dctrl_from_rise_ps = 7934;
            2: dctrl_from_rise_ps = 7935;
            default: dctrl_from_rise_ps = 8025;
        endcase
    endfunction

    function automatic integer low_guard_ps(input integer bit_index);
        case (bit_index)
            7: low_guard_ps = 11560;
            6: low_guard_ps = 11575;
            5: low_guard_ps = 11576;
            4: low_guard_ps = 11560;
            3: low_guard_ps = 11560;
            2: low_guard_ps = 11577;
            default: low_guard_ps = 11574;
        endcase
    endfunction

    task automatic reset_sampling_controls;
        begin
            dctrlp_state = 7'b1000000;
            dctrln_state = 7'b1000000;
        end
    endtask

    task automatic abort_if_stale(input integer my_generation, output reg aborted);
        begin
            aborted = (my_generation != generation) || (CLKS !== 1'b0);
        end
    endtask

    task automatic run_conversion(input integer my_generation);
        integer bit_index;
        integer decision_bit;
        reg aborted;
        integer elapsed_ps;
        reg [7:0] code_work;
        begin
            code_work = 8'h00;
            #(11050);
            abort_if_stale(my_generation, aborted);
            if (!aborted) begin
                for (bit_index = 7; bit_index >= 0; bit_index = bit_index - 1) begin
                    CMPCK = 1'b1;
                    elapsed_ps = 0;

                    #(decision_aperture_ps(bit_index));
                    elapsed_ps = decision_aperture_ps(bit_index);
                    abort_if_stale(my_generation, aborted);
                    if (aborted) begin
                        bit_index = -1;
                    end else begin
                        if ((DCMPP === 1'b1) && (DCMPN === 1'b0)) begin
                            decision_bit = 1;
                        end else if ((DCMPP === 1'b0) && (DCMPN === 1'b1)) begin
                            decision_bit = 0;
                        end else begin
                            #(5000);
                            elapsed_ps = elapsed_ps + 5000;
                            abort_if_stale(my_generation, aborted);
                            if (!aborted && (DCMPP === 1'b1) && (DCMPN === 1'b0)) begin
                                decision_bit = 1;
                            end else if (!aborted && (DCMPP === 1'b0) && (DCMPN === 1'b1)) begin
                                decision_bit = 0;
                            end else begin
                                if (!aborted && (DCMPP === 1'b1) && (DCMPN === 1'b1)) begin
                                    INVALID_DECISION_COUNT = INVALID_DECISION_COUNT + 1'b1;
                                end else if (!aborted) begin
                                    TIMEOUT_COUNT = TIMEOUT_COUNT + 1'b1;
                                end
                                aborted = 1;
                                generation = generation + 1;
                                conversion_active = 0;
                                CMPCK = 1'b0;
                                EOC_INT = 1'b0;
                                CONVERSION_COMPLETE = 1'b0;
                            end
                        end

                        if (!aborted) begin
                            code_work[bit_index] = decision_bit[0];
                            if (bit_index > 0) begin
                                #(dctrl_from_rise_ps(bit_index) - elapsed_ps);
                                elapsed_ps = dctrl_from_rise_ps(bit_index);
                                abort_if_stale(my_generation, aborted);
                                if (!aborted) begin
                                    dctrlp_state[bit_index] = decision_bit[0];
                                    dctrln_state[bit_index] = ~decision_bit[0];
                                end
                            end else begin
                                #(10633 - elapsed_ps);
                                elapsed_ps = 10633;
                                abort_if_stale(my_generation, aborted);
                                if (!aborted) begin
                                    DOUT = code_work;
                                    EOC_INT = 1'b1;
                                    CONVERSION_COMPLETE = 1'b1;
                                end
                            end

                            if (!aborted) begin
                                #(cmpck_high_ps(bit_index) - elapsed_ps);
                                CMPCK = 1'b0;
                                if (bit_index > 0) begin
                                    #(low_guard_ps(bit_index));
                                    abort_if_stale(my_generation, aborted);
                                end else begin
                                    conversion_active = 0;
                                end
                            end
                        end
                    end
                end
            end
        end
    endtask

    initial begin
        generation = 0;
        conversion_active = 0;
        CMPCK = 1'b0;
        DOUT = 8'h00;
        EOC_INT = 1'b0;
        INVALID_DECISION_COUNT = 8'h00;
        TIMEOUT_COUNT = 8'h00;
        CONVERSION_COMPLETE = 1'b0;
        reset_sampling_controls();
    end

    always @(posedge CLKS) begin
        generation = generation + 1;
        if (conversion_active != 0) begin
            TIMEOUT_COUNT = TIMEOUT_COUNT + 1'b1;
        end
        conversion_active = 0;
        CMPCK = 1'b0;
        EOC_INT = 1'b0;
        CONVERSION_COMPLETE = 1'b0;
        reset_sampling_controls();
    end

    always @(negedge CLKS) begin
        generation = generation + 1;
        conversion_active = 1;
        CMPCK = 1'b0;
        EOC_INT = 1'b0;
        CONVERSION_COMPLETE = 1'b0;
        INVALID_DECISION_COUNT = 8'h00;
        TIMEOUT_COUNT = 8'h00;
        reset_sampling_controls();
        fork
            run_conversion(generation);
        join_none
    end
endmodule
