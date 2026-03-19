import logging
import uuid
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

class FulfillmentOrchestrator:
    """Orchestrates the complete payment fulfillment pipeline from order creation
    to license generation, product delivery, and email notification."""
    
    def __init__(self, db_session=None, email_service=None, product_delivery_service=None):
        """Initialize the fulfillment orchestrator with required services.
        
        Args:
            db_session: SQLAlchemy database session
            email_service: EmailService instance for sending emails
            product_delivery_service: ProductDeliveryService instance for S3 URLs
        """
        self.db_session = db_session
        self.email_service = email_service
        self.product_delivery_service = product_delivery_service
    
    def _get_db_session(self):
        """Get or create a database session."""
        if self.db_session:
            return self.db_session
        
        from payment_orchestration.models import Base, Order, License
        
        database_url = os.getenv('DATABASE_URL', 'sqlite:///fulfillment.db')
        engine = create_engine(database_url)
        Base.metadata.create_all(engine)
        
        Session = sessionmaker(bind=engine)
        return Session()
    
    async def fulfill_order(self, order_id, customer_email, customer_name, plan, payment_id, amount_cents):
        """Process a complete order fulfillment.
        
        This method orchestrates the entire fulfillment pipeline:
        1. Create order record
        2. Generate license key
        3. Generate product download URL
        4. Send delivery email
        5. Mark order as completed
        
        Args:
            order_id: Unique order identifier
            customer_email: Customer's email address
            customer_name: Customer's name
            plan: Product plan identifier
            payment_id: Stripe payment ID
            amount_cents: Payment amount in cents
            
        Returns:
            tuple: (success: bool, order_id: str, license_key: str or error_message)
        """
        session = self._get_db_session()
        
        try:
            logger.info(f"Starting fulfillment for order: {order_id}")
            
            # Import models
            from payment_orchestration.models import Order, License
            from payment_orchestration.license_service import LicenseGenerator
            from payment_orchestration.audit_logger import AuditLogger
            
            # Step 1: Create order record
            order = Order(
                order_id=order_id,
                customer_email=customer_email,
                customer_name=customer_name,
                plan=plan,
                payment_id=payment_id,
                amount_cents=amount_cents,
                status="payment_received",
                created_at=datetime.utcnow()
            )
            session.add(order)
            session.commit()
            
            AuditLogger.log_event(
                AuditLogger.EVENT_PAYMENT_RECEIVED,
                order_id,
                customer_email,
                {"plan": plan, "amount_cents": amount_cents}
            )
            logger.info(f"Order created: {order_id}")
            
            # Step 2: Generate license key
            generator = LicenseGenerator(prefix='DRX', validity_period=365*24*60*60)
            license_key = generator.generate_license_key()
            
            # Store license in database
            license_obj = License(
                license_key=license_key,
                order_id=order_id,
                plan=plan,
                customer_email=customer_email,
                activated_at=datetime.utcnow()
            )
            session.add(license_obj)
            
            order.status = "license_generated"
            session.commit()
            
            AuditLogger.log_event(
                AuditLogger.EVENT_LICENSE_GENERATED,
                order_id,
                customer_email,
                {"license_key": license_key[:10] + "..."}
            )
            logger.info(f"License generated for order: {order_id}")
            
            # Step 3: Generate product download URL
            if self.product_delivery_service:
                download_url = self.product_delivery_service.generate_download_url(plan)
            else:
                # Fallback: generate a placeholder URL
                download_url = f"https://products.droxai.com/download/{plan}/{license_key}"
            
            order.status = "product_prepared"
            session.commit()
            logger.info(f"Product URL generated for order: {order_id}")
            
            # Step 4: Send delivery email
            email_sent = False
            if self.email_service:
                email_sent = await self.email_service.send_delivery_email(
                    customer_email,
                    customer_name,
                    plan,
                    license_key,
                    download_url
                )
            
            if not email_sent:
                logger.warning(f"Email delivery failed for order: {order_id}, continuing anyway")
            
            # Step 5: Mark order as completed
            order.status = "completed"
            order.completed_at = datetime.utcnow()
            session.commit()
            
            AuditLogger.log_event(
                AuditLogger.EVENT_ORDER_COMPLETED,
                order_id,
                customer_email,
                {"email_sent": email_sent}
            )
            
            logger.info(f"Order {order_id} completed successfully")
            return True, order_id, license_key
            
        except Exception as e:
            logger.error(f"Fulfillment failed for order {order_id}: {str(e)}")
            
            # Rollback and mark as failed
            try:
                session.rollback()
                
                # Try to update order status to failed
                from payment_orchestration.models import Order
                order = session.query(Order).filter_by(order_id=order_id).first()
                if order:
                    order.status = "failed"
                    order.error_message = str(e)
                    session.commit()
                
                # Log the failure
                from payment_orchestration.audit_logger import AuditLogger
                AuditLogger.log_event(
                    AuditLogger.EVENT_ORDER_FAILED,
                    order_id,
                    customer_email,
                    {"error": str(e)},
                    status="failed"
                )
                
                # Send error notification email
                if self.email_service:
                    await self.email_service.send_error_notification(
                        customer_email,
                        customer_name,
                        order_id,
                        str(e)
                    )
                    
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {str(rollback_error)}")
            
            return False, order_id, str(e)
    
    def get_order_status(self, order_id):
        """Get the current status of an order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            dict: Order status information or None if not found
        """
        session = self._get_db_session()
        
        try:
            from payment_orchestration.models import Order
            
            order = session.query(Order).filter_by(order_id=order_id).first()
            
            if not order:
                return None
            
            return {
                "order_id": order.order_id,
                "customer_email": order.customer_email,
                "customer_name": order.customer_name,
                "plan": order.plan,
                "status": order.status,
                "amount_cents": order.amount_cents,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None,
                "error_message": order.error_message
            }
            
        except Exception as e:
            logger.error(f"Error retrieving order status: {str(e)}")
            return None
    
    def get_customer_orders(self, customer_email):
        """Get all orders for a customer.
        
        Args:
            customer_email: Customer's email address
            
        Returns:
            list: List of order dictionaries
        """
        session = self._get_db_session()
        
        try:
            from payment_orchestration.models import Order
            
            orders = session.query(Order).filter_by(customer_email=customer_email).all()
            
            return [{
                "order_id": o.order_id,
                "plan": o.plan,
                "status": o.status,
                "amount_cents": o.amount_cents,
                "created_at": o.created_at.isoformat() if o.created_at else None
            } for o in orders]
            
        except Exception as e:
            logger.error(f"Error retrieving customer orders: {str(e)}")
            return []