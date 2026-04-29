<#
    Travel Hacking Toolkit - Setup Script (Windows / PowerShell)

    Native Windows equivalent of scripts/setup.sh. Works in Windows PowerShell 5.1+
    and PowerShell 7+. Gets you from clone to working in under a minute.

    Usage:
        # From Windows PowerShell / PowerShell 7+
        powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1

        # Or use the .cmd wrapper (double-clickable)
        .\scripts\setup.cmd
#>

#Requires -Version 5.1

$ErrorActionPreference = 'Stop'

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir   = Split-Path -Parent $ScriptDir

function Has-Command {
    param([string]$Name)
    [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Read-Choice {
    param([string]$Prompt, [string[]]$Valid)
    while ($true) {
        $answer = Read-Host $Prompt
        if ($Valid -contains $answer) { return $answer }
        Write-Host "  Invalid choice. Try again." -ForegroundColor Yellow
    }
}

function Invoke-Native {
    <#
        Run a native command with stdout and stderr captured to temp files.
        PowerShell never sees the stderr stream, so native stderr cannot turn
        into a red NativeCommandError record under $ErrorActionPreference=Stop.
        Returns @{ ExitCode; Output } where Output is stdout + stderr combined.
    #>
    param(
        [Parameter(Mandatory)] [string]   $FilePath,
        [Parameter(Mandatory)] [string[]] $Arguments
    )

    $stdout = [IO.Path]::GetTempFileName()
    $stderr = [IO.Path]::GetTempFileName()
    try {
        $proc = Start-Process -FilePath $FilePath -ArgumentList $Arguments `
            -NoNewWindow -Wait -PassThru `
            -RedirectStandardOutput $stdout -RedirectStandardError $stderr
        $text = ''
        if (Test-Path $stdout) { $text += (Get-Content -LiteralPath $stdout -Raw -ErrorAction SilentlyContinue) }
        if (Test-Path $stderr) { $text += (Get-Content -LiteralPath $stderr -Raw -ErrorAction SilentlyContinue) }
        return @{ ExitCode = $proc.ExitCode; Output = $text }
    } finally {
        Remove-Item -LiteralPath $stdout, $stderr -ErrorAction SilentlyContinue
    }
}

function Invoke-DockerPull {
    param(
        [Parameter(Mandatory)] [string] $Image,
        [Parameter(Mandatory)] [string] $Label,
        [Parameter(Mandatory)] [string] $BuildContext,
        [Parameter(Mandatory)] [string] $LocalTag
    )

    $result = Invoke-Native -FilePath 'docker' -Arguments @('pull', $Image)

    if ($result.ExitCode -eq 0) {
        Write-Host "  [ok] $Label Docker image ready."
        return
    }

    $text = [string]$result.Output
    $isAuthFail = ($text -match 'unauthorized|denied|authentication required')

    if ($isAuthFail) {
        Write-Host "  Could not pull $Label image: registry returned 'unauthorized'." -ForegroundColor Yellow
        Write-Host "    GHCR auth notes:" -ForegroundColor Yellow
        Write-Host "      - 'docker login ghcr.io' needs a GitHub Personal Access Token with the 'read:packages' scope as the password."
        Write-Host "      - Your GitHub account password will not work. A PAT without 'read:packages' will not work."
        Write-Host "      - Stale creds: try 'docker logout ghcr.io' and retry (anonymous pull works for public images)."
        Write-Host "      - The image may also be private; building locally avoids this entirely."
    } else {
        Write-Host "  Could not pull $Label image (docker exit $($result.ExitCode))." -ForegroundColor Yellow
    }

    $buildCtxPath = Join-Path $RepoDir $BuildContext
    if (Test-Path $buildCtxPath) {
        $buildChoice = Read-Host "  Build the $Label image locally from $BuildContext instead? [y/N]"
        if ($buildChoice -match '^[Yy]$') {
            Write-Host "  Building $LocalTag from $BuildContext (this can take a few minutes)..."
            $build = Invoke-Native -FilePath 'docker' -Arguments @('build', '-t', $LocalTag, $buildCtxPath)
            if ($build.ExitCode -eq 0) {
                Write-Host "  [ok] Built $LocalTag locally. Use 'docker run --rm $LocalTag ...' in place of the ghcr.io tag."
            } else {
                Write-Host "  docker build failed (exit $($build.ExitCode)). Build manually: docker build -t $LocalTag $BuildContext" -ForegroundColor Yellow
                if ($build.Output) { Write-Host ($build.Output.Trim()) -ForegroundColor DarkGray }
            }
        } else {
            Write-Host "    Build manually later: docker build -t $LocalTag $BuildContext"
        }
    }
}

function Resolve-PythonCommand {
    foreach ($candidate in @('python', 'python3', 'py')) {
        if (Has-Command $candidate) {
            try {
                $out = & $candidate --version 2>&1
                if ($LASTEXITCODE -eq 0 -and $out -match 'Python 3') { return $candidate }
            } catch { }
        }
    }
    return $null
}

Write-Host "=== Travel Hacking Toolkit Setup ==="
Write-Host ""

# --- Which tool? ---
Write-Host "Which AI coding tool do you use?"
Write-Host "  1) OpenCode"
Write-Host "  2) Claude Code"
Write-Host "  3) Codex"
Write-Host "  4) All"
Write-Host ""
$ToolChoice = Read-Host "Choice [1-4]"
if ($ToolChoice -notin @('1', '2', '3', '4')) {
    Write-Host "Invalid choice. Exiting." -ForegroundColor Red
    exit 1
}

$UseOpenCode = $false
$UseClaude   = $false
$UseCodex    = $false

switch ($ToolChoice) {
    '1' { $UseOpenCode = $true }
    '2' { $UseClaude   = $true }
    '3' { $UseCodex    = $true }
    '4' {
        $UseOpenCode = $true
        $UseClaude   = $true
        $UseCodex    = $true
    }
}

# --- API key setup ---
function Setup-ApiKeys {
    Write-Host ""
    Write-Host "Setting up API keys..."

    if ($UseOpenCode -or $UseCodex) {
        $envFile    = Join-Path $RepoDir '.env'
        $envExample = Join-Path $RepoDir '.env.example'
        if (-not (Test-Path $envFile)) {
            Copy-Item -LiteralPath $envExample -Destination $envFile
            Write-Host "  Created .env (OpenCode/Codex). Edit it to add your API keys."
        } else {
            Write-Host "  .env already exists. Skipping."
        }
    }

    if ($UseClaude) {
        $claudeSettings = Join-Path $RepoDir '.claude\settings.local.json'
        $claudeExample  = Join-Path $RepoDir '.claude\settings.local.json.example'
        if (-not (Test-Path $claudeSettings)) {
            if (Test-Path $claudeExample) {
                Copy-Item -LiteralPath $claudeExample -Destination $claudeSettings
                Write-Host "  Created .claude\settings.local.json (Claude Code, auto-gitignored)."
                Write-Host "  Edit it to add your API keys."
            }
        } else {
            Write-Host "  .claude\settings.local.json already exists. Skipping."
        }
    }

    Write-Host ""
    Write-Host "  The 5 free MCP servers work without any keys."
    Write-Host "  For the full experience, add at minimum:"
    Write-Host "    SEATS_AERO_API_KEY     Award flight search (the main event)"
    Write-Host "    DUFFEL_API_KEY_LIVE    Primary cash flight prices (search free, pay per booking)"
    Write-Host "    IGNAV_API_KEY          Secondary cash flight prices (1,000 free requests)"
    Write-Host ""
}

# --- Atlas Obscura npm deps ---
function Install-AtlasDeps {
    Write-Host "Installing Atlas Obscura dependencies..."
    if (Has-Command 'npm') {
        $atlasDir = Join-Path $RepoDir 'skills\atlas-obscura'
        Push-Location $atlasDir
        try {
            # npm.cmd on Windows; `npm` resolves to the shim via PATHEXT
            & npm install --silent 2>$null | Out-Null
            Write-Host "  Done."
        } catch {
            Write-Host "  npm install failed. Atlas Obscura will auto-install on first use." -ForegroundColor Yellow
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "  npm not found. Atlas Obscura will auto-install on first use if Node.js is available."
        Write-Host "  Install Node.js from https://nodejs.org/ (or: winget install OpenJS.NodeJS.LTS)"
    }
}

# --- Optional tools ---
function Install-OptionalTools {
    Write-Host ""
    Write-Host "Optional tools for additional flight search skills:"
    Write-Host ""

    # agent-browser (for google-flights skill)
    if (Has-Command 'agent-browser') {
        Write-Host "  [ok] agent-browser already installed (google-flights skill)"
    } else {
        Write-Host "  agent-browser: Enables the google-flights skill (browser-automated Google Flights)."
        if (-not (Has-Command 'npm')) {
            Write-Host "  npm not found. Install Node.js first (https://nodejs.org/ or 'winget install OpenJS.NodeJS.LTS')." -ForegroundColor Yellow
        } else {
            $abChoice = Read-Host "  Install agent-browser? [y/N]"
            if ($abChoice -match '^[Yy]$') {
                & npm install -g agent-browser
                if ($LASTEXITCODE -eq 0) {
                    & agent-browser install
                    Write-Host "  [ok] agent-browser installed."
                } else {
                    Write-Host "  npm install failed." -ForegroundColor Yellow
                }
            } else {
                Write-Host "  Skipped. google-flights skill won't work without it."
            }
        }
    }

    Write-Host ""

    # Southwest / AA: Docker or Patchright
    Write-Host "  Southwest skill: searches southwest.com for fare classes and points pricing."
    Write-Host "  Requires either Docker Desktop (recommended) or Patchright (Python)."
    Write-Host ""

    if (Has-Command 'docker') {
        Write-Host "  Docker detected. Pulling pre-built images..."
        Invoke-DockerPull -Image 'ghcr.io/borski/sw-fares:latest' -Label 'Southwest' `
            -BuildContext 'skills\southwest' -LocalTag 'sw-fares'
        Invoke-DockerPull -Image 'ghcr.io/borski/aa-miles-check:latest' -Label 'American Airlines' `
            -BuildContext 'skills\american-airlines' -LocalTag 'aa-check'

        Write-Host ""
        Write-Host "  Chase and Amex Travel portal skills (optional, build locally):"
        Write-Host "  docker build -t chase-travel skills\chase-travel\"
        Write-Host "  docker build -t amex-travel skills\amex-travel\"
    } else {
        Write-Host "  Docker not found. (Install Docker Desktop: https://www.docker.com/products/docker-desktop/ or 'winget install Docker.DockerDesktop')"
        $pythonCmd = Resolve-PythonCommand

        if (-not $pythonCmd) {
            Write-Host "  Python 3 not found either. Install Python (https://www.python.org/downloads/ or 'winget install Python.Python.3.12') or Docker to use the Southwest skill." -ForegroundColor Yellow
        } else {
            $patchrightInstalled = $false
            try {
                & $pythonCmd -c "import patchright" 2>$null
                if ($LASTEXITCODE -eq 0) { $patchrightInstalled = $true }
            } catch { }

            if ($patchrightInstalled) {
                Write-Host "  [ok] Patchright already installed (southwest skill, headed mode)"
            } else {
                $prChoice = Read-Host "  Install Patchright for Southwest skill? [y/N]"
                if ($prChoice -match '^[Yy]$') {
                    & $pythonCmd -m pip install patchright
                    if ($LASTEXITCODE -eq 0) {
                        & $pythonCmd -m patchright install chromium
                        Write-Host "  [ok] Patchright installed. Southwest skill will open a Chrome window briefly."
                    } else {
                        Write-Host "  pip install failed." -ForegroundColor Yellow
                    }
                } else {
                    Write-Host "  Skipped. Southwest skill won't work without Docker or Patchright."
                }
            }
        }
    }

    Write-Host ""
}

# --- Global install (optional) ---
function Install-SkillsTo {
    param([string]$Target)

    Write-Host ""
    Write-Host "  Installing skills to $Target..."
    New-Item -ItemType Directory -Force -Path $Target | Out-Null

    $skillsRoot = Join-Path $RepoDir 'skills'
    Get-ChildItem -LiteralPath $skillsRoot -Directory | ForEach-Object {
        $skillName = $_.Name
        $dest = Join-Path $Target $skillName

        if (Test-Path $dest) {
            Write-Host "    Updating $skillName..."
            Remove-Item -LiteralPath $dest -Recurse -Force
        } else {
            Write-Host "    Installing $skillName..."
        }

        Copy-Item -LiteralPath $_.FullName -Destination $dest -Recurse
    }

    Write-Host "  Done."
}

function Offer-GlobalInstall {
    Write-Host ""
    Write-Host "Skills are already available when you work from this directory."
    Write-Host "Want to also install them system-wide (available in any project)?"
    Write-Host ""
    $globalChoice = Read-Host "Install globally? [y/N]"

    if ($globalChoice -match '^[Yy]$') {
        if ($UseOpenCode) {
            Install-SkillsTo (Join-Path $HOME '.config\opencode\skills')
        }
        if ($UseClaude) {
            Install-SkillsTo (Join-Path $HOME '.claude\skills')
        }
    } else {
        Write-Host "  Skipped. You can always run this script again later."
    }
}

# --- Codex plugin install ---
function Install-CodexPlugin {
    $pluginName  = 'travel-hacking-toolkit'
    $pluginSrc   = Join-Path $RepoDir "plugins\$pluginName"
    $codexHome   = if ($env:CODEX_HOME) { $env:CODEX_HOME } else { Join-Path $HOME '.codex' }
    $codexPlugDir = Join-Path $codexHome 'plugins'
    $codexPlugPath = Join-Path $codexPlugDir $pluginName
    $marketplaceRoot = if ($env:CODEX_MARKETPLACE_ROOT) { $env:CODEX_MARKETPLACE_ROOT } else { Join-Path $HOME '.agents' }
    $marketplaceDir  = Join-Path $marketplaceRoot 'plugins'
    $marketplacePath = Join-Path $marketplaceDir 'marketplace.json'

    Write-Host ""
    Write-Host "Installing Codex plugin..."

    $pythonCmd = Resolve-PythonCommand
    if (-not $pythonCmd) {
        Write-Host "  python3 not found. Skipping Codex plugin install." -ForegroundColor Yellow
        Write-Host "  Install Python (https://www.python.org/downloads/ or 'winget install Python.Python.3.12') and re-run setup." -ForegroundColor Yellow
        return
    }

    New-Item -ItemType Directory -Force -Path $codexPlugDir | Out-Null
    New-Item -ItemType Directory -Force -Path $marketplaceDir | Out-Null

    if (Test-Path -LiteralPath $codexPlugPath) {
        Remove-Item -LiteralPath $codexPlugPath -Recurse -Force
    }

    # Two install methods on Windows. Symlink needs admin or Developer Mode but
    # auto-propagates toolkit updates. Copy works everywhere but is a snapshot,
    # so updates require re-running this script.
    Write-Host ""
    Write-Host "  Codex plugin install method:"
    Write-Host "    1) Symlink (recommended). Auto-propagates toolkit updates."
    Write-Host "       Requires admin OR Developer Mode (Settings -> Privacy & security -> For developers)."
    Write-Host "    2) Copy. Works without admin. Re-run setup after pulling toolkit updates."
    Write-Host ""
    $methodChoice = Read-Host "  Choice [1/2]"

    if ($methodChoice -eq '1') {
        try {
            New-Item -ItemType SymbolicLink -Path $codexPlugPath -Target $pluginSrc -ErrorAction Stop | Out-Null
            Write-Host "  Plugin symlinked to $codexPlugPath"
        } catch {
            Write-Host "  Symlink failed: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "  Enable Developer Mode (Settings -> Privacy & security -> For developers)" -ForegroundColor Yellow
            Write-Host "  or relaunch this script as administrator, then try again." -ForegroundColor Yellow
            Write-Host "  Or re-run and choose option 2 (Copy) to install without admin." -ForegroundColor Yellow
            return
        }
    } elseif ($methodChoice -eq '2') {
        Copy-Item -LiteralPath $pluginSrc -Destination $codexPlugPath -Recurse -Force
        Write-Host "  Plugin copied to $codexPlugPath"
        Write-Host "  Re-run setup.cmd after 'git pull' to refresh." -ForegroundColor Yellow
    } else {
        Write-Host "  Invalid choice. Skipping Codex plugin install." -ForegroundColor Yellow
        return
    }

    # Marketplace JSON merge (idempotent: replaces existing entry by name, else appends)
    $pythonScript = @'
import json
import os
import sys

path = sys.argv[1]
entry = {
    "name": "travel-hacking-toolkit",
    "source": {
        "source": "local",
        "path": "./plugins/travel-hacking-toolkit"
    },
    "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
    },
    "category": "Productivity"
}

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {
        "name": "local-plugins",
        "interface": {
            "displayName": "Local Plugins"
        },
        "plugins": []
    }

data.setdefault("name", "local-plugins")
data.setdefault("interface", {})
data["interface"].setdefault("displayName", "Local Plugins")
plugins = data.setdefault("plugins", [])

for idx, plugin in enumerate(plugins):
    if plugin.get("name") == entry["name"]:
        plugins[idx] = entry
        break
else:
    plugins.append(entry)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
'@

    $tempScript = [IO.Path]::GetTempFileName() + '.py'
    try {
        Set-Content -LiteralPath $tempScript -Value $pythonScript -Encoding UTF8
        $result = Invoke-Native -FilePath $pythonCmd -Arguments @($tempScript, $marketplacePath)
        if ($result.ExitCode -ne 0) {
            Write-Host "  Failed to update marketplace.json (python exit $($result.ExitCode))." -ForegroundColor Yellow
            if ($result.Output) { Write-Host ($result.Output.Trim()) -ForegroundColor DarkGray }
            return
        }
    } finally {
        Remove-Item -LiteralPath $tempScript -ErrorAction SilentlyContinue
    }

    Write-Host "  Marketplace updated at $marketplacePath"
    Write-Host "  Launch Codex from this repo after editing .env"
}

# --- Run ---
Setup-ApiKeys
Install-AtlasDeps
Install-OptionalTools

if ($UseCodex) {
    Install-CodexPlugin
}

if ($UseOpenCode -or $UseClaude) {
    Offer-GlobalInstall
}

Write-Host ""
Write-Host "=== Setup complete! ==="
Write-Host ""
Write-Host "Launch your tool from this directory:"

if ($UseOpenCode) {
    Write-Host "  OpenCode:    opencode"
}
if ($UseClaude) {
    Write-Host "  Claude Code: claude --strict-mcp-config --mcp-config .mcp.json"
}
if ($UseCodex) {
    Write-Host "  Codex:       codex"
}

Write-Host ""

if ($UseOpenCode -or $UseCodex) {
    Write-Host "Add your API keys:  edit .env"
}
if ($UseClaude) {
    Write-Host "Add your API keys:  edit .claude\settings.local.json"
}

Write-Host ""
Write-Host "Then ask: `"Find me a cheap business class flight to Tokyo`""
Write-Host ""
