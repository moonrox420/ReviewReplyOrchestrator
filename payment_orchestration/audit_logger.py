import os
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class AuditLogger:
    """Audit logging service for tracking all payment and fulfillment events.
    Provides persistent logging for compliance and debugging purposes."""
    
    # Event type constants
    EVENT_PAYMENT_RECEIVED = "payment_received"
    EVENT_LICENSE_GENERATED = "license_generated"
    EVENT_ORDER_COMPLETED = "order_completed"
    EVENT_ORDER_FAILED = "order_failed"
    EVENT_EMAIL_SENT = "email_sent"
    EVENT_EMAIL_FAILED = "email_failed"
    EVENT_DOWNLOAD_LINK_GENERATED = "download_link_generated"
    EVENT_WEBHOOK_RECEIVED = "webhook_received"
    EVENT_CHECKOUT_CREATED = "checkout_created"
    
    @staticmethod
    def log_event(event_type, order_id, customer_email, details=None, status="success"):
        """Log an audit event.
        
        Args:
            event_type: Type of event (use EVENT_* constants)
            order_id: Order identifier
            customer_email: Customer's email address
            details: Additional event details (dict)
            status: Event status (success/failed)
        """
        timestamp = datetime.utcnow().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "event_type": event_type,
            "order_id": order_id,
            "customer_email": customer_email,
            "status": status,
            "details": details or {}
        }
        
        # Log to Python logger
        if status == "success":
            logger.info(f"[AUDIT] {event_type} - Order: {order_id}, Email: {customer_email}")
        else:
            logger.error(f"[AUDIT] {event_type} FAILED - Order: {order_id}, Error: {details}")
        
        # Persist to audit log file
        AuditLogger._persist_log(log_entry)
        
        return log_entry
    
    @staticmethod
    def _persist_log(log_entry):
        """Persist log entry to file.
        
        Args:
            log_entry: Log entry dictionary
        """
        try:
            log_file = os.getenv('AUDIT_LOG_FILE', 'audit.log')
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to persist audit log: {str(e)}")
    
    @staticmethod
    def get_recent_events(limit=100, event_type=None, order_id=None):
        """Retrieve recent audit events.
        
        Args:
            limit: Maximum number of events to return
            event_type: Filter by event type (optional)
            order_id: Filter by order ID (optional)
            
        Returns:
            list: List of log entry dictionaries
        """
        try:
            log_file = os.getenv('AUDIT_LOG_FILE', 'audit.log')
            
            if not os.path.exists(log_file):
                return []
            
            events = []
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            
                            # Apply filters
                            if event_type and entry.get('event_type') != event_type:
                                continue
                            if order_id and entry.get('order_id') != order_id:
                                continue
                            
                            events.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            # Return most recent events first
            return events[-limit:][::-1]
            
        except Exception as e:
            logger.error(f"Failed to retrieve audit events: {str(e)}")
            return []
    
    @staticmethod
    def get_order_history(order_id):
        """Get complete audit history for a specific order.
        
        Args:
            order_id: Order identifier
            
        Returns:
            list: List of events for this order, sorted by timestamp
        """
        events = AuditLogger.get_recent_events(limit=1000, order_id=order_id)
        
        # Sort by timestamp
        events.sort(key=lambda x: x.get('timestamp', ''))
        
        return events
    
    @staticmethod
    def get_event_stats():
        """Get statistics about logged events.
        
        Returns:
            dict: Event statistics
        """
        try:
            events = AuditLogger.get_recent_events(limit=10000)
            
            stats = {
                "total_events": len(events),
                "event_types": {},
                "success_count": 0,
                "failure_count": 0
            }
            
            for event in events:
                event_type = event.get('event_type', 'unknown')
                status = event.get('status', 'unknown')
                
                # Count by event type
                if event_type not in stats["event_types"]:
                    stats["event_types"][event_type] = 0
                stats["event_types"][event_type] += 1
                
                # Count by status
                if status == "success":
                    stats["success_count"] += 1
                elif status == "failed":
                    stats["failure_count"] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get event stats: {str(e)}")
            return {
                "total_events": 0,
                "event_types": {},
                "success_count": 0,
                "failure_count": 0
            }
    
    @staticmethod
    def clear_old_logs(days_to_keep=90):
        """Clear audit logs older than specified days.
        
        Args:
            days_to_keep: Number of days of logs to keep
            
        Returns:
            int: Number of entries removed
        """
        try:
            log_file = os.getenv('AUDIT_LOG_FILE', 'audit.log')
            
            if not os.path.exists(log_file):
                return 0
            
            cutoff_date = datetime.utcnow() - __import__('timedelta', fromlist=['timedelta']).timedelta(days=days_to_keep)
            cutoff_str = cutoff_date.isoformat()
            
            kept_events = []
            removed_count = 0
            
            with open(log_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            if entry.get('timestamp', '') >= cutoff_str:
                                kept_events.append(line)
                            else:
                                removed_count += 1
                        except json.JSONDecodeError:
                            continue
            
            # Rewrite file with kept events
            with open(log_file, 'w') as f:
                for event in kept_events:
                    f.write(event + '\n')
            
            logger.info(f"Cleared {removed_count} old audit log entries")
            return removed_count
            
        except Exception as e:
            logger.error(f"Failed to clear old logs: {str(e)}")
            return 0