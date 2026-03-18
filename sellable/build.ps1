# Build executable
pip install pyinstaller

pyinstaller --onefile `
    --name "ReviewBot" `
    --add-data "license_system.py;." `
    review_bot_sellable.py

Write-Host "Build complete: dist/ReviewBot.exe"