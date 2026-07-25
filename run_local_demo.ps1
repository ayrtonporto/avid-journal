# AViD Journal - local demo launcher WITH the resident Lean REPL pool.
# Run from the worktree:  .\run_local_demo.ps1
# Then open http://127.0.0.1:7860  (Ctrl+C to stop)

$ErrorActionPreference = "Stop"
$wt   = $PSScriptRoot
$repo = (Resolve-Path (Join-Path $wt "..\..\..")).Path   # main repo (has compiled Mathlib)

$py       = Join-Path $repo ".venv\Scripts\python.exe"
$leanMain = Join-Path $repo "lean_project"
$envFile  = Join-Path $repo ".env"
$replBin  = Join-Path $wt   "vendor\repl\.lake\build\bin\repl.exe"

# Load API keys from the main .env (OPENCODE_GO_API_KEY, etc.)
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2].Trim())
        }
    }
    Write-Host "[env] loaded keys from $envFile"
} else {
    Write-Host "[env] WARNING: .env not found - server-default model wont work (use own API key in the UI)"
}

# Demo + REPL pool config
$env:AVID_DEV_MODE       = "1"      # no Google sign-in for local testing
$env:AVID_PREWARM        = "1"      # warm the REPL pool at startup
$env:AVID_REPL_POOL      = "1"
$env:AVID_REPL_BIN       = $replBin
$env:AVID_REPL_POOL_SIZE = "2"      # 2 concurrent analyses (needs ~12 GB free)
$env:LEAN_PROJECT_DIR    = $leanMain
$env:AVID_FORMALIZATION_ENABLED = "1"
$env:AVID_D2_ENABLED     = "1"
$env:THEOREMSEARCH_ENABLED = "1"   # D1 C_I theorem-level source (replaces Semantic Scholar)
$env:AVID_JUDGE_TIMEOUT  = "30"    # hard cap per DeepSeek judge call (fail-open)

# Claude Code (local, OAuth) as an optional formalizer: put `claude` on PATH so
# the provider's shutil.which("claude") resolves, and default the agentic model.
$claudeDir = Join-Path $env:APPDATA "npm"    # where `claude` npm shim lives
if (Test-Path (Join-Path $claudeDir "claude.cmd")) {
    $env:PATH = "$claudeDir;$env:PATH"
    Write-Host "[claude] on PATH: $claudeDir"
} else {
    Write-Host "[claude] WARNING: claude.cmd not found in $claudeDir - the 'Claude Code' option will fail"
}
$env:AVID_MODEL_PROVIDER = "claude"

Write-Host "[repl] binary : $replBin"
Write-Host "[lean] project: $leanMain"
if (-not (Test-Path $replBin))  { Write-Host "[repl] WARNING: REPL binary missing - will fall back to the COLD path" }
if (-not (Test-Path $leanMain)) { Write-Host "[lean] ERROR: compiled lean_project not found at $leanMain"; exit 1 }

Write-Host ""
Write-Host "Starting server on http://127.0.0.1:7860  (pool warms ~30s in background)"
Write-Host ""
& $py -m uvicorn server:app --host 127.0.0.1 --port 7860
