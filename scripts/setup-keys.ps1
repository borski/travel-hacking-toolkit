# Travel Hacker key setup (PowerShell). Prompts you locally for API keys,
# validates them, and writes exports to your PowerShell profile with backup.
# Never echoes values.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\setup-keys.ps1
#
# Cmd.exe users: this script writes to your PowerShell `$PROFILE`. If you
# work in cmd.exe (not PowerShell), set keys directly with `setx KEY "value"`
# instead. New cmd windows will pick them up. PowerShell windows need to be
# restarted (or run `. $PROFILE`) after this script.

$ErrorActionPreference = 'Stop'

Write-Host "Travel Hacker key setup"
Write-Host "  PowerShell profile: $PROFILE"
Write-Host ""
Write-Host "I will prompt you for API keys (input is masked, never echoed)."
Write-Host "Anything you skip stays unset. All keys are optional."
Write-Host ""

# Make sure profile exists
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Host "Created profile at $PROFILE"
}

$KeysAdded = 0
$KeysSkipped = 0
$NewLines = @()

function Already-Set($key) {
    $content = Get-Content $PROFILE -ErrorAction SilentlyContinue
    if ($null -eq $content) { return $false }
    $pattern = '^\s*\$env:' + [regex]::Escape($key) + '\s*='
    return ($content -match $pattern).Count -gt 0
}

function Prompt-Key($key, $desc, $url, $minLen = 10) {
    if (Already-Set $key) {
        Write-Host "[exists] $key (already in profile, skipping)"
        $script:KeysSkipped++
        return
    }

    $current = [Environment]::GetEnvironmentVariable($key)
    if (-not [string]::IsNullOrEmpty($current)) {
        Write-Host ""
        Write-Host "$key is already in your current environment but not yet in `$PROFILE."
        $persist = Read-Host "  Persist the current value to `$PROFILE`? [y/N]"
        if ($persist -match '^[Yy]') {
            if ($current -match "'") {
                Write-Host "[rejected] $key value contains a single quote. Skipped."
                $script:KeysSkipped++
                return
            }
            if ($current.Length -lt $minLen) {
                Write-Host "[rejected] $key current value is too short ($($current.Length) chars, expected at least $minLen). Skipped."
                $script:KeysSkipped++
                return
            }
            $script:NewLines += "`$env:$key = '$current'"
            $script:KeysAdded++
            Write-Host "[ready]  $key (will write current value to profile)"
        } else {
            Write-Host "[skipped] $key (kept ephemeral)"
            $script:KeysSkipped++
        }
        return
    }

    Write-Host ""
    Write-Host $key
    Write-Host "  $desc"
    if ($url) { Write-Host "  Get one at: $url" }

    # AsSecureString = masked input
    $secure = Read-Host "  Paste key (Enter to skip)" -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    $value = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)

    if ([string]::IsNullOrEmpty($value)) {
        Write-Host "[skipped] $key"
        $script:KeysSkipped++
        return
    }

    if ($value -match "'") {
        Write-Host "[rejected] $key contains a single quote, which would break the export. Skipped."
        $script:KeysSkipped++
        return
    }

    if ($value.Length -lt $minLen) {
        Write-Host "[rejected] $key looks too short ($($value.Length) chars, expected at least $minLen). Skipped."
        $script:KeysSkipped++
        return
    }

    # Single-quoted PowerShell strings are literal (no expansion)
    $script:NewLines += "`$env:$key = '$value'"
    $script:KeysAdded++
    Write-Host "[ready]  $key (will write to profile)"
}

# --- Tier 1 ---

Write-Host "=== Tier 1 (high-value) ==="

Prompt-Key 'SEATS_AERO_API_KEY' `
    'Award flight search across 27 mileage programs. The main event.' `
    'https://seats.aero/profile (Pro ~$8/mo)'

Prompt-Key 'DUFFEL_API_KEY_LIVE' `
    'Real GDS cash flight prices. Free to search, pay per booking.' `
    'https://duffel.com (use the LIVE key, not test)'

Prompt-Key 'IGNAV_API_KEY' `
    'Backup cash flight prices. Fast REST API.' `
    'https://ignav.com (1,000 free requests/month)'

Prompt-Key 'AWARDWALLET_API_KEY' `
    'Auto-pull your loyalty balances, elite status, transfer ratios.' `
    'https://business.awardwallet.com/profile/api (Business account required)'

Prompt-Key 'AWARDWALLET_USER_ID' `
    'Your AwardWallet user ID (paired with the API key above).' `
    '' `
    3

# --- Tier 2 ---

Write-Host ""
$more = Read-Host "Continue with Tier 2 (SerpAPI, RapidAPI, LiteAPI, TripAdvisor)? [y/N]"
if ($more -match '^[Yy]') {
    Prompt-Key 'SERPAPI_API_KEY' 'Google Flights/Hotels comparison data.' 'https://serpapi.com (100 searches/mo free)'
    Prompt-Key 'RAPIDAPI_KEY'    'Booking.com Live + Google Flights Live as fallback sources.' 'https://rapidapi.com'
    Prompt-Key 'LITEAPI_API_KEY' 'Hotel rate inventory via LiteAPI MCP.' 'https://liteapi.travel'
    Prompt-Key 'TRIPADVISOR_API_KEY' 'Hotel ratings, reviews, and rankings.' 'https://tripadvisor-content-api.readme.io (5K calls/mo free)'
}

# --- Tier 3 ---

Write-Host ""
$more = Read-Host "Continue with Tier 3 (Scandinavia transit)? [y/N]"
if ($more -match '^[Yy]') {
    Prompt-Key 'ENTUR_CLIENT_NAME' "Norway transit search. Free, no signup. Format: 'yourcompany-app'." '' 3
    Prompt-Key 'RESROBOT_API_KEY'  'Sweden rail/bus search.' 'https://www.trafiklab.se (30K calls/mo free)'
    Prompt-Key 'REJSEPLANEN_API_KEY' 'Denmark rail/bus search.' 'https://help.rejseplanen.dk'
}

# --- Write ---

Write-Host ""
Write-Host "Summary: $KeysAdded to add, $KeysSkipped skipped."

if ($KeysAdded -eq 0) {
    Write-Host "Nothing to write. Done."
    exit 0
}

$confirm = Read-Host "Write $KeysAdded exports to $PROFILE`? [Y/n]"
if ($confirm -match '^[Nn]') {
    Write-Host "Aborted. No changes made."
    exit 0
}

# Backup if profile has content
if ((Get-Item $PROFILE).Length -gt 0) {
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backup = "$PROFILE.bak.$timestamp"
    Copy-Item $PROFILE $backup
    Write-Host "Backup: $backup"
}

# Append header + lines
$header = @(
    ''
    "# Added by travel-hacker setup-keys.ps1 on $(Get-Date)"
)
$header + $NewLines | Add-Content $PROFILE

Write-Host "Wrote $KeysAdded exports to $PROFILE."
Write-Host ""
Write-Host "Run this to load them now (or open a new PowerShell window):"
Write-Host "  . `$PROFILE"
Write-Host ""
Write-Host "Then start Claude Code and ask it to plan a trip."
