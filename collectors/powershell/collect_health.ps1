# collect_health.ps1
# PowerShell collector for Windows.
# Collects system health data and outputs a v1.1 schema-compliant JSON to stdout.
# Called by powershell_collector.py via subprocess.
#
# Output: single JSON string to stdout — Python reads and parses this.
# Errors:  written to stderr — Python checks for these separately.

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Thresholds ────────────────────────────────────────────────────────────────
$CPU_WARN  = 80
$MEM_WARN  = 80
$DISK_WARN = 85

# ── Helpers ───────────────────────────────────────────────────────────────────

function Get-Status($value, $threshold) {
    if ($value -ge $threshold) { return "WARNING" } else { return "OK" }
}

# ── Metadata ──────────────────────────────────────────────────────────────────

$metadata = @{
    timestamp      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hostname       = $env:COMPUTERNAME
    os_type        = "Windows"
    os_version     = (Get-WmiObject Win32_OperatingSystem).Caption
    executor       = "PowerShell_Collector_v1"
    schema_version = "1.1"
}

# ── CPU ───────────────────────────────────────────────────────────────────────
# Uses Performance Counter (Cooked Value = cumulative average) — closest to psutil

try {
    $cpuSample  = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 2).CounterSamples
    $cpuUsage   = [math]::Round(($cpuSample | Measure-Object CookedValue -Average).Average, 1)
    $cpuCores   = (Get-WmiObject Win32_ComputerSystem).NumberOfLogicalProcessors
    $cpuStatus  = Get-Status $cpuUsage $CPU_WARN
    $cpuMessage = if ($cpuStatus -eq "WARNING") { "CPU at $cpuUsage% — above threshold" } else { "Normal" }
    $cpu = @{
        usage_pct  = $cpuUsage
        core_count = [int]$cpuCores
        status     = $cpuStatus
        message    = $cpuMessage
    }
} catch {
    $cpu = @{ usage_pct = $null; core_count = $null; status = "WARNING"; message = "Could not retrieve CPU data: $_" }
}

# ── Memory ────────────────────────────────────────────────────────────────────

try {
    $os        = Get-WmiObject Win32_OperatingSystem
    $totalGb   = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
    $freeGb    = [math]::Round($os.FreePhysicalMemory      / 1MB, 1)
    $usedGb    = [math]::Round($totalGb - $freeGb, 1)
    $memPct    = [math]::Round(($usedGb / $totalGb) * 100, 1)
    $memStatus = Get-Status $memPct $MEM_WARN
    $memory = @{
        usage_pct = $memPct
        used_gb   = $usedGb
        total_gb  = $totalGb
        status    = $memStatus
        message   = if ($memStatus -eq "WARNING") { "Memory at $memPct% — above threshold" } else { "Normal" }
    }
} catch {
    $memory = @{ usage_pct = $null; used_gb = $null; total_gb = $null; status = "WARNING"; message = "Could not retrieve memory data: $_" }
}

# ── Disk ──────────────────────────────────────────────────────────────────────

try {
    $diskRaw   = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'"
    $totalGb   = [math]::Round($diskRaw.Size      / 1GB, 1)
    $freeGb    = [math]::Round($diskRaw.FreeSpace  / 1GB, 1)
    $usedGb    = [math]::Round($totalGb - $freeGb, 1)
    $diskPct   = [math]::Round(($usedGb / $totalGb) * 100, 1)
    $diskStatus = Get-Status $diskPct $DISK_WARN
    $disk = @{
        usage_pct = $diskPct
        used_gb   = $usedGb
        total_gb  = $totalGb
        status    = $diskStatus
        message   = if ($diskStatus -eq "WARNING") { "Disk at $diskPct% — above threshold" } else { "Normal" }
    }
} catch {
    $disk = @{ usage_pct = $null; used_gb = $null; total_gb = $null; status = "WARNING"; message = "Could not retrieve disk data: $_" }
}

# ── Services ──────────────────────────────────────────────────────────────────

$serviceTargets = @("Spooler", "wuauserv")
$services = @()

foreach ($svcName in $serviceTargets) {
    try {
        $svc     = Get-Service -Name $svcName -ErrorAction SilentlyContinue
        $running = ($svc -ne $null) -and ($svc.Status -eq "Running")
        $entry   = @{
            name    = $svcName
            running = $running
            status  = if ($running) { "OK" } else { "WARNING" }
        }
        if (-not $running) {
            $entry["message"] = "Service '$svcName' not found or not running"
        }
        $services += $entry
    } catch {
        $services += @{ name = $svcName; running = $false; status = "WARNING"; message = "Error checking service: $_" }
    }
}

# ── Network ───────────────────────────────────────────────────────────────────

try {
    $null = [System.Net.Dns]::GetHostAddresses("google.com")
    $network = @{ connected = $true;  status = "OK";      message = "Connected" }
} catch {
    $network = @{ connected = $false; status = "WARNING"; message = "DNS resolution failed — no internet connectivity" }
}

# ── Assemble checks ───────────────────────────────────────────────────────────

$checks = @{
    system_resources = @{
        cpu    = $cpu
        memory = $memory
        disk   = $disk
    }
    services = $services
    network  = $network
}

# ── Summary ───────────────────────────────────────────────────────────────────

$allStatuses = @(
    $cpu.status
    $memory.status
    $disk.status
    $network.status
) + ($services | ForEach-Object { $_.status })

$alertCount   = ($allStatuses | Where-Object { $_ -eq "WARNING" }).Count
$overallStatus = if ($alertCount -gt 0) { "WARNING" } else { "OK" }

$summary = @{
    overall_status = $overallStatus
    alert_count    = $alertCount
}

# ── Output ────────────────────────────────────────────────────────────────────
# ConvertTo-Json -Depth 10 ensures nested objects are fully serialized.
# Python reads this from stdout and parses with json.loads().

@{
    report_metadata = $metadata
    summary         = $summary
    checks          = $checks
} | ConvertTo-Json -Depth 10 -Compress
