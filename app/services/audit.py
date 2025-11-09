"""Audit logging service."""
import json
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models import AuditLog, User


def log_action(
    db: Session,
    action: str,
    user: Optional[User] = None,
    payload: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Log an auditable action.
    
    Args:
        db: Database session
        action: Action description
        user: User performing action (optional)
        payload: Additional data (will be JSON-serialized)
        
    Returns:
        Created audit log entry
    """
    payload_json = json.dumps(payload or {}, default=str)
    
    log_entry = AuditLog(
        user_id=user.id if user else None,
        action=action,
        payload_json=payload_json
    )
    
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    return log_entry


def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information from text.
    
    Args:
        text: Input text
        
    Returns:
        Text with PII redacted
    """
    # Simple email redaction
    import re
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REDACTED]', text)
    
    # Redact potential phone numbers (Bangladesh format)
    text = re.sub(r'\b(\+?880|0)?1[3-9]\d{8}\b', '[PHONE_REDACTED]', text)
    
    return text