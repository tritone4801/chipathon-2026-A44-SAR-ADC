# Read the repository A44_A DEF against its frozen child and the GF180
# standard-cell library, then run full Magic DRC and extract for Netgen.
foreach variable {A44_FINAL_DEF A44_CORE_GDS A44_SC_GDS A44_OUTPUT_DIR} {
    if {![info exists env($variable)]} { error "$variable is not defined" }
}

file mkdir $env(A44_OUTPUT_DIR)
cd $env(A44_OUTPUT_DIR)
crashbackups stop
drc off
gds readonly true
gds rescale false
gds read $env(A44_CORE_GDS)
gds read $env(A44_SC_GDS)
def read $env(A44_FINAL_DEF)
load A44_A -silent
property FIXED_BBOX {0 0 22200 22200}
save A44_A
writeall force

drc on
drc euclidean on
drc style drc(full)
select top cell
box 0um 0um 1110um 1110um
drc check
drc catchup
puts "A44_DEF_DRC_BEGIN"
drc count total
puts "A44_DEF_DRC_END"
puts "A44_DEF_DRC_WHY=[drc listall why]"

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
ext2spice -o A44_A_DEF_READBACK.spice A44_A
puts "A44_DEF_READBACK_COMPLETE=1"
quit -noprompt
