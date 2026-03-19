import os
import re
import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


def safe_get_env(var_name, default=None):
    """Safely get an environment variable with a default fallback.
    
    Args:
        var_name: Environment variable name
        default: Default value if not found
        
    Returns:
        str: Environment variable value or default
    """
    return os.environ.get(var_name, default)


def format_currency(cents):
    """Format cents as a currency string.
    
    Args:
        cents: Amount in cents (int or str)
        
    Returns:
        str: Formatted currency string (e.g., "$99.00")
    """
    try:
        if isinstance(cents, str):
            cents = int(cents)
        return f'${cents / 100:,.2f}'
    except (ValueError, TypeError) as e:
        logger.error(f'Invalid currency value: {cents}')
        return '$0.00'


def validate_email(email):
    """Validate an email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if valid email format
    """
    if not email:
        return False
    
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def generate_order_id():
    """Generate a unique order ID.
    
    Returns:
        str: Unique order ID in format ORD-{uuid_short}
    """
    short_uuid = str(uuid.uuid4())[:8].upper()
    return f'ORD-{short_uuid}'


def generate_unique_id(prefix=''):
    """Generate a unique identifier with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID
        
    Returns:
        str: Unique identifier
    """
    short_uuid = str(uuid.uuid4())[:12].upper()
    if prefix:
        return f'{prefix}-{short_uuid}'
    return short_uuid


def json_serial(obj):
    """JSON serializer for objects not serializable by default.
    
    Args:
        obj: Object to serialize
        
    Returns:
        Serialized representation
        
    Raises:
        TypeError: If object type is not serializable
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, '__dict__'):
        return obj.__dict__
    raise TypeError(f'Type {type(obj).__name__} is not JSON serializable')


def safe_json_dumps(data):
    """Safely serialize data to JSON string.
    
    Args:
        data: Data to serialize
        
    Returns:
        str: JSON string or None if serialization fails
    """
    try:
        return json.dumps(data, default=json_serial)
    except (TypeError, ValueError) as e:
        logger.error(f'JSON serialization failed: {str(e)}')
        return None


def safe_json_loads(json_str):
    """Safely deserialize JSON string to Python object.
    
    Args:
        json_str: JSON string to deserialize
        
    Returns:
        dict/list: Deserialized object or None if parsing fails
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f'JSON deserialization failed: {str(e)}')
        return None


def sanitize_string(input_str, max_length=None):
    """Sanitize a string by removing potentially dangerous characters.
    
    Args:
        input_str: String to sanitize
        max_length: Optional maximum length
        
    Returns:
        str: Sanitized string
    """
    if not input_str:
        return ''
    
    # Remove control characters
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', str(input_str))
    
    # Strip whitespace
    sanitized = sanitized.strip()
    
    # Truncate if needed
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def parse_amount_to_cents(amount):
    """Parse a monetary amount to cents.
    
    Args:
        amount: Amount as string, float, or int
        
    Returns:
        int: Amount in cents
    """
    try:
        if isinstance(amount, str):
            # Remove currency symbols
            amount = re.sub(r'[$€£,]', '', amount)
            amount = float(amount)
        elif isinstance(amount, Decimal):
            amount = float(amount)
        
        return int(round(amount * 100))
    except (ValueError, TypeError) as e:
        logger.error(f'Failed to parse amount: {amount}')
        return 0


def mask_email(email):
    """Mask an email address for logging/display.
    
    Args:
        email: Email address to mask
        
    Returns:
        str: Masked email (e.g., "u***@example.com")
    """
    if not email or '@' not in email:
        return '***'
    
    local, domain = email.split('@', 1)
    if len(local) <= 1:
        masked_local = '*'
    else:
        masked_local = local[0] + '***'
    
    return f'{masked_local}@{domain}'


def mask_license_key(license_key):
    """Mask a license key for logging/display.
    
    Args:
        license_key: License key to mask
        
    Returns:
        str: Masked license key (e.g., "DRX-****-****")
    """
    if not license_key:
        return '****'
    
    parts = license_key.split('-')
    if len(parts) >= 2:
        return f'{parts[0]}-****-****'
    
    return license_key[:4] + '****'


def get_timestamp():
    """Get current UTC timestamp as ISO string.
    
    Returns:
        str: ISO format timestamp
    """
    return datetime.utcnow().isoformat()


def log_request(request):
    """Log HTTP request details.
    
    Args:
        request: FastAPI/Flask request object
    """
    try:
        logger.info(
            f'Request: {request.method} {request.url.path} '
            f'- Client: {request.client.host if request.client else "unknown"}'
        )
    except Exception as e:
        logger.error(f'Failed to log request: {str(e)}')


def log_error(error, context=None):
    """Log an error with optional context.
    
    Args:
        error: Exception or error message
        context: Optional context dictionary
    """
    error_msg = f'Error: {str(error)}'
    if context:
        error_msg += f' | Context: {json.dumps(context)}'
    logger.error(error_msg)


def chunk_list(lst, chunk_size):
    """Split a list into chunks.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        list: List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d, parent_key='', sep='.'):
    """Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key for recursion
        sep: Separator between keys
        
    Returns:
        dict: Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f'{parent_key}{sep}{k}' if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)