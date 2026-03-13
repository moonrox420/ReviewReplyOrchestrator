# test-lead.ps1
$payload = @{
  business_name='Bright Smiles Dental'
  email='client@example.com'
  persona='dentist_medspa'
  compliance_profile='HIPAA'
  tone_style='Warm'
  signoff='– Dr. Patel, Owner'
  private_email='support@brightsmiles.example'
  reviews_sample=@(
    @{rating=5; text='Amazing hygienist. Friendly staff.'},
    @{rating=2; text='Waited 40 minutes. Not happy.'},
    @{rating=4; text='Great cleaning, lobby was busy.'},
    @{rating=5; text='Love this place.'},
    @{rating=3; text='Good service, a bit pricey.'}
  )
} | ConvertTo-Json -Depth 6
Invoke-RestMethod -Uri 'http://127.0.0.1:7363/lead-intake' -Method Post -Body $payload -ContentType 'application/json'
