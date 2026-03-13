# Quick script to submit customer reviews
$businessName = Read-Host "Business Name"
$email = Read-Host "Customer Email"

Write-Host "Paste 5 reviews (press Enter after each):"
$reviews = @()
1..5 | ForEach-Object {
    $rating = Read-Host "Review $_ - Rating (1-5)"
    $text = Read-Host "Review $_ - Text"
    $reviews += @{rating=[int]$rating; text=$text}
}

$payload = @{
    business_name = $businessName
    email = $email
    persona = 'dentist_medspa'
    compliance_profile = 'HIPAA'
    tone_style = 'Warm'
    signoff = '– Team'
    private_email = ''
    reviews_sample = $reviews
} | ConvertTo-Json -Depth 6

Write-Host "`nSending to orchestrator..." -ForegroundColor Yellow
Invoke-RestMethod -Uri 'http://localhost:7363/lead-intake' -Method Post -Body $payload -ContentType 'application/json'
Write-Host "✅ Done! Customer will receive email." -ForegroundColor Green