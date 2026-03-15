import hashlib
import json
import os
from datetime import datetime

class LicenseValidator:
    def __init__(self):
        self.license_file = "license.key"
        self.master_key = "MOONROX2026"  # Your master validation key
    
    def generate_license(self, customer_email):
        """Generate unique license key for customer"""
        timestamp = datetime.now().strftime("%Y%m%d")
        raw = f"{customer_email}{timestamp}{self.master_key}"
        license_key = hashlib.sha256(raw.encode()).hexdigest()[:24].upper()
        return f"MRX-{license_key[:8]}-{license_key[8:16]}-{license_key[16:24]}"
    
    def validate_license(self, license_key):
        """Check if license key is valid"""
        if not os.path.exists(self.license_file):
            return False
        
        try:
            with open(self.license_file, 'r') as f:
                stored_data = json.load(f)
                return stored_data.get('license_key') == license_key and stored_data.get('active', False)
        except:
            return False
    
    def activate_license(self, license_key, customer_email):
        """Activate license on customer's machine"""
        license_data = {
            'license_key': license_key,
            'customer_email': customer_email,
            'activated_on': datetime.now().isoformat(),
            'active': True
        }
        
        with open(self.license_file, 'w') as f:
            json.dump(license_data, f)
        
        return True
    
    def check_or_prompt(self):
        """Check for valid license or prompt user to enter one"""
        if os.path.exists(self.license_file):
            with open(self.license_file, 'r') as f:
                data = json.load(f)
                if data.get('active'):
                    print(f"✓ License active for: {data.get('customer_email')}")
                    return True
        
        print("\n" + "="*60)
        print("LICENSE ACTIVATION REQUIRED")
        print("="*60)
        license_key = input("Enter your license key: ").strip()
        email = input("Enter your email: ").strip()
        
        # Validate format
        if not license_key.startswith("MRX-") or len(license_key) != 30:
            print("❌ Invalid license key format")
            return False
        
        # Activate
        self.activate_license(license_key, email)
        print("✓ License activated successfully!")
        return True
