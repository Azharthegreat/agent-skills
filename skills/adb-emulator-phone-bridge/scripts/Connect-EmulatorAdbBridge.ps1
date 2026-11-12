[CmdletBinding()]
param(
    [ValidateSet('Status', 'Connect', 'Disconnect')]
    [string]$Action = 'Status',

    [string]$PhoneSerial,

    [string]$EmulatorSerial,

    [ValidateRange(1, 65535)]
    [int]$PhonePort,

    [ValidateRange(1, 65535)]
    [int]$HostAdbPort,

    [string]$AdbPath,

    [ValidateRange(0, 60)]
    [int]$WaitSeconds = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Resolve-AdbExecutable {
    param([string]$RequestedPath)

    if ($RequestedPath) {
        $resolvedRequestedPath = Resolve-Path -LiteralPath $RequestedPath -ErrorAction Stop
        return $resolvedRequestedPath.Path
    }

    $command = Get-Command adb.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        return $command.Source
    }

    $localAppDataPath = [Environment]::GetFolderPath('LocalApplicationData')
    $standardPath = Join-Path $localAppDataPath 'Android\Sdk\platform-tools\adb.exe'
    if (Test-Path -LiteralPath $standardPath -PathType Leaf) {
        return (Resolve-Path -LiteralPath $standardPath).Path
    }

    throw 'adb.exe was not found. Install Android SDK Platform-Tools or pass -AdbPath.'
}

function Invoke-Adb {
    param(
        [Parameter(Mandatory)]
        [string[]]$CommandArguments,

        [switch]$AllowFailure
    )

    $capturedOutput = @(& $script:ResolvedAdb @CommandArguments 2>&1)
    $commandExitCode = $LASTEXITCODE
    $outputText = ($capturedOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine

    if (-not $AllowFailure -and $commandExitCode -ne 0) {
        throw "adb command failed with exit code ${commandExitCode}: adb $($CommandArguments -join ' ')`n$outputText"
    }

    [pscustomobject]@{
        ExitCode = $commandExitCode
        Text = $outputText
        Lines = @($capturedOutput | ForEach-Object { $_.ToString() })
    }
}

function Get-AdbDeviceRows {
    $deviceResult = Invoke-Adb -CommandArguments @('devices', '-l')
    $rows = foreach ($line in $deviceResult.Lines) {
        if ($line -match '^([^\s]+)\s+([^\s]+)(?:\s+(.*))?$' -and $Matches[1] -ne 'List') {
            $serial = $Matches[1]
            $state = $Matches[2]
            $details = if ($Matches.Count -ge 4) { $Matches[3] } else { '' }
            $modelMatch = [regex]::Match($details, '(?:^|\s)model:([^\s]+)')
            $productMatch = [regex]::Match($details, '(?:^|\s)product:([^\s]+)')
            $deviceMatch = [regex]::Match($details, '(?:^|\s)device:([^\s]+)')
            $model = if ($modelMatch.Success) { $modelMatch.Groups[1].Value } else { '' }
            $product = if ($productMatch.Success) { $productMatch.Groups[1].Value } else { '' }
            $deviceName = if ($deviceMatch.Success) { $deviceMatch.Groups[1].Value } else { '' }

            [pscustomobject]@{
                Serial = $serial
                State = $state
                Model = $model
                Product = $product
                Device = $deviceName
                IsEmulator = $serial -match '^emulator-\d+$'
                Raw = $line
            }
        }
    }

    @($rows)
}

function Wait-ForAdbTargets {
    param(
        [string]$RequiredPhoneSerial,
        [string]$RequiredEmulatorSerial,
        [int]$MaximumWaitSeconds
    )

    $deadline = (Get-Date).AddSeconds($MaximumWaitSeconds)
    do {
        $rows = Get-AdbDeviceRows
        $phoneReady = -not $RequiredPhoneSerial -or ($rows | Where-Object {
            $_.Serial -eq $RequiredPhoneSerial -and $_.State -eq 'device'
        })
        $emulatorReady = -not $RequiredEmulatorSerial -or ($rows | Where-Object {
            $_.Serial -eq $RequiredEmulatorSerial -and $_.State -eq 'device'
        })

        if ($phoneReady -and $emulatorReady) {
            return $rows
        }

        if ((Get-Date) -ge $deadline) {
            return $rows
        }

        Start-Sleep -Seconds 1
    } while ($true)
}

function Get-TargetRow {
    param(
        [object[]]$Rows,
        [string]$RequestedSerial,
        [bool]$WantEmulator,
        [string]$Label
    )

    $onlineCandidates = @($Rows | Where-Object {
        $_.State -eq 'device' -and $_.IsEmulator -eq $WantEmulator
    })

    if ($RequestedSerial) {
        $selected = @($onlineCandidates | Where-Object { $_.Serial -eq $RequestedSerial })
        if ($selected.Count -ne 1) {
            $knownState = $Rows | Where-Object { $_.Serial -eq $RequestedSerial } | Select-Object -First 1
            if ($knownState) {
                throw "$Label '$RequestedSerial' is present but has state '$($knownState.State)', not 'device'."
            }
            throw "$Label '$RequestedSerial' is not available."
        }
        return $selected[0]
    }

    if ($onlineCandidates.Count -eq 1) {
        return $onlineCandidates[0]
    }
    if ($onlineCandidates.Count -eq 0) {
        throw "No online $Label was found."
    }

    $candidateList = ($onlineCandidates | ForEach-Object { $_.Serial }) -join ', '
    throw "Multiple online ${Label}s were found: $candidateList. Pass the exact serial explicitly."
}

function Get-DeviceProperty {
    param(
        [string]$Serial,
        [string]$Property
    )

    (Invoke-Adb -CommandArguments @('-s', $Serial, 'shell', 'getprop', $Property)).Text.Trim()
}

function Get-ReverseMappings {
    param([string]$Serial)

    $mappingResult = Invoke-Adb -CommandArguments @('-s', $Serial, 'reverse', '--list')
    @($mappingResult.Lines | Where-Object { $_.Trim() })
}

function Test-ReverseMapping {
    param(
        [string[]]$Mappings,
        [int]$DevicePort,
        [int]$HostPort
    )

    $expectedPattern = "tcp:$DevicePort\s+tcp:$HostPort(?:\s|$)"
    [bool]($Mappings | Where-Object { $_ -match $expectedPattern })
}

function Resolve-EmulatorAdbPort {
    param(
        [string]$Serial,
        [int]$RequestedPort
    )

    if ($RequestedPort -gt 0) {
        return $RequestedPort
    }

    $reportedPort = Get-DeviceProperty -Serial $Serial -Property 'service.adb.tcp.port'
    $parsedReportedPort = 0
    if ([int]::TryParse($reportedPort, [ref]$parsedReportedPort) -and
        $parsedReportedPort -ge 1 -and $parsedReportedPort -le 65535) {
        return $parsedReportedPort
    }

    if ($Serial -match '^emulator-(\d+)$') {
        $consolePort = [int]$Matches[1]
        $calculatedPort = $consolePort + 1
        if ($calculatedPort -le 65535) {
            return $calculatedPort
        }
    }

    throw "Could not determine the ADB port for emulator '$Serial'. Pass -HostAdbPort explicitly."
}

function Show-Status {
    param([object[]]$Rows)

    Write-Output "ADB executable: $script:ResolvedAdb"
    Write-Output 'Connected targets:'
    if ($Rows.Count -eq 0) {
        Write-Output '  none'
        return
    }

    $Rows | Format-Table Serial, State, Model, Product, IsEmulator -AutoSize | Out-String | Write-Output

    $onlinePhones = @($Rows | Where-Object { $_.State -eq 'device' -and -not $_.IsEmulator })
    foreach ($phone in $onlinePhones) {
        Write-Output "Reverse mappings for $($phone.Serial) ($($phone.Model)):"
        $mappings = @(Get-ReverseMappings -Serial $phone.Serial)
        if ($mappings.Count -eq 0) {
            Write-Output '  none'
        } else {
            $mappings | ForEach-Object { Write-Output "  $_" }
        }
    }
}

$script:ResolvedAdb = Resolve-AdbExecutable -RequestedPath $AdbPath
$initialRows = Wait-ForAdbTargets `
    -RequiredPhoneSerial $PhoneSerial `
    -RequiredEmulatorSerial $EmulatorSerial `
    -MaximumWaitSeconds $WaitSeconds

if ($Action -eq 'Status') {
    Show-Status -Rows $initialRows
    exit 0
}

$phoneRow = Get-TargetRow `
    -Rows $initialRows `
    -RequestedSerial $PhoneSerial `
    -WantEmulator $false `
    -Label 'physical phone'

$emulatorRow = Get-TargetRow `
    -Rows $initialRows `
    -RequestedSerial $EmulatorSerial `
    -WantEmulator $true `
    -Label 'emulator'

$phoneQemu = Get-DeviceProperty -Serial $phoneRow.Serial -Property 'ro.boot.qemu'
$emulatorQemu = Get-DeviceProperty -Serial $emulatorRow.Serial -Property 'ro.boot.qemu'
$verifiedPhoneModel = Get-DeviceProperty -Serial $phoneRow.Serial -Property 'ro.product.model'
$verifiedEmulatorModel = Get-DeviceProperty -Serial $emulatorRow.Serial -Property 'ro.product.model'

if ($phoneQemu -eq '1') {
    throw "Selected phone '$($phoneRow.Serial)' reports ro.boot.qemu=1 and is not a physical-phone target."
}
if ($emulatorQemu -ne '1') {
    throw "Selected emulator '$($emulatorRow.Serial)' did not report ro.boot.qemu=1."
}

$resolvedHostPort = Resolve-EmulatorAdbPort `
    -Serial $emulatorRow.Serial `
    -RequestedPort $HostAdbPort
$resolvedPhonePort = if ($PhonePort -gt 0) { $PhonePort } else { $resolvedHostPort }

Write-Output "Phone: $verifiedPhoneModel [$($phoneRow.Serial)]"
Write-Output "Emulator: $verifiedEmulatorModel [$($emulatorRow.Serial)]"
Write-Output "Route: phone 127.0.0.1:$resolvedPhonePort -> host 127.0.0.1:$resolvedHostPort"

if ($Action -eq 'Connect') {
    Invoke-Adb -CommandArguments @(
        '-s', $phoneRow.Serial,
        'reverse', "tcp:$resolvedPhonePort", "tcp:$resolvedHostPort"
    ) | Out-Null

    $mappingsAfterConnect = Get-ReverseMappings -Serial $phoneRow.Serial
    if (-not (Test-ReverseMapping `
        -Mappings $mappingsAfterConnect `
        -DevicePort $resolvedPhonePort `
        -HostPort $resolvedHostPort)) {
        throw 'adb returned success, but the expected reverse mapping was not present during verification.'
    }

    Write-Output 'Verified reverse mapping:'
    $mappingsAfterConnect | ForEach-Object { Write-Output "  $_" }
    Write-Output "Phone-side client endpoint: 127.0.0.1:$resolvedPhonePort"
    exit 0
}

$mappingsBeforeDisconnect = Get-ReverseMappings -Serial $phoneRow.Serial
if (-not (Test-ReverseMapping `
    -Mappings $mappingsBeforeDisconnect `
    -DevicePort $resolvedPhonePort `
    -HostPort $resolvedHostPort)) {
    Write-Output 'The selected reverse mapping is already absent. No changes were made.'
    exit 0
}

Invoke-Adb -CommandArguments @(
    '-s', $phoneRow.Serial,
    'reverse', '--remove', "tcp:$resolvedPhonePort"
) | Out-Null

$mappingsAfterDisconnect = Get-ReverseMappings -Serial $phoneRow.Serial
if (Test-ReverseMapping `
    -Mappings $mappingsAfterDisconnect `
    -DevicePort $resolvedPhonePort `
    -HostPort $resolvedHostPort) {
    throw 'The selected mapping is still present after the remove command.'
}

Write-Output "Removed only $($phoneRow.Serial) tcp:$resolvedPhonePort."
