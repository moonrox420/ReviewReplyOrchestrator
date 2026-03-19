import boto3
import logging
import os
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ProductDeliveryService:
    """Service for managing product delivery via S3 pre-signed URLs."""
    
    def __init__(self, bucket_name=None, region_name=None):
        """Initialize product delivery service with S3 configuration.
        
        Args:
            bucket_name: S3 bucket name (defaults to env var AWS_S3_BUCKET)
            region_name: AWS region (defaults to env var AWS_REGION or us-east-1)
        """
        self.bucket_name = bucket_name or os.getenv('AWS_S3_BUCKET', 'droxai-products')
        self.region_name = region_name or os.getenv('AWS_REGION', 'us-east-1')
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            region_name=self.region_name,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
        # Default expiration: 7 days
        self.default_expiration = 604800
    
    def generate_download_url(self, product_key, expiration_seconds=None):
        """Generate a pre-signed S3 URL for product download.
        
        Args:
            product_key: Product identifier key
            expiration_seconds: URL expiration time in seconds (default: 7 days)
            
        Returns:
            str: Pre-signed download URL
            
        Raises:
            Exception: If URL generation fails
        """
        try:
            expiration = expiration_seconds or self.default_expiration
            
            # Construct the S3 object key
            object_key = f"products/{product_key}/installer.zip"
            
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            
            logger.info(f"Download URL generated for product: {product_key}")
            return url
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise Exception("AWS credentials not configured")
        except PartialCredentialsError:
            logger.error("Incomplete AWS credentials")
            raise Exception("Incomplete AWS credentials")
        except ClientError as e:
            logger.error(f"S3 client error: {str(e)}")
            raise Exception(f"Failed to generate download URL: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error generating download URL: {str(e)}")
            raise
    
    def upload_product(self, file_path, product_key):
        """Upload a product installer to S3.
        
        Args:
            file_path: Local path to the file to upload
            product_key: Product identifier key
            
        Returns:
            bool: True if upload successful
            
        Raises:
            Exception: If upload fails
        """
        try:
            object_key = f"products/{product_key}/installer.zip"
            
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                object_key
            )
            
            logger.info(f"Product uploaded successfully: {product_key}")
            return True
            
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise Exception(f"File not found: {file_path}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise Exception("AWS credentials not configured")
        except ClientError as e:
            logger.error(f"S3 upload error: {str(e)}")
            raise Exception(f"Failed to upload product: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading product: {str(e)}")
            raise
    
    def check_product_exists(self, product_key):
        """Check if a product exists in S3.
        
        Args:
            product_key: Product identifier key
            
        Returns:
            bool: True if product exists
        """
        try:
            object_key = f"products/{product_key}/installer.zip"
            
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return True
            
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking product existence: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking product: {str(e)}")
            return False
    
    def get_product_metadata(self, product_key):
        """Get metadata for a product in S3.
        
        Args:
            product_key: Product identifier key
            
        Returns:
            dict: Product metadata including size, last modified, etc.
        """
        try:
            object_key = f"products/{product_key}/installer.zip"
            
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            return {
                'product_key': product_key,
                'size_bytes': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified', ''),
                'content_type': response.get('ContentType', ''),
                'etag': response.get('ETag', '')
            }
            
        except ClientError as e:
            logger.error(f"Error getting product metadata: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting metadata: {str(e)}")
            return None
    
    def delete_product(self, product_key):
        """Delete a product from S3.
        
        Args:
            product_key: Product identifier key
            
        Returns:
            bool: True if deletion successful
        """
        try:
            object_key = f"products/{product_key}/installer.zip"
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info(f"Product deleted successfully: {product_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting product: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error deleting product: {str(e)}")
            return False
    
    def list_products(self, prefix="products/"):
        """List all products in the S3 bucket.
        
        Args:
            prefix: S3 prefix to list (default: "products/")
            
        Returns:
            list: List of product keys
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            products = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Extract product key from object key
                    key = obj['Key']
                    if key.endswith('/installer.zip'):
                        product_key = key.replace('products/', '').replace('/installer.zip', '')
                        products.append({
                            'product_key': product_key,
                            'size': obj['Size'],
                            'last_modified': obj['LastModified']
                        })
            
            return products
            
        except ClientError as e:
            logger.error(f"Error listing products: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing products: {str(e)}")
            return []