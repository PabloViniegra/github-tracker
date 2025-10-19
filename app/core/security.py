"""Security utilities for authentication and authorization."""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta, timezone
from typing import Tuple

from fastapi import HTTPException, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings
from app.models.token import TokenPayload

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()


def create_access_token(user_id: str) -> Tuple[str, datetime]:
    """
    Create a JWT access token for user authentication.

    Args:
        user_id: The MongoDB ObjectId of the user as a string

    Returns:
        tuple: (encoded_jwt_token, expiration_datetime)
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )

    to_encode = {"sub": user_id, "exp": expire, "type": "access"}

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    return encoded_jwt, expire


def create_refresh_token(user_id: str) -> Tuple[str, datetime]:
    """
    Create a JWT refresh token for obtaining new access tokens.

    Args:
        user_id: The MongoDB ObjectId of the user as a string

    Returns:
        tuple: (encoded_jwt_token, expiration_datetime)
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_token_expire_days
    )

    to_encode = {"sub": user_id, "exp": expire, "type": "refresh"}

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    return encoded_jwt, expire


def verify_token(token: str, token_type: str = "access") -> TokenPayload:
    """
    Verify and decode a JWT token.

    Args:
        token: The JWT token to verify
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        TokenPayload: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    settings = get_settings()

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        token_data = TokenPayload(**payload)

        if token_data.type != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
            )

        return token_data

    except JWTError as e:
        logger.warning(f"Token verification failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        payload_body: The raw webhook payload
        signature_header: The X-Hub-Signature-256 header value

    Returns:
        bool: True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing webhook signature header")
        return False

    try:
        parts = signature_header.split("=", 1)
        if len(parts) != 2:
            logger.warning("Invalid signature header format")
            return False

        hash_algorithm, github_signature = parts

        if hash_algorithm != "sha256":
            logger.warning(f"Unsupported hash algorithm: {hash_algorithm}")
            return False

        settings = get_settings()
        mac = hmac.new(
            settings.github_webhook_secret.encode(),
            msg=payload_body,
            digestmod=hashlib.sha256,
        )

        is_valid = hmac.compare_digest(mac.hexdigest(), github_signature)

        if not is_valid:
            logger.warning("Webhook signature verification failed")

        return is_valid

    except Exception as e:
        logger.error(f"Error verifying webhook signature: {str(e)}")
        return False
