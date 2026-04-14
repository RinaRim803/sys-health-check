# Collectors.psm1
# PowerShell collection functions for sys-health-check.
#
# Each function collects one check type and returns a hashtable
# that matches the v1.1 JSON schema structure.
#
# Thresholds and service targets are loaded from config.json
# at the project root — shared with the Python collector.
#
# Imported by collect_health.ps1:
#   Import-Module "$PSScriptRoot/Collectors.psm1" -Force


# ── Config loader ─────────────────────────────────────────────────────────────

function Get-HealthConfig {
    <#
    .SYNOPSIS
        Load and return config.json from the project root.
        Cached after first call — reads file only once per session.
    #>
    if (-not $script:_config) {
        $configPath      = Join-Path $PSScriptRoot "..\..\config.json"
        $script:_config  = Get-Content -Path $configPath -Raw | ConvertFrom-Json
    }
    return $script:_config
}


# ── Internal helper ───────────────────────────────────────────────────────────

function Get-CheckStatus($value, $threshold) {
    if ($value -ge $threshold) { return "WARNING" } else { return "OK" }
}


# ── Collection functions ──────────────────────────────────────────────────────

function Get-CpuInfo {
    <#
    .SYNOPSIS
        Collect CPU usage using Performance Counter (Cooked Value average).
        Two samples taken and averaged — closest to psutil's interval-based method.
    #>
    $cfg = Get-HealthConfig

    try {
        $samples  = (Get-Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 2).CounterSamples
        $usage    = [math]::Round(($samples | Measure-Object CookedValue -Average).Average, 1)
        $cores    = [int](Get-WmiObject Win32_ComputerSystem).NumberOfLogicalProcessors
        $status   = Get-CheckStatus $usage $cfg.thresholds.cpu_warning_pct
        return @{
            usage_pct  = $usage
            core_count = $cores
            status     = $status
            message    = if ($status -eq "WARNING") { "CPU at $usage% — above threshold" } else { "Normal" }
        }
    } catch {
        return @{ usage_pct = $null; core_count = $null; status = "WARNING"; message = "Could not retrieve CPU data: $_" }
    }
}


function Get-MemoryInfo {
    <#
    .SYNOPSIS
        Collect memory usage via WMI Win32_OperatingSystem.
    #>
    $cfg = Get-HealthConfig

    try {
        $os      = Get-WmiObject Win32_OperatingSystem
        $totalGb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
        $freeGb  = [math]::Round($os.FreePhysicalMemory      / 1MB, 1)
        $usedGb  = [math]::Round($totalGb - $freeGb, 1)
        $pct     = [math]::Round(($usedGb / $totalGb) * 100, 1)
        $status  = Get-CheckStatus $pct $cfg.thresholds.memory_warning_pct
        return @{
            usage_pct = $pct
            used_gb   = $usedGb
            total_gb  = $totalGb
            status    = $status
            message   = if ($status -eq "WARNING") { "Memory at $pct% — above threshold" } else { "Normal" }
        }
    } catch {
        return @{ usage_pct = $null; used_gb = $null; total_gb = $null; status = "WARNING"; message = "Could not retrieve memory data: $_" }
    }
}


function Get-DiskInfo {
    <#
    .SYNOPSIS
        Collect disk usage for the C: drive via WMI Win32_LogicalDisk.
    #>
    $cfg = Get-HealthConfig

    try {
        $disk    = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'"
        $totalGb = [math]::Round($disk.Size      / 1GB, 1)
        $freeGb  = [math]::Round($disk.FreeSpace  / 1GB, 1)
        $usedGb  = [math]::Round($totalGb - $freeGb, 1)
        $pct     = [math]::Round(($usedGb / $totalGb) * 100, 1)
        $status  = Get-CheckStatus $pct $cfg.thresholds.disk_warning_pct
        return @{
            usage_pct = $pct
            used_gb   = $usedGb
            total_gb  = $totalGb
            status    = $status
            message   = if ($status -eq "WARNING") { "Disk at $pct% — above threshold" } else { "Normal" }
        }
    } catch {
        return @{ usage_pct = $null; used_gb = $null; total_gb = $null; status = "WARNING"; message = "Could not retrieve disk data: $_" }
    }
}


function Get-ServicesInfo {
    <#
    .SYNOPSIS
        Check whether key Windows services are running.
        Service targets are loaded from config.json — no hardcoding.
    #>
    $cfg      = Get-HealthConfig
    $targets  = $cfg.services.Windows
    $results  = @()

    foreach ($svcName in $targets) {
        try {
            $svc     = Get-Service -Name $svcName -ErrorAction SilentlyContinue
            $running = ($null -ne $svc) -and ($svc.Status -eq "Running")
            $entry   = @{
                name    = $svcName
                running = $running
                status  = if ($running) { "OK" } else { "WARNING" }
            }
            if (-not $running) {
                $entry["message"] = "Service '$svcName' not found or not running"
            }
            $results += $entry
        } catch {
            $results += @{ name = $svcName; running = $false; status = "WARNING"; message = "Error: $_" }
        }
    }
    return $results
}


function Get-NetworkInfo {
    <#
    .SYNOPSIS
        Check internet connectivity via DNS resolution.
        DNS target and timeout are loaded from config.json.
    #>
    $cfg = Get-HealthConfig

    try {
        $null = [System.Net.Dns]::GetHostAddresses($cfg.network.dns_check_host)
        return @{ connected = $true;  status = "OK";      message = "Connected" }
    } catch {
        return @{ connected = $false; status = "WARNING"; message = "DNS resolution failed — no internet connectivity" }
    }
}


# ── Exports ───────────────────────────────────────────────────────────────────

Export-ModuleMember -Function Get-CpuInfo, Get-MemoryInfo, Get-DiskInfo, Get-ServicesInfo, Get-NetworkInfo