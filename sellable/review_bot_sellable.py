import os
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from license_system import LicenseSystem

class ReviewBot:
    def __init__(self):
        # Check license
        license = LicenseSystem()
        if not license.check_or_prompt():
            print("\n❌ License check failed")
            exit(1)
        
        self.config_file = "bot_config.json"
        self.load_config()
        self.setup_driver()
    
    def load_config(self):
        """Load configuration"""
        if not os.path.exists(self.config_file):
            self.first_setup()
        
        with open(self.config_file, 'r') as f:
            cfg = json.load(f)
            self.google_email = cfg['google_email']
            self.google_password = cfg['google_password']
            self.business_name = cfg['business_name']
            self.ai_url = cfg.get('ai_url', 'http://127.0.0.1:11434')
            self.ai_model = cfg.get('ai_model', 'qwen2.5:7b-instruct')
            self.reply_tone = cfg.get('reply_tone', 'professional and friendly')
    
    def first_setup(self):
        """First time configuration"""
        print("\n" + "="*60)
        print("INITIAL SETUP")
        print("="*60)
        
        google_email = input("Google Business Email: ").strip()
        google_password = input("Google Business Password: ").strip()
        business_name = input("Business Name: ").strip()
        
        print("\nAI Configuration:")
        print("1. Ollama (http://127.0.0.1:11434)")
        print("2. LM Studio (http://127.0.0.1:1234)")
        print("3. Custom URL")
        choice = input("Select [1/2/3]: ").strip()
        
        if choice == "1":
            ai_url = "http://127.0.0.1:11434"
        elif choice == "2":
            ai_url = "http://127.0.0.1:1234/v1"
        else:
            ai_url = input("Enter AI URL: ").strip()
        
        ai_model = input("Model name (default: qwen2.5:7b-instruct): ").strip() or "qwen2.5:7b-instruct"
        reply_tone = input("Reply tone (default: professional and friendly): ").strip() or "professional and friendly"
        
        config = {
            'google_email': google_email,
            'google_password': google_password,
            'business_name': business_name,
            'ai_url': ai_url,
            'ai_model': ai_model,
            'reply_tone': reply_tone
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✓ Configuration saved!")
        
        self.google_email = google_email
        self.google_password = google_password
        self.business_name = business_name
        self.ai_url = ai_url
        self.ai_model = ai_model
        self.reply_tone = reply_tone
    
    def setup_driver(self):
        """Setup Chrome"""
        opts = Options()
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--start-maximized")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=opts
        )
        self.wait = WebDriverWait(self.driver, 20)
    
    def login_google(self):
        """Login to Google"""
        print("Logging in...")
        self.driver.get("https://accounts.google.com")
        
        email_field = self.wait.until(EC.presence_of_element_located((By.ID, "identifierId")))
        email_field.send_keys(self.google_email)
        self.driver.find_element(By.ID, "identifierNext").click()
        time.sleep(3)
        
        password_field = self.wait.until(EC.presence_of_element_located((By.NAME, "Passwd")))
        password_field.send_keys(self.google_password)
        self.driver.find_element(By.ID, "passwordNext").click()
        time.sleep(5)
        
        print("✓ Logged in")
    
    def goto_reviews(self):
        """Navigate to reviews"""
        self.driver.get("https://business.google.com/reviews")
        time.sleep(5)
    
    def get_unanswered(self):
        """Find unanswered reviews"""
        reviews = []
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-review-id]")
            
            for el in elements:
                if not el.find_elements(By.CSS_SELECTOR, ".owner-response"):
                    text = el.find_element(By.CSS_SELECTOR, ".review-text").text
                    rating = len(el.find_elements(By.CSS_SELECTOR, ".star-icon.filled"))
                    reviews.append({'element': el, 'text': text, 'rating': rating})
        except:
            pass
        
        return reviews
    
    def generate_reply(self, review_text, rating):
        """Generate AI reply using local model"""
        prompt = f"""Generate a {self.reply_tone} response to this {rating}-star review for {self.business_name}.

Review: {review_text}

Requirements:
- Under 500 characters
- Sound human and genuine
- Thank them
- Address specific points
- Maintain {self.reply_tone} tone

Reply:"""
        
        try:
            # Try Ollama format
            response = requests.post(
                f"{self.ai_url}/api/generate",
                json={
                    "model": self.ai_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['response'].strip()
        except:
            pass
        
        try:
            # Try OpenAI-compatible format (LM Studio)
            response = requests.post(
                f"{self.ai_url}/chat/completions",
                json={
                    "model": self.ai_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
        except:
            pass
        
        return "Thank you for your feedback!"
    
    def post_reply(self, review_el, reply_text):
        """Post reply"""
        try:
            reply_btn = review_el.find_element(By.CSS_SELECTOR, "[aria-label*='Reply']")
            reply_btn.click()
            time.sleep(2)
            
            textarea = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea")))
            textarea.send_keys(reply_text)
            time.sleep(1)
            
            submit = self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Post']")
            submit.click()
            time.sleep(3)
            
            return True
        except:
            return False
    
    def run(self, interval=300):
        """Main loop"""
        print("\n" + "="*60)
        print(f"REVIEW BOT RUNNING: {self.business_name}")
        print("="*60)
        
        try:
            self.login_google()
            self.goto_reviews()
            
            while True:
                # Check subscription every run
                license = LicenseSystem()
                if not license.check_subscription():
                    print("\n❌ Subscription expired. Stopping.")
                    break
                
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking reviews...")
                
                reviews = self.get_unanswered()
                print(f"Found {len(reviews)} unanswered")
                
                for r in reviews:
                    print(f"\nProcessing {r['rating']}-star review...")
                    
                    reply = self.generate_reply(r['text'], r['rating'])
                    print(f"Reply: {reply[:80]}...")
                    
                    if self.post_reply(r['element'], reply):
                        print("✓ Posted")
                    else:
                        print("❌ Failed")
                    
                    time.sleep(10)
                
                print(f"\nSleeping {interval}s...")
                time.sleep(interval)
                self.driver.refresh()
                time.sleep(5)
        
        except KeyboardInterrupt:
            print("\n\nStopped by user")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    bot = ReviewBot()
    bot.run(interval=300)