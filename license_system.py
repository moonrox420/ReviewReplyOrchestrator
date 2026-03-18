import hashlib
import json
import os
import requests
from datetime import datetime, timedelta

class LicenseSystem:
    def __init__(self):
        self.license_file = "license.json"
        self.master_key = "MOONROX2026"
    
    def generate_license(self, customer_email, purchase_id):
        """Generate license key for new customer"""
        raw = f"{customer_email}{purchase_id}{self.master_key}"
        key = hashlib.sha256(raw.encode()).hexdigest()[:24].upper()
        return f"MRX-{key[:8]}-{key[8:16]}-{key[16:24]}"
    
    def activate(self, license_key, customer_email):
        """Activate license on first use"""
        license_data = {
            'license_key': license_key,
            'customer_email': customer_email,
            'activated_on': datetime.now().isoformat(),
            'subscription_active': True,
            'last_check': datetime.now().isoformat()
        }
        
        with open(self.license_file, 'w') as f:
            json.dump(license_data, f)
        
        return True
    
    def check_subscription(self):
        """Check if subscription is still active"""
        if not os.path.exists(self.license_file):
            return False
        
        with open(self.license_file, 'r') as f:
            data = json.load(f)
        
        # Update last check time
        data['last_check'] = datetime.now().isoformat()
        
        with open(self.license_file, 'w') as f:
            json.dump(data, f)
        
        return data.get('subscription_active', False)
    
    def check_or_prompt(self):
        """Check for valid license or prompt activation"""
        if os.path.exists(self.license_file):
            if self.check_subscription():
                with open(self.license_file, 'r') as f:
                    data = json.load(f)
                print(f"✓ Active subscription for: {data.get('customer_email')}")
                return True
            else:
                print("\n❌ SUBSCRIPTION EXPIRED")
                print("Renew at: https://gumroad.com/yourlinkhere")
                return False
        
        print("\n" + "="*60)
        print("LICENSE ACTIVATION")
        print("="*60)
        license_key = input("Enter license key: ").strip()
        email = input("Enter email: ").strip()
        
        if not license_key.startswith("MRX-") or len(license_key) != 30:
            print("❌ Invalid license key")
            return False
        
        self.activate(license_key, email)
        print("✓ License activated!")
        return True
