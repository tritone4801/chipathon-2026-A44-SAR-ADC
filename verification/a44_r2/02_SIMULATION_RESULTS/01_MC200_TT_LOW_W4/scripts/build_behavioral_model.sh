#!/usr/bin/env bash
set -euo pipefail

ROOT="/foss/designs/manual_goal/verification/A44_TT_BEH_NO_R6_MC200_FAST64_SIGNOFF_20260718"
MODEL="SAR_LOGIC_BEH_TT_3P3_27C"
MODEL_DIR="$ROOT/models"
OBJ_DIR="$MODEL_DIR/obj_dir"
NGSPICE_COSIM_SRC="/foss/tools/ngspice/share/ngspice/scripts/src"

cd "$MODEL_DIR"
rm -rf "$OBJ_DIR"

iverilog -g2012 -s "$MODEL" -o "$MODEL.ivvp" "$MODEL.v"
verilator --Mdir "$OBJ_DIR" --prefix Vlng --top-module "$MODEL" \
  --CFLAGS "-fpic" --cc --timing --no-sched-zero-delay "$MODEL.v"

sed -nE 's/.*VL_IN([0-9]+)\(\&([^,]+),([0-9]+),([0-9]+)\);/VL_DATA(\1,\2,\3,\4)/p' \
  "$OBJ_DIR/Vlng.h" > "$OBJ_DIR/inputs.h"
sed -nE 's/.*VL_OUT([0-9]+)\(\&([^,]+),([0-9]+),([0-9]+)\);/VL_DATA(\1,\2,\3,\4)/p' \
  "$OBJ_DIR/Vlng.h" > "$OBJ_DIR/outputs.h"
sed -nE 's/.*VL_INOUT([0-9]+)\(\&([^,]+),([0-9]+),([0-9]+)\);/VL_DATA(\1,\2,\3,\4)/p' \
  "$OBJ_DIR/Vlng.h" > "$OBJ_DIR/inouts.h"

verilator --Mdir "$OBJ_DIR" --prefix Vlng --top-module "$MODEL" \
  --CFLAGS "-I$NGSPICE_COSIM_SRC -DWITH_TIMING -fpic" \
  --cc --build --exe --timing --no-sched-zero-delay \
  "$NGSPICE_COSIM_SRC/verilator_main.cpp" \
  "$NGSPICE_COSIM_SRC/verilator_shim.cpp" \
  "$MODEL.v"

g++ --shared \
  "$OBJ_DIR/verilator_shim.o" \
  "$OBJ_DIR/verilated.o" \
  "$OBJ_DIR/verilated_threads.o" \
  "$OBJ_DIR/verilated_timing.o" \
  "$OBJ_DIR/Vlng__ALL.a" \
  -pthread -lpthread -latomic -o "$MODEL.so"

nm -D "$MODEL.so" | grep ' Cosim_setup$'
file "$MODEL.so"
