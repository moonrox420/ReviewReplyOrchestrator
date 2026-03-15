# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile --name "ReviewReplyBot" review_reply_bot_sellable.py

Write-Host "Executable created in dist/ReviewReplyBot.exe"