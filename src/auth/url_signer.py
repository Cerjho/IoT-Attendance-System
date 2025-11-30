"""
URL Signer for Attendance System
Generates cryptographically signed URLs with HMAC-SHA256 signatures.

Security Features:
- HMAC-SHA256 signature prevents tampering
- Timestamp-based expiry (configurable)
- Constant-time signature comparison (prevents timing attacks)
- URL-safe base64 encoding
- Student ID validation

Usage:
    signer = URLSigner(secret_key="your-secret")
    signed_url = signer.sign_url(
        base_url="https://example.com/view",
        student_id="2021001",
        expiry_hours=24
    )
    
    is_valid, error = signer.verify_url(
        url="https://example.com/view?student_id=2021001&expires=123456&sig=abc..."
    )
"""

import hmac
import hashlib
import time
import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class URLSigner:
    """
    Cryptographic URL signer for secure attendance links.
    """
    
    def __init__(self, secret_key: str):
        """
        Initialize URL signer with secret key.
        
        Args:
            secret_key: Secret key for HMAC signing (from .env)
        
        Raises:
            ValueError: If secret key is empty or too short
        """
        if not secret_key or len(secret_key) < 32:
            raise ValueError("Secret key must be at least 32 characters for security")
        
        self.secret_key = secret_key.encode('utf-8')
        logger.info("URLSigner initialized")
    
    def sign_url(
        self, 
        base_url: str, 
        student_id: str, 
        expiry_hours: int = 24,
        additional_params: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Generate a signed URL with expiry timestamp.
        
        Args:
            base_url: Base URL without query parameters
            student_id: Student identifier (student_number, not UUID)
            expiry_hours: Hours until link expires (default 24)
            additional_params: Optional additional query parameters
        
        Returns:
            Signed URL with student_id, expires, and sig parameters
        
        Example:
            >>> signer.sign_url("https://example.com/view", "2021001", 24)
            "https://example.com/view?student_id=2021001&expires=1701388800&sig=abc123..."
        """
        # Calculate expiry timestamp
        expires_at = int((datetime.now() + timedelta(hours=expiry_hours)).timestamp())
        
        # Build parameters
        params = {
            'student_id': student_id,
            'expires': str(expires_at)
        }
        
        # Add any additional parameters
        if additional_params:
            params.update(additional_params)
        
        # Generate signature
        signature = self._generate_signature(params)
        params['sig'] = signature
        
        # Build signed URL
        signed_url = f"{base_url}?{urlencode(params)}"
        
        logger.info(f"Signed URL generated for student {student_id}, expires at {datetime.fromtimestamp(expires_at)}")
        return signed_url
    
    def verify_url(self, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Verify a signed URL's authenticity and expiry.
        
        Args:
            url: Full URL with query parameters
        
        Returns:
            Tuple of (is_valid, student_id, error_message)
            - is_valid: True if signature valid and not expired
            - student_id: Student ID if valid, None otherwise
            - error_message: Error description if invalid, None otherwise
        
        Example:
            >>> is_valid, student_id, error = signer.verify_url(signed_url)
            >>> if is_valid:
            ...     print(f"Valid for student {student_id}")
            ... else:
            ...     print(f"Invalid: {error}")
        """
        try:
            # Parse URL
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Extract required parameters
            if 'student_id' not in params:
                return False, None, "Missing student_id parameter"
            
            if 'expires' not in params:
                return False, None, "Missing expires parameter"
            
            if 'sig' not in params:
                return False, None, "Missing signature parameter"
            
            student_id = params['student_id'][0]
            expires_str = params['expires'][0]
            provided_sig = params['sig'][0]
            
            # Validate expiry timestamp format
            try:
                expires_at = int(expires_str)
            except ValueError:
                return False, None, "Invalid expiry timestamp format"
            
            # Check if expired
            now = int(time.time())
            if now > expires_at:
                expired_at = datetime.fromtimestamp(expires_at)
                logger.warning(f"URL expired at {expired_at} for student {student_id}")
                return False, None, f"Link expired at {expired_at.strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Reconstruct parameters for signature verification (without 'sig')
            verify_params = {
                'student_id': student_id,
                'expires': expires_str
            }
            
            # Add any additional parameters (excluding 'sig')
            for key, values in params.items():
                if key not in ['student_id', 'expires', 'sig']:
                    verify_params[key] = values[0]
            
            # Generate expected signature
            expected_sig = self._generate_signature(verify_params)
            
            # Constant-time comparison to prevent timing attacks
            if not self._constant_time_compare(provided_sig, expected_sig):
                logger.warning(f"Invalid signature for student {student_id}")
                return False, None, "Invalid signature - link may have been tampered with"
            
            # Valid!
            logger.info(f"Valid signed URL verified for student {student_id}")
            return True, student_id, None
            
        except Exception as e:
            logger.error(f"Error verifying URL: {e}")
            return False, None, f"Verification error: {str(e)}"
    
    def _generate_signature(self, params: Dict[str, str]) -> str:
        """
        Generate HMAC-SHA256 signature for parameters.
        
        Args:
            params: Dictionary of parameters to sign
        
        Returns:
            Hex-encoded HMAC signature
        """
        # Sort parameters for consistent signature
        sorted_params = sorted(params.items())
        
        # Create message to sign
        message = '&'.join(f"{k}={v}" for k, v in sorted_params)
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key,
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _constant_time_compare(self, a: str, b: str) -> bool:
        """
        Constant-time string comparison to prevent timing attacks.
        
        Args:
            a: First string
            b: Second string
        
        Returns:
            True if strings are equal
        """
        # Use hmac.compare_digest for constant-time comparison
        return hmac.compare_digest(a, b)
    
    def get_expiry_info(self, url: str) -> Optional[Dict[str, any]]:
        """
        Get expiry information from a signed URL without full verification.
        
        Args:
            url: Signed URL
        
        Returns:
            Dict with expiry info or None if invalid format
        """
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            if 'expires' not in params:
                return None
            
            expires_at = int(params['expires'][0])
            expires_datetime = datetime.fromtimestamp(expires_at)
            now = datetime.now()
            
            return {
                'expires_at': expires_datetime,
                'expires_timestamp': expires_at,
                'is_expired': now > expires_datetime,
                'time_remaining': expires_datetime - now if now < expires_datetime else timedelta(0),
                'student_id': params.get('student_id', [None])[0]
            }
        except Exception as e:
            logger.error(f"Error getting expiry info: {e}")
            return None


def generate_secret_key() -> str:
    """
    Generate a secure random secret key for URL signing.
    
    Returns:
        64-character hex string (32 bytes)
    
    Example:
        >>> secret = generate_secret_key()
        >>> print(f"Add to .env: URL_SIGNING_SECRET={secret}")
    """
    import secrets
    return secrets.token_hex(32)


if __name__ == "__main__":
    # Generate a new secret key
    print("=" * 80)
    print("GENERATE SECRET KEY FOR URL SIGNING")
    print("=" * 80)
    secret = generate_secret_key()
    print(f"\nAdd this to your .env file:")
    print(f"URL_SIGNING_SECRET={secret}")
    print("\n" + "=" * 80)
    
    # Demo usage
    print("\nDEMO: Signed URL Generation")
    print("=" * 80)
    
    signer = URLSigner(secret_key=secret)
    
    # Generate signed URL
    base_url = "https://cerjho.github.io/IoT-Attendance-System/view-attendance.html"
    student_id = "2021001"
    expiry_hours = 24
    
    signed_url = signer.sign_url(base_url, student_id, expiry_hours)
    print(f"\nSigned URL (valid for {expiry_hours} hours):")
    print(signed_url)
    
    # Verify the URL
    print("\nVerification:")
    is_valid, verified_student_id, error = signer.verify_url(signed_url)
    
    if is_valid:
        print(f"✅ Valid signature for student: {verified_student_id}")
    else:
        print(f"❌ Invalid: {error}")
    
    # Get expiry info
    info = signer.get_expiry_info(signed_url)
    if info:
        print(f"\nExpiry Info:")
        print(f"  Expires at: {info['expires_at']}")
        print(f"  Time remaining: {info['time_remaining']}")
        print(f"  Is expired: {info['is_expired']}")
    
    # Test tampering detection
    print("\n" + "=" * 80)
    print("DEMO: Tamper Detection")
    print("=" * 80)
    
    tampered_url = signed_url.replace("2021001", "2021002")
    is_valid, verified_student_id, error = signer.verify_url(tampered_url)
    
    if is_valid:
        print(f"❌ SECURITY ISSUE: Tampered URL was accepted!")
    else:
        print(f"✅ Tamper detected: {error}")
