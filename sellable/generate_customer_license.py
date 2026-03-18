from license_validator import LicenseValidator

def generate_new_license():
    """Generate license key for new customer"""
    validator = LicenseValidator()
    
    customer_email = input("Customer email: ").strip()
    license_key = validator.generate_license(customer_email)
    
    print("\n" + "="*60)
    print("NEW LICENSE GENERATED")
    print("="*60)
    print(f"Customer: {customer_email}")
    print(f"License Key: {license_key}")
    print("="*60)
    print("\nSend this license key to your customer.")

if __name__ == "__main__":
    generate_new_license()
