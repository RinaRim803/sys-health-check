# collect_health.ps1
# PowerShell collector entry point for sys-health-check.
#
# This script is the orchestrator — it imports Collectors.psm1,
# calls each collection function, assembles the v1.1 schema dict,
# and outputs it as JSON to stdout.
#
# All collection logic lives in Collectors.psm1 (sibling in this folder).
# All thresholds and service targets live in config.json (project root).
#
# Called by collectors/powershell/collector.py via subprocess:
#   powershell -File collect_health.ps1
#   → stdout JSON → json.loads() → Python dict

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Import collection module ───────────────────────────────────────────────────
Import-Module "$PSScriptRoot/Collectors.psm1" -Force


# ── Metadata ──────────────────────────────────────────────────────────────────
$metadata = @{
    timestamp      = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    hostname       = $env:COMPUTERNAME
    os_type        = "Windows"
    os_version     = (Get-WmiObject Win32_OperatingSystem).Caption
    executor       = "PowerShell_Collector_v1"
    schema_version = "1.1"
}


# ── Run collectors ────────────────────────────────────────────────────────────
$cpu      = Get-CpuInfo
$memory   = Get-MemoryInfo
$disk     = Get-DiskInfo
$services = Get-ServicesInfo
$network  = Get-NetworkInfo


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

$alertCount    = ($allStatuses | Where-Object { $_ -eq "WARNING" }).Count
$overallStatus = if ($alertCount -gt 0) { "WARNING" } else { "OK" }


# ── Output to stdout ──────────────────────────────────────────────────────────
# Python reads this via subprocess stdout → json.loads()
@{
    report_metadata = $metadata
    summary         = @{ overall_status = $overallStatus; alert_count = $alertCount }
    checks          = $checks
} | ConvertTo-Json -Depth 10 -Compress