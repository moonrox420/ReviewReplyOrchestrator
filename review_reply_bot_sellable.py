import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import anthropic
from license_validator import LicenseValidator

class ReviewReplyBot:
    def __init__(self):
        # CHECK LICENSE FIRST
        validator = LicenseValidator()
        if not validator.check_or_prompt():
            print("\n❌ INVALID LICENSE. Contact your seller.")
            exit(1)
        
        self.config_file = "config.json"
        self.load_config()
        self.setup_driver()
    
    def load_config(self):
        """Load user configuration"""
        if not os.path.exists(self.config_file):
            self.first_time_setup()
        
        with open(self.config_file, 'r') as f:
            config = json.load(f)
            self.google_email = config['google_email']
            self.google_password = config['google_password']
            self.anthropic_key = config['anthropic_key']
            self.business_name = config['business_name']
            self.reply_tone = config.get('reply_tone', 'professional and friendly')
    
    def first_time_setup(self):
        """First-time configuration wizard"""
        print("\n" + "="*60)
        print("FIRST TIME SETUP")
        print("="*60)
        
        google_email = input("Google Business Profile Email: ").strip()
        google_password = input("Google Business Profile Password: ").strip()
        anthropic_key = input("Anthropic API Key: ").strip()
        business_name = input("Your Business Name: ").strip()
        reply_tone = input("Reply Tone (default: professional and friendly): ").strip() or "professional and friendly"
        
        config = {
            'google_email': google_email,
            'google_password': google_password,
            'anthropic_key': anthropic_key,
            'business_name': business_name,
            'reply_tone': reply_tone
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print("✓ Configuration saved!")
        self.google_email = google_email
        self.google_password = google_password
        self.anthropic_key = anthropic_key
        self.business_name = business_name
        self.reply_tone = reply_tone
    
    def setup_driver(self):
        """Setup Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
    
    def login_google(self):
        """Login to Google account"""
        print("Logging into Google...")
        self.driver.get("https://accounts.google.com")
        
        # Email
        email_field = self.wait.until(EC.presence_of_element_located((By.ID, "identifierId")))
        email_field.send_keys(self.google_email)
        self.driver.find_element(By.ID, "identifierNext").click()
        time.sleep(3)
        
        # Password
        password_field = self.wait.until(EC.presence_of_element_located((By.NAME, "Passwd")))
        password_field.send_keys(self.google_password)
        self.driver.find_element(By.ID, "passwordNext").click()
        time.sleep(5)
        
        print("✓ Logged in successfully")
    
    def navigate_to_reviews(self):
        """Navigate to Google Business reviews"""
        print("Navigating to reviews...")
        self.driver.get("https://business.google.com/reviews")
        time.sleep(5)
    
    def get_unanswered_reviews(self):
        """Find all unanswered reviews"""
        reviews = []
        try:
            review_elements = self.driver.find_elements(By.CSS_SELECTOR, "[data-review-id]")
            
            for element in review_elements:
                # Check if already replied
                replied = element.find_elements(By.CSS_SELECTOR, ".owner-response")
                if not replied:
                    review_text = element.find_element(By.CSS_SELECTOR, ".review-text").text
                    rating = len(element.find_elements(By.CSS_SELECTOR, ".star-icon.filled"))
                    reviews.append({
                        'element': element,
                        'text': review_text,
                        'rating': rating
                    })
        except Exception as e:
            print(f"Error finding reviews: {e}")
        
        return reviews
    
    def generate_reply(self, review_text, rating):
        """Generate AI reply using Claude"""
        client = anthropic.Anthropic(api_key=self.anthropic_key)
        
        prompt = f"""Generate a {self.reply_tone} response to this {rating}-star Google review for {self.business_name}.

Review: {review_text}

Requirements:
- Keep it under 500 characters
- Sound genuine and human
- Thank them for the feedback
- Address specific points they mentioned
- Maintain {self.reply_tone} tone

Reply:"""
        
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text.strip()
    
    def post_reply(self, review_element, reply_text):
        """Post reply to review"""
        try:
            # Click reply button
            reply_button = review_element.find_element(By.CSS_SELECTOR, "[aria-label*='Reply']")
            reply_button.click()
            time.sleep(2)
            
            # Enter reply
            text_area = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "textarea")))
            text_area.send_keys(reply_text)
            time.sleep(1)
            
            # Submit
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "[aria-label*='Post']")
            submit_button.click()
            time.sleep(3)
            
            return True
        except Exception as e:
            print(f"Error posting reply: {e}")
            return False
    
    def run(self, check_interval=300):
        """Main monitoring loop"""
        print("\n" + "="*60)
        print(f"REVIEW REPLY BOT RUNNING FOR: {self.business_name}")
        print("="*60)
        
        try:
            self.login_google()
            self.navigate_to_reviews()
            
            while True:
                print(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking for new reviews...")
                
                reviews = self.get_unanswered_reviews()
                print(f"Found {len(reviews)} unanswered reviews")
                
                for review in reviews:
                    print(f"\nProcessing {review['rating']}-star review...")
                    print(f"Review: {review['text'][:100]}...")
                    
                    reply = self.generate_reply(review['text'], review['rating'])
                    print(f"Generated reply: {reply[:100]}...")
                    
                    if self.post_reply(review['element'], reply):
                        print("✓ Reply posted successfully")
                    else:
                        print("❌ Failed to post reply")
                    
                    time.sleep(10)  # Delay between replies
                
                print(f"\nSleeping for {check_interval} seconds...")
                time.sleep(check_interval)
                
                # Refresh page
                self.driver.refresh()
                time.sleep(5)
        
        except KeyboardInterrupt:
            print("\n\nBot stopped by user")
        finally:
            self.driver.quit()

if __name__ == "__main__":
    bot = ReviewReplyBot()
    bot.run(check_interval=300)  # Check every 5 minutes