$ErrorActionPreference = 'Stop'
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Container = 'iic-osic-tools_a44_xvnc'
$Resolved = (Resolve-Path -LiteralPath $PackageRoot).Path
$WorkspaceRoot = 'D:\PICO'

if ($Resolved.StartsWith($WorkspaceRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    $Relative = $Resolved.Substring($WorkspaceRoot.Length).TrimStart('\').Replace('\', '/')
    $ContainerPath = "/foss/designs/$Relative"
    docker exec $Container bash --noprofile --norc -lc "cd '$ContainerPath' && make -C 03_CACE_AND_SIMULATION_TOOLS quick-verify"
} else {
    docker run --rm -v "${Resolved}:/foss/designs/a44_repro" -w /foss/designs/a44_repro hpretl/iic-osic-tools:chipathon26 bash --noprofile --norc -lc "make -C 03_CACE_AND_SIMULATION_TOOLS quick-verify"
}

if ($LASTEXITCODE -ne 0) {
    throw "A44 quick verification failed with exit code $LASTEXITCODE"
}
