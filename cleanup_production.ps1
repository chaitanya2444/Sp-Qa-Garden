# QA Garden - Production Cleanup Script
# Date: 2026-02-14
# Purpose: Remove unnecessary files and prepare for production deployment

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "QA Garden - Production Cleanup Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Navigate to project root
$projectRoot = "C:\Users\rleel\OneDrive\Desktop\QA DASH\qa-garden-dashboard"
Set-Location $projectRoot

Write-Host "📁 Project Root: $projectRoot" -ForegroundColor Yellow
Write-Host ""

# Phase 1: Create Backup
Write-Host "Phase 1: Creating Backup..." -ForegroundColor Green
$backupDir = "$projectRoot\BACKUP_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

# Backup latest outputs
Write-Host "  ✓ Backing up latest test generator output..." -ForegroundColor Gray
Copy-Item "agents\test_generator\output\run_job_1_generated_20260214_140904.json" "$backupDir\" -Force

Write-Host "  ✓ Backing up triage database..." -ForegroundColor Gray
Copy-Item "agents\triage_engine\triage_db.json" "$backupDir\" -Force

Write-Host "  ✓ Backing up current locators..." -ForegroundColor Gray
Copy-Item "agents\crawler\locators_new\" "$backupDir\locators_new\" -Recurse -Force

Write-Host "✅ Backup created at: $backupDir" -ForegroundColor Green
Write-Host ""

# Phase 2: Clean Crawler
Write-Host "Phase 2: Cleaning Crawler Agent..." -ForegroundColor Green
$crawlerCleaned = 0

if (Test-Path "agents\crawler\auth_retry_*.png") {
    Remove-Item "agents\crawler\auth_retry_*.png" -Force
    $crawlerCleaned += 3
    Write-Host "  ✓ Removed debug screenshots (auth_retry_*.png)" -ForegroundColor Gray
}

if (Test-Path "agents\crawler\snappod_login_final_fail.png") {
    Remove-Item "agents\crawler\snappod_login_final_fail.png" -Force
    $crawlerCleaned += 1
    Write-Host "  ✓ Removed snappod_login_final_fail.png" -ForegroundColor Gray
}

if (Test-Path "agents\crawler\final_diag_state.png") {
    Remove-Item "agents\crawler\final_diag_state.png" -Force
    $crawlerCleaned += 1
    Write-Host "  ✓ Removed final_diag_state.png" -ForegroundColor Gray
}

Get-ChildItem "agents\crawler\" -Directory -Filter "locators_old*" | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    $crawlerCleaned += 1
    Write-Host "  ✓ Removed $($_.Name)" -ForegroundColor Gray
}

if (Test-Path "agents\crawler\locators\") {
    Remove-Item "agents\crawler\locators\" -Recurse -Force
    $crawlerCleaned += 1
    Write-Host "  ✓ Removed old locators directory" -ForegroundColor Gray
}

if (Test-Path "agents\crawler\browse_ai_helper.py") {
    Remove-Item "agents\crawler\browse_ai_helper.py" -Force
    $crawlerCleaned += 1
    Write-Host "  ✓ Removed browse_ai_helper.py" -ForegroundColor Gray
}

if (Test-Path "agents\crawler\diag_frames.py") {
    Remove-Item "agents\crawler\diag_frames.py" -Force
    $crawlerCleaned += 1
    Write-Host "  ✓ Removed diag_frames.py" -ForegroundColor Gray
}

Write-Host "✅ Crawler: Removed $crawlerCleaned items" -ForegroundColor Green
Write-Host ""

# Phase 3: Clean Test Generator
Write-Host "Phase 3: Cleaning Test Generator Agent..." -ForegroundColor Green
$testGenCleaned = 0

# Keep only latest output
$latestOutput = "run_job_1_generated_20260214_140904.json"
Get-ChildItem "agents\test_generator\output\*.json" | Where-Object { $_.Name -ne $latestOutput } | ForEach-Object {
    Remove-Item $_.FullName -Force
    $testGenCleaned += 1
}
Write-Host "  ✓ Removed $testGenCleaned old test outputs" -ForegroundColor Gray

# Remove test scripts
$testScripts = @("test_bridge_logic.py", "test_gemini.py", "test_grok.py", "test_groq.py", "test_hf.py", "trigger_test_gen.py", "list_models.py")
foreach ($script in $testScripts) {
    if (Test-Path "agents\test_generator\$script") {
        Remove-Item "agents\test_generator\$script" -Force
        $testGenCleaned += 1
        Write-Host "  ✓ Removed $script" -ForegroundColor Gray
    }
}

Write-Host "✅ Test Generator: Removed $testGenCleaned items" -ForegroundColor Green
Write-Host ""

# Phase 4: Clean Playwright Generator
Write-Host "Phase 4: Cleaning Playwright Generator Agent..." -ForegroundColor Green
$playwrightCleaned = 0

if (Test-Path "agents\playwright_gen\main.zip") {
    Remove-Item "agents\playwright_gen\main.zip" -Force
    $playwrightCleaned += 1
    Write-Host "  ✓ Removed main.zip" -ForegroundColor Gray
}

Write-Host "✅ Playwright Generator: Removed $playwrightCleaned items" -ForegroundColor Green
Write-Host ""

# Phase 5: Clean CI/CD
Write-Host "Phase 5: Cleaning CI/CD Agent..." -ForegroundColor Green
$cicdCleaned = 0

$cicdFiles = @("main.zip", "manual_results.xml", "pytest_output.txt", "debug_pytest.py", "test_xml_sync.py")
foreach ($file in $cicdFiles) {
    if (Test-Path "agents\cicd\$file") {
        Remove-Item "agents\cicd\$file" -Force
        $cicdCleaned += 1
        Write-Host "  ✓ Removed $file" -ForegroundColor Gray
    }
}

Write-Host "✅ CI/CD: Removed $cicdCleaned items" -ForegroundColor Green
Write-Host ""

# Phase 6: Clean Triage Engine
Write-Host "Phase 6: Cleaning Triage Engine Agent..." -ForegroundColor Green
$triageCleaned = 0

# Remove test scripts and outputs
$triageFiles = @(
    "autodetect_gemini.py", "autodetect_result.txt", "bert_server.py", 
    "check_bert_status.py", "check_methods.py", "final_test_output.json",
    "latest_dryrun.json", "latest_result.json", "list_models.py",
    "model_list_full.txt", "model_list_lines.txt", "models.txt", "models_plain.txt",
    "pick_model.py", "playwright-report.json", "run_all_services.py", "run_all_tests.py",
    "test_gemini.ps1", "test_gemini.py", "test_gemini_key.py", "test_triage.json",
    "verify_gemini.py", "verify_triage.py", "view_results.py"
)

foreach ($file in $triageFiles) {
    if (Test-Path "agents\triage_engine\$file") {
        Remove-Item "agents\triage_engine\$file" -Force
        $triageCleaned += 1
    }
}
Write-Host "  ✓ Removed $triageCleaned test files" -ForegroundColor Gray

# Remove test-results directory
if (Test-Path "agents\triage_engine\test-results\") {
    Remove-Item "agents\triage_engine\test-results\" -Recurse -Force
    $triageCleaned += 1
    Write-Host "  ✓ Removed test-results directory" -ForegroundColor Gray
}

# Remove tests directory
if (Test-Path "agents\triage_engine\tests\") {
    Remove-Item "agents\triage_engine\tests\" -Recurse -Force
    $triageCleaned += 1
    Write-Host "  ✓ Removed tests directory" -ForegroundColor Gray
}

Write-Host "✅ Triage Engine: Removed $triageCleaned items" -ForegroundColor Green
Write-Host ""

# Phase 7: Clean Python Cache
Write-Host "Phase 7: Cleaning Python Cache Files..." -ForegroundColor Green
$cacheCleaned = 0

Get-ChildItem -Path "agents\" -Recurse -Directory -Filter "__pycache__" | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    $cacheCleaned += 1
}

Get-ChildItem -Path "agents\" -Recurse -Directory -Filter ".pytest_cache" | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force
    $cacheCleaned += 1
}

Write-Host "✅ Cleaned $cacheCleaned cache directories" -ForegroundColor Green
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Cleanup Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
$totalCleaned = $crawlerCleaned + $testGenCleaned + $playwrightCleaned + $cicdCleaned + $triageCleaned + $cacheCleaned
Write-Host "Total Items Removed: $totalCleaned" -ForegroundColor Yellow
Write-Host "Backup Location: $backupDir" -ForegroundColor Yellow
Write-Host ""

Write-Host "⚠️  IMPORTANT: Next Steps" -ForegroundColor Red
Write-Host "1. Remove hardcoded API keys from code (see production_readiness_plan.md)" -ForegroundColor Yellow
Write-Host "2. Move all API keys to .env files" -ForegroundColor Yellow
Write-Host "3. Update .gitignore" -ForegroundColor Yellow
Write-Host "4. Test all agents with environment variables" -ForegroundColor Yellow
Write-Host ""

Write-Host "✅ Cleanup Complete!" -ForegroundColor Green
