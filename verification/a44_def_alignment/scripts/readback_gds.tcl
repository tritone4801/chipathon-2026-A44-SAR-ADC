# Read the repository-root A44_A GDS, restore logical ports, run full Magic
# DRC, and extract the hierarchy used by the fresh Netgen comparison.
foreach variable {A44_FINAL_GDS A44_RESTORE_PORTS A44_OUTPUT_DIR} {
    if {![info exists env($variable)]} { error "$variable is not defined" }
}

file mkdir $env(A44_OUTPUT_DIR)
cd $env(A44_OUTPUT_DIR)
crashbackups stop
drc off
gds readonly true
gds rescale false
gds read $env(A44_FINAL_GDS)
load A44_A -silent
source $env(A44_RESTORE_PORTS)
writeall force

set port_count 0
for {set port_index 0} {$port_index <= 100} {incr port_index} {
    if {[port $port_index name -quiet] ne ""} {
        incr port_count
    }
}
puts "A44_GDS_PORT_COUNT=$port_count"

drc on
drc euclidean on
drc style drc(full)
select top cell
box 0um 0um 1110um 1110um
drc check
drc catchup
puts "A44_GDS_DRC_BEGIN"
drc count total
puts "A44_GDS_DRC_END"
puts "A44_GDS_DRC_WHY=[drc listall why]"

extract do local
extract all
ext2spice lvs
ext2spice subcircuits top on
ext2spice format ngspice
ext2spice scale off
ext2spice cthresh infinite
ext2spice rthresh infinite
ext2spice hierarchy on
ext2spice merge none
ext2spice -o A44_A_GDS_READBACK.spice A44_A
puts "A44_GDS_READBACK_COMPLETE=1"
quit -noprompt
