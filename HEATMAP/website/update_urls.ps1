# PowerShell script to replace all /website/ with /HEATMAP/website/
Get-ChildItem -Path "j:\HEATMAP\website" -Recurse -Include *.php | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    $newContent = $content -replace '/website/', '/HEATMAP/website/'
    Set-Content $_.FullName -Value $newContent -NoNewline
}
Write-Host "All URLs updated to /HEATMAP/website/"
