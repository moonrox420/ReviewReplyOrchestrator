import os
from typing import Dict, Any, Optional


class DatabaseConfig:
    """Database configuration settings."""
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL from environment or use default SQLite."""
        return os.getenv('DATABASE_URL', 'sqlite:///fulfillment.db')


class StripeConfig:
    """Stripe API configuration settings."""
    
    @staticmethod
    def get_api_key() -> str:
        """Get Stripe API key from environment."""
        return os.getenv('STRIPE_API_KEY', '')
    
    @staticmethod
    def get_webhook_secret() -> str:
        """Get Stripe webhook secret from environment."""
        return os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    @staticmethod
    def is_test_mode() -> bool:
        """Check if running in test mode."""
        api_key = StripeConfig.get_api_key()
        return api_key.startswith('sk_test_') if api_key else True


class EmailConfig:
    """Email/SMTP configuration settings."""
    
    @staticmethod
    def get_smtp_host() -> str:
        return os.getenv('SMTP_HOST', 'smtp.gmail.com')
    
    @staticmethod
    def get_smtp_port() -> int:
        return int(os.getenv('SMTP_PORT', '587'))
    
    @staticmethod
    def get_smtp_user() -> str:
        return os.getenv('SMTP_USER', '')
    
    @staticmethod
    def get_smtp_password() -> str:
        return os.getenv('SMTP_PASSWORD', '')
    
    @staticmethod
    def get_config() -> Dict[str, Any]:
        return {
            'host': EmailConfig.get_smtp_host(),
            'port': EmailConfig.get_smtp_port(),
            'user': EmailConfig.get_smtp_user(),
            'password': EmailConfig.get_smtp_password()
        }


class S3Config:
    """AWS S3 configuration settings."""
    
    @staticmethod
    def get_access_key() -> str:
        return os.getenv('AWS_ACCESS_KEY_ID', '')
    
    @staticmethod
    def get_secret_key() -> str:
        return os.getenv('AWS_SECRET_ACCESS_KEY', '')
    
    @staticmethod
    def get_bucket() -> str:
        return os.getenv('AWS_S3_BUCKET', 'droxai-products')
    
    @staticmethod
    def get_region() -> str:
        return os.getenv('AWS_REGION', 'us-east-1')
    
    @staticmethod
    def get_config() -> Dict[str, str]:
        return {
            'access_key': S3Config.get_access_key(),
            'secret_key': S3Config.get_secret_key(),
            'bucket': S3Config.get_bucket(),
            'region': S3Config.get_region()
        }


class ServerConfig:
    """Server configuration settings."""
    
    @staticmethod
    def get_host() -> str:
        return os.getenv('API_HOST', '0.0.0.0')
    
    @staticmethod
    def get_port() -> int:
        return int(os.getenv('API_PORT', '8000'))
    
    @staticmethod
    def is_debug() -> bool:
        return os.getenv('DEBUG', 'false').lower() == 'true'


class ProductConfig:
    """Product catalog and pricing configuration."""
    
    PRODUCTS = {
        'review_reply_starter': {
            'name': 'Review Reply Sprint - Starter',
            'price_cents': 9900,
            'price_display': '$99/mo',
            'yearly_price_cents': 9900,
            'yearly_display': '$990/year',
            'product_key': 'review_reply_starter_v1.0',
            'max_users': 1,
            'features': [
                'Single location',
                'Unlimited review responses',
                'Standard brand voice training',
                'Email support',
                'Quarterly updates',
                'Self-hosted deployment'
            ]
        },
        'review_reply_business': {
            'name': 'Review Reply Sprint - Business',
            'price_cents': 19900,
            'price_display': '$199/mo',
            'yearly_price_cents': 19900,
            'yearly_display': '$1,990/year',
            'product_key': 'review_reply_business_v1.0',
            'max_users': 5,
            'features': [
                'Up to 5 locations',
                'Unlimited review responses',
                'Advanced brand voice training',
                'Priority email support',
                'Monthly updates',
                'White-label options',
                'API access'
            ]
        },
        'review_reply_enterprise': {
            'name': 'Review Reply Sprint - Enterprise',
            'price_cents': 39900,
            'price_display': '$399/mo',
            'yearly_price_cents': 39900,
            'yearly_display': '$3,990/year',
            'product_key': 'review_reply_enterprise_v1.0',
            'max_users': None,
            'features': [
                'Unlimited locations',
                'Unlimited review responses',
                'Dedicated account manager',
                'Phone + email support',
                'Weekly updates',
                'Full white-label rights',
                'Custom integrations'
            ]
        },
        'toad_solo': {
            'name': 'TOAD - Solo',
            'price_cents': 4900,
            'price_display': '$49/mo',
            'yearly_price_cents': 4900,
            'yearly_display': '$490/year',
            'product_key': 'toad_solo_v1.0',
            'max_users': 1,
            'features': [
                '1 developer',
                'Unlimited generations',
                'Multi-language support',
                'Auto-test & rollback',
                'Email support',
                'Quarterly updates'
            ]
        },
        'toad_team': {
            'name': 'TOAD - Team',
            'price_cents': 12900,
            'price_display': '$129/mo',
            'yearly_price_cents': 12900,
            'yearly_display': '$1,290/year',
            'product_key': 'toad_team_v1.0',
            'max_users': 5,
            'features': [
                'Up to 5 developers',
                'Unlimited generations',
                'Priority code generation',
                'Team collaboration tools',
                'Priority email support',
                'Monthly updates',
                'Custom model training'
            ]
        },
        'toad_enterprise': {
            'name': 'TOAD - Enterprise',
            'price_cents': 29900,
            'price_display': '$299/mo',
            'yearly_price_cents': 29900,
            'yearly_display': '$2,990/year',
            'product_key': 'toad_enterprise_v1.0',
            'max_users': None,
            'features': [
                'Unlimited developers',
                'Unlimited generations',
                'Dedicated support',
                'SSO integration',
                'Weekly updates',
                'Custom model training',
                'API access'
            ]
        },
        'droxcli_individual': {
            'name': 'DroxCLI - Individual',
            'price_cents': 2900,
            'price_display': '$29/mo',
            'yearly_price_cents': 2900,
            'yearly_display': '$290/year',
            'product_key': 'droxcli_individual_v1.0',
            'max_users': 1,
            'features': [
                '1 user',
                'Unlimited commands',
                'Automatic rollback',
                'Safety validations',
                'Email support',
                'Quarterly updates'
            ]
        },
        'droxcli_team': {
            'name': 'DroxCLI - Team',
            'price_cents': 7900,
            'price_display': '$79/mo',
            'yearly_price_cents': 7900,
            'yearly_display': '$790/year',
            'product_key': 'droxcli_team_v1.0',
            'max_users': 10,
            'features': [
                'Up to 10 users',
                'Unlimited commands',
                'Ollama/local LLM support',
                'Git integration',
                'Priority email support',
                'Monthly updates',
                'Shared command history'
            ]
        },
        'droxcli_enterprise': {
            'name': 'DroxCLI - Enterprise',
            'price_cents': 14900,
            'price_display': '$149/mo',
            'yearly_price_cents': 14900,
            'yearly_display': '$1,490/year',
            'product_key': 'droxcli_enterprise_v1.0',
            'max_users': None,
            'features': [
                'Unlimited users',
                'Unlimited commands',
                'Custom integrations',
                'SSO integration',
                'Phone + email support',
                'Weekly updates',
                'Custom LLM support'
            ]
        },
        'proconstruct_trade': {
            'name': 'ProConstruct - Trade Pro',
            'price_cents': 14900,
            'price_display': '$149/mo',
            'yearly_price_cents': 14900,
            'yearly_display': '$1,490/year',
            'product_key': 'proconstruct_trade_v1.0',
            'max_users': 1,
            'features': [
                '1 user',
                'Unlimited quotes',
                'Material estimation',
                'Project timelines',
                'Email support',
                'Quarterly updates'
            ]
        },
        'proconstruct_crew': {
            'name': 'ProConstruct - Crew',
            'price_cents': 29900,
            'price_display': '$299/mo',
            'yearly_price_cents': 29900,
            'yearly_display': '$2,990/year',
            'product_key': 'proconstruct_crew_v1.0',
            'max_users': 5,
            'features': [
                'Up to 5 users',
                'Unlimited quotes',
                'Client management',
                'Compliance tracking',
                'Priority email support',
                'Monthly updates',
                'Mobile app access'
            ]
        },
        'proconstruct_enterprise': {
            'name': 'ProConstruct - Enterprise',
            'price_cents': 49900,
            'price_display': '$499/mo',
            'yearly_price_cents': 49900,
            'yearly_display': '$4,990/year',
            'product_key': 'proconstruct_enterprise_v1.0',
            'max_users': None,
            'features': [
                'Unlimited users',
                'Unlimited quotes',
                'Multi-location support',
                'Dedicated account manager',
                'Phone + email support',
                'Weekly updates',
                'API access'
            ]
        },
        'autocampaigns_starter': {
            'name': 'AutoCampaigns - Starter',
            'price_cents': 7900,
            'price_display': '$79/mo',
            'yearly_price_cents': 7900,
            'yearly_display': '$790/year',
            'product_key': 'autocampaigns_starter_v1.0',
            'max_users': 1,
            'features': [
                '1 user',
                'Unlimited contacts',
                'Email campaigns',
                'Basic automation',
                'Email support',
                'Quarterly updates'
            ]
        },
        'autocampaigns_growth': {
            'name': 'AutoCampaigns - Growth',
            'price_cents': 14900,
            'price_display': '$149/mo',
            'yearly_price_cents': 14900,
            'yearly_display': '$1,490/year',
            'product_key': 'autocampaigns_growth_v1.0',
            'max_users': 5,
            'features': [
                'Up to 5 users',
                'Unlimited contacts',
                'Email + SMS campaigns',
                'Advanced automation',
                'Priority email support',
                'Monthly updates',
                'Social scheduling'
            ]
        },
        'autocampaigns_agency': {
            'name': 'AutoCampaigns - Agency',
            'price_cents': 29900,
            'price_display': '$299/mo',
            'yearly_price_cents': 29900,
            'yearly_display': '$2,990/year',
            'product_key': 'autocampaigns_agency_v1.0',
            'max_users': None,
            'features': [
                'Unlimited users',
                'Unlimited contacts',
                'Multi-client support',
                'White-label options',
                'Phone + email support',
                'Weekly updates',
                'API access'
            ]
        }
    }
    
    @staticmethod
    def get_product(plan_id: str) -> Optional[Dict[str, Any]]:
        """Get product configuration by plan ID."""
        return ProductConfig.PRODUCTS.get(plan_id)
    
    @staticmethod
    def get_all_products() -> Dict[str, Dict[str, Any]]:
        """Get all product configurations."""
        return ProductConfig.PRODUCTS
    
    @staticmethod
    def get_price_cents(plan_id: str) -> int:
        """Get price in cents for a plan."""
        product = ProductConfig.get_product(plan_id)
        return product['price_cents'] if product else 0