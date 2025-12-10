#!/usr/bin/env python3
"""
SMS Delivery Webhook Receiver
Receives delivery status updates from Android SMS Gateway
"""
import json
import logging
import sqlite3
import threading
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify

logger = logging.getLogger(__name__)


class SMSWebhookReceiver:
    """
    Webhook receiver for SMS delivery status updates
    Runs Flask server in background thread
    """

    def __init__(
        self,
        db_path: str = "data/attendance.db",
        port: int = 8081,
        enabled: bool = True,
        auth_token: Optional[str] = None
    ):
        """
        Initialize SMS webhook receiver
        
        Args:
            db_path: Path to database for logging delivery status
            port: Port to run webhook server on
            enabled: Enable/disable webhook receiver
            auth_token: Optional auth token for webhook security
        """
        self.db_path = db_path
        self.port = port
        self.enabled = enabled
        self.auth_token = auth_token
        
        self.app = Flask(__name__)
        self.server_thread = None
        self.running = False
        
        # Setup routes
        self._setup_routes()
        
        # Initialize database
        self._init_database()
        
        if self.enabled:
            logger.info(f"SMS webhook receiver initialized on port {port}")
        else:
            logger.info("SMS webhook receiver disabled")

    def _init_database(self):
        """Create delivery log table if not exists"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sms_delivery_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id TEXT UNIQUE,
                    phone_number TEXT,
                    status TEXT,
                    student_id TEXT,
                    error_message TEXT,
                    timestamp TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for quick lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_message_id 
                ON sms_delivery_log(message_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status 
                ON sms_delivery_log(status)
            """)
            
            conn.commit()
            conn.close()
            logger.debug("SMS delivery log table initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize delivery log table: {e}")

    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/sms-webhook', methods=['POST'])
        def sms_status_webhook():
            """
            Receive SMS delivery status from Android SMS Gateway
            
            Expected payload:
            {
                "id": "msg_123",
                "state": "Delivered",  # or "Sent", "Failed", "Pending"
                "phoneNumber": "+639755269146",
                "message": "Good day! Student...",
                "deviceId": "zmmfTkL3...",
                "updatedAt": "2025-12-10T14:30:00Z",
                "error": "optional error message"
            }
            """
            try:
                # Check auth token if configured
                if self.auth_token:
                    auth_header = request.headers.get('Authorization', '')
                    if auth_header != f"Bearer {self.auth_token}":
                        logger.warning(f"Unauthorized webhook attempt from {request.remote_addr}")
                        return jsonify({"error": "Unauthorized"}), 401
                
                data = request.json
                if not data:
                    return jsonify({"error": "No data provided"}), 400
                
                message_id = data.get('id')
                status = data.get('state', 'unknown')
                phone = data.get('phoneNumber')
                timestamp = data.get('updatedAt', datetime.now().isoformat())
                error_msg = data.get('error')
                
                logger.info(
                    f"📨 SMS Status Update: id={message_id}, "
                    f"status={status}, phone={phone}"
                )
                
                # Save to database
                self._save_delivery_status(
                    message_id, phone, status, timestamp, error_msg
                )
                
                # Handle failures
                if status in ["Failed", "Rejected", "Error"]:
                    logger.warning(
                        f"❌ SMS delivery failed: id={message_id}, "
                        f"phone={phone}, error={error_msg}"
                    )
                    # Could trigger retry logic here
                    self._handle_failed_sms(message_id, phone, error_msg)
                
                elif status in ["Delivered", "Sent"]:
                    logger.info(f"✅ SMS delivered successfully: id={message_id}")
                
                return jsonify({"success": True, "message": "Status received"}), 200
                
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/sms-webhook/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "service": "sms-webhook",
                "port": self.port
            }), 200

    def _save_delivery_status(
        self,
        message_id: str,
        phone: str,
        status: str,
        timestamp: str,
        error_msg: Optional[str] = None
    ):
        """Save delivery status to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Try to extract student_id from recent attendance records
            student_id = None
            try:
                cursor.execute("""
                    SELECT student_id FROM attendance 
                    WHERE photo_path LIKE ? 
                    ORDER BY created_at DESC LIMIT 1
                """, (f"%{phone[-10:]}%",))  # Match last 10 digits
                result = cursor.fetchone()
                if result:
                    student_id = result[0]
            except Exception:
                pass
            
            # Insert or update
            cursor.execute("""
                INSERT INTO sms_delivery_log 
                (message_id, phone_number, status, student_id, error_message, timestamp, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(message_id) DO UPDATE SET
                    status = excluded.status,
                    error_message = excluded.error_message,
                    timestamp = excluded.timestamp,
                    updated_at = CURRENT_TIMESTAMP
            """, (message_id, phone, status, student_id, error_msg, timestamp))
            
            conn.commit()
            conn.close()
            logger.debug(f"Saved delivery status: {message_id} -> {status}")
            
        except Exception as e:
            logger.error(f"Failed to save delivery status: {e}")

    def _handle_failed_sms(self, message_id: str, phone: str, error_msg: str):
        """Handle failed SMS delivery"""
        # Could implement retry logic here
        # For now, just log the failure
        logger.warning(f"SMS failed for {phone}: {error_msg}")
        
        # Could add to retry queue if needed
        pass

    def start(self):
        """Start webhook server in background thread"""
        if not self.enabled:
            logger.debug("SMS webhook receiver disabled, not starting")
            return
        
        def run_server():
            try:
                logger.info(f"Starting SMS webhook server on port {self.port}")
                self.app.run(
                    host='0.0.0.0',
                    port=self.port,
                    debug=False,
                    use_reloader=False
                )
            except Exception as e:
                logger.error(f"SMS webhook server error: {e}")
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.running = True
        logger.info(f"SMS webhook receiver started on port {self.port}")
    
    def stop(self):
        """Stop webhook server"""
        if not self.running:
            return
        
        self.running = False
        # Note: Flask server running in daemon thread will stop when main program exits
        logger.info("SMS webhook receiver stopped")

    def get_delivery_stats(self) -> dict:
        """Get delivery statistics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total by status
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM sms_delivery_log
                GROUP BY status
            """)
            status_counts = dict(cursor.fetchall())
            
            # Recent failures (last 24 hours)
            cursor.execute("""
                SELECT COUNT(*) 
                FROM sms_delivery_log
                WHERE status IN ('Failed', 'Rejected', 'Error')
                AND datetime(created_at) > datetime('now', '-24 hours')
            """)
            recent_failures = cursor.fetchone()[0]
            
            # Delivery rate
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN status IN ('Delivered', 'Sent') THEN 1 ELSE 0 END) as delivered,
                    COUNT(*) as total
                FROM sms_delivery_log
            """)
            delivered, total = cursor.fetchone()
            delivery_rate = (delivered / total * 100) if total > 0 else 0
            
            conn.close()
            
            return {
                "status_counts": status_counts,
                "recent_failures_24h": recent_failures,
                "delivery_rate_percent": round(delivery_rate, 1),
                "total_tracked": total
            }
            
        except Exception as e:
            logger.error(f"Failed to get delivery stats: {e}")
            return {}
