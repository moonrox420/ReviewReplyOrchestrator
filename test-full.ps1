# PowerShell — test-full.ps1
$reviews = 1..10 | ForEach-Object { @{rating=(Get-Random -Min 1 -Max 6); text="Sample review "} }
$payload = @{
  business_name='RoofPro USA'
  email='owner@roofprousa.example'
  persona='trades'
  compliance_profile='General'
  tone_style='Direct'
  signoff='– Mike, Owner'
  private_email='support@roofpro.example'
  reviews=$reviews
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri 'http://127.0.0.1:7364/intake-submit' -Method Post -Body $payload -ContentType 'application/json'
