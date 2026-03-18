from license_system import LicenseSystem

def main():
    system = LicenseSystem()
    
    email = input("Customer email: ").strip()
    purchase_id = input("Gumroad purchase ID: ").strip()
    
    license_key = system.generate_license(email, purchase_id)
    
    print("\n" + "="*60)
    print("LICENSE GENERATED")
    print("="*60)
    print(f"Customer: {email}")
    print(f"Purchase: {purchase_id}")
    print(f"License:  {license_key}")
    print("="*60)
    print("\nSend this key to customer")

if __name__ == "__main__":
    main()
