# Tune PA drive (V6 amplitude) to hit 50W output.
# Reads netlist.cir, sweeps V6, computes V(Pr1) RMS -> power into 450 ohm load.

$ngspice = "D:\Program Files\Qucs-S\bin\ngspice_con.exe"
$src = "C:\Users\AlAnd\QucsWorkspace\xmitter_prj\netlist.cir"
$work = "$env:TEMP\tune_drive.cir"
$out = "C:\Users\AlAnd\QucsWorkspace\xmitter_prj\tune_pr1.dat"

# Start with the existing netlist but strip the AC analysis + replace write with wrdata
$base = Get-Content $src -Raw

# Clean .control block: just one transient, dump v(pr1) text
$newctrl = @"
.control
tran 2.0202e-09 0.0010002 0.001  uic
wrdata $($out -replace '\\','/') v(pr1) v(pr10)
exit
.endc
"@

$base = $base -replace "(?s)\.control.*?\.endc", $newctrl

# Sweep Vp (V5) with V6 fixed at 200V (well into saturation)
$vp_values = @(550, 580, 600, 625, 650, 700)
$v6 = 200

"Vp(V)`tV_rms(V)`tP_out(W)`tVp_min(V)`tVp_max(V)"

foreach ($vp in $vp_values) {
    # Patch V6 amplitude and V5 (plate supply)
    $patched = $base -replace "V6 _net6 _net11 DC 0 SIN\(0 [\d\.]+", "V6 _net6 _net11 DC 0 SIN(0 $v6"
    $patched = $patched -replace "AC [\d\.]+ ACPHASE", "AC $v6 ACPHASE"
    $patched = $patched -replace "V5 _net18 0 DC \d+", "V5 _net18 0 DC $vp"
    # also update the IC for plate nodes
    $patched = $patched -replace "v\(_net0\) = \d+", "v(_net0) = $vp"
    $patched = $patched -replace "v\(_net7\) = \d+", "v(_net7) = $vp"
    Set-Content -Path $work -Value $patched -Encoding ASCII

    # Run ngspice silently
    & $ngspice -b $work 2>&1 | Out-Null

    # Read the wrdata output: two-column text (time, v(pr1))
    if (-not (Test-Path $out)) {
        "$v6`tFAILED - no output file"
        continue
    }
    $rows = Get-Content $out
    $times = @(); $vs = @(); $vp10 = @()
    foreach ($r in $rows) {
        $cols = ($r -split '\s+') | Where-Object { $_ -ne '' }
        # wrdata format: t, v(pr1), t, v(pr10)
        if ($cols.Count -ge 4) {
            $times += [double]$cols[0]; $vs += [double]$cols[1]; $vp10 += [double]$cols[3]
        }
    }
    if ($vs.Count -lt 2) { "$v6`tFAILED - no data rows"; continue }

    # Use last 70% of samples (steady state)
    $start = [int]($vs.Count * 0.3)
    $window_t = $times[$start..($times.Count - 1)]
    $window_v = $vs[$start..($vs.Count - 1)]

    # Trapezoidal RMS over the window
    $sq_total = 0.0; $dt_total = 0.0
    for ($i = 1; $i -lt $window_t.Count; $i++) {
        $dt = $window_t[$i] - $window_t[$i-1]
        $avg_sq = ($window_v[$i]*$window_v[$i] + $window_v[$i-1]*$window_v[$i-1]) / 2
        $sq_total += $avg_sq * $dt
        $dt_total += $dt
    }
    $vrms = [math]::Sqrt($sq_total / $dt_total)
    $power = $vrms * $vrms / 450
    $vp_window = $vp10[$start..($vp10.Count - 1)]
    $vp_min = ($vp_window | Measure-Object -Minimum).Minimum
    $vp_max = ($vp_window | Measure-Object -Maximum).Maximum
    "{0,5}`t{1,7:F2}`t{2,7:F2}`t{3,7:F1}`t{4,7:F1}" -f $vp, $vrms, $power, $vp_min, $vp_max
}
