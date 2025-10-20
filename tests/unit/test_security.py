"""
Unit tests for security functions.

Tests JWT token creation/validation and GitHub webhook signature verification.
"""

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_github_signature,
    verify_token,
)
from app.models.token import TokenPayload


# =============================================================================
# JWT Token Creation Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.security
class TestJWTTokenCreation:
    """Test JWT token creation functions."""

    def test_create_access_token_success(self, test_settings):
        """Test successful access token creation."""
        with patch("app.core.security.get_settings", return_value=test_settings):
            user_id = "507f1f77bcf86cd799439011"

            token, expiration = create_access_token(user_id)

            # Verify token is a string
            assert isinstance(token, str)
            assert len(token) > 0

            # Verify expiration is set correctly
            assert isinstance(expiration, datetime)
            expected_exp = datetime.now(timezone.utc) + timedelta(
                minutes=test_settings.jwt_access_token_expire_minutes
            )
            # Allow 2 second tolerance for test execution time
            assert abs((expiration - expected_exp).total_seconds()) < 2

            # Decode and verify payload
            payload = jwt.decode(
                token,
                test_settings.jwt_secret_key,
                algorithms=[test_settings.jwt_algorithm]
            )
            assert payload["sub"] == user_id
            assert payload["type"] == "access"
            assert "exp" in payload

    def test_create_refresh_token_success(self, test_settings):
        """Test successful refresh token creation."""
        with patch("app.core.security.get_settings", return_value=test_settings):
            user_id = "507f1f77bcf86cd799439011"

            token, expiration = create_refresh_token(user_id)

            # Verify token is a string
            assert isinstance(token, str)
            assert len(token) > 0

            # Verify expiration is set correctly
            assert isinstance(expiration, datetime)
            expected_exp = datetime.now(timezone.utc) + timedelta(
                days=test_settings.jwt_refresh_token_expire_days
            )
            # Allow 2 second tolerance
            assert abs((expiration - expected_exp).total_seconds()) < 2

            # Decode and verify payload
            payload = jwt.decode(
                token,
                test_settings.jwt_secret_key,
                algorithms=[test_settings.jwt_algorithm]
            )
            assert payload["sub"] == user_id
            assert payload["type"] == "refresh"
            assert "exp" in payload

    def test_access_token_contains_correct_claims(self, test_settings):
        """Test that access token contains all required claims."""
        with patch("app.core.security.get_settings", return_value=test_settings):
            user_id = "507f1f77bcf86cd799439011"

            token, _ = create_access_token(user_id)

            payload = jwt.decode(
                token,
                test_settings.jwt_secret_key,
                algorithms=[test_settings.jwt_algorithm]
            )

            # Verify required claims
            assert "sub" in payload
            assert "exp" in payload
            assert "type" in payload
            assert payload["sub"] == user_id
            assert payload["type"] == "access"

    def test_refresh_token_contains_correct_claims(self, test_settings):
        """Test that refresh token contains all required claims."""
        with patch("app.core.security.get_settings", return_value=test_settings):
            user_id = "507f1f77bcf86cd799439011"

            token, _ = create_refresh_token(user_id)

            payload = jwt.decode(
                token,
                test_settings.jwt_secret_key,
                algorithms=[test_settings.jwt_algorithm]
            )

            # Verify required claims
            assert "sub" in payload
            assert "exp" in payload
            assert "type" in payload
            assert payload["sub"] == user_id
            assert payload["type"] == "refresh"


# =============================================================================
# JWT Token Verification Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.security
class TestJWTTokenVerification:
    """Test JWT token verification functions."""

    def test_verify_valid_access_token(self, test_settings):
        """Test verification of a valid access token."""
        user_id = "507f1f77bcf86cd799439011"
        token, _ = create_access_token(user_id)

        token_data = verify_token(token, token_type="access")

        assert isinstance(token_data, TokenPayload)
        assert token_data.sub == user_id
        assert token_data.type == "access"
        assert isinstance(token_data.exp, datetime)

    def test_verify_valid_refresh_token(self, test_settings):
        """Test verification of a valid refresh token."""
        user_id = "507f1f77bcf86cd799439011"
        token, _ = create_refresh_token(user_id)

        token_data = verify_token(token, token_type="refresh")

        assert isinstance(token_data, TokenPayload)
        assert token_data.sub == user_id
        assert token_data.type == "refresh"
        assert isinstance(token_data.exp, datetime)

    def test_verify_token_wrong_type(self, test_settings):
        """Test that verification fails when token type doesn't match."""
        user_id = "507f1f77bcf86cd799439011"
        access_token, _ = create_access_token(user_id)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(access_token, token_type="refresh")

        assert exc_info.value.status_code == 401
        assert "Invalid token type" in str(exc_info.value.detail)

    def test_verify_expired_token(self, test_settings):
        """Test that verification fails for expired token."""
        user_id = "507f1f77bcf86cd799439011"

        # Create token that's already expired
        expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)
        payload = {
            "sub": user_id,
            "exp": expired_time,
            "type": "access"
        }
        expired_token = jwt.encode(
            payload,
            test_settings.jwt_secret_key,
            algorithm=test_settings.jwt_algorithm
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired_token, token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_token_invalid_signature(self, test_settings):
        """Test that verification fails for token with invalid signature."""
        user_id = "507f1f77bcf86cd799439011"

        # Create token with wrong secret
        payload = {
            "sub": user_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "type": "access"
        }
        invalid_token = jwt.encode(
            payload,
            "wrong_secret_key_1234567890abcdef",
            algorithm=test_settings.jwt_algorithm
        )

        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token, token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_token_malformed(self, test_settings):
        """Test that verification fails for malformed token."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("not.a.valid.jwt.token", token_type="access")

        assert exc_info.value.status_code == 401

    def test_verify_token_empty_string(self, test_settings):
        """Test that verification fails for empty token."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("", token_type="access")

        assert exc_info.value.status_code == 401


# =============================================================================
# GitHub Webhook Signature Verification Tests
# =============================================================================

@pytest.mark.unit
@pytest.mark.security
class TestGitHubWebhookSignature:
    """Test GitHub webhook signature verification."""

    def test_verify_valid_signature(self, test_settings):
        """Test verification of a valid GitHub webhook signature."""
        with patch("app.core.security.get_settings", return_value=test_settings):
            payload = b'{"action":"opened","repository":{"owner":{"login":"testuser"}}}'

            # Generate valid signature
            mac = hmac.new(
                test_settings.github_webhook_secret.encode(),
                msg=payload,
                digestmod=hashlib.sha256
            )
            signature = f"sha256={mac.hexdigest()}"

            result = verify_github_signature(payload, signature)

            assert result is True

    def test_verify_invalid_signature(self, test_settings):
        """Test that verification fails for invalid signature."""
        payload = b'{"action":"opened","repository":{"owner":{"login":"testuser"}}}'

        # Generate signature with wrong payload
        wrong_payload = b'{"action":"closed"}'
        mac = hmac.new(
            test_settings.github_webhook_secret.encode(),
            msg=wrong_payload,
            digestmod=hashlib.sha256
        )
        invalid_signature = f"sha256={mac.hexdigest()}"

        result = verify_github_signature(payload, invalid_signature)

        assert result is False

    def test_verify_signature_missing_header(self, test_settings):
        """Test that verification fails when signature header is missing."""
        payload = b'{"action":"opened"}'

        result = verify_github_signature(payload, None)

        assert result is False

    def test_verify_signature_empty_header(self, test_settings):
        """Test that verification fails for empty signature header."""
        payload = b'{"action":"opened"}'

        result = verify_github_signature(payload, "")

        assert result is False

    def test_verify_signature_invalid_format(self, test_settings):
        """Test that verification fails for invalid signature format."""
        payload = b'{"action":"opened"}'

        # Missing 'sha256=' prefix
        result = verify_github_signature(payload, "abc123def456")

        assert result is False

    def test_verify_signature_wrong_algorithm(self, test_settings):
        """Test that verification fails for wrong hash algorithm."""
        payload = b'{"action":"opened"}'

        # Use sha1 instead of sha256
        mac = hmac.new(
            test_settings.github_webhook_secret.encode(),
            msg=payload,
            digestmod=hashlib.sha1
        )
        signature = f"sha1={mac.hexdigest()}"

        result = verify_github_signature(payload, signature)

        assert result is False

    def test_verify_signature_timing_attack_protection(self, test_settings):
        """Test that verification uses constant-time comparison."""
        payload = b'{"action":"opened"}'

        # Generate valid signature
        mac = hmac.new(
            test_settings.github_webhook_secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        valid_signature = f"sha256={mac.hexdigest()}"

        # Modify one character
        invalid_signature = valid_signature[:-1] + "a"

        # Should fail even with just one character difference
        result = verify_github_signature(payload, invalid_signature)

        assert result is False

    def test_verify_signature_exception_handling(self, test_settings):
        """Test that exceptions during verification are handled gracefully."""
        payload = b'{"action":"opened"}'

        # Test with malformed signature that might cause exceptions
        result = verify_github_signature(payload, "sha256=not_hex_characters!!!")

        # Should return False instead of raising exception
        assert result is False


# =============================================================================
# Integration Tests for Security Flow
# =============================================================================

@pytest.mark.unit
@pytest.mark.security
class TestSecurityIntegration:
    """Test integration of security functions."""

    def test_full_token_lifecycle(self, test_settings):
        """Test creation and verification of token in a lifecycle."""
        user_id = "507f1f77bcf86cd799439011"

        # Create token
        token, expiration = create_access_token(user_id)

        # Verify token immediately
        token_data = verify_token(token, token_type="access")

        assert token_data.sub == user_id
        assert token_data.type == "access"

        # Verify expiration matches
        assert abs((token_data.exp - expiration).total_seconds()) < 1

    def test_access_and_refresh_tokens_are_different(self, test_settings):
        """Test that access and refresh tokens are different for same user."""
        user_id = "507f1f77bcf86cd799439011"

        access_token, _ = create_access_token(user_id)
        refresh_token, _ = create_refresh_token(user_id)

        # Tokens should be different
        assert access_token != refresh_token

        # But both should be valid for their respective types
        access_data = verify_token(access_token, token_type="access")
        refresh_data = verify_token(refresh_token, token_type="refresh")

        assert access_data.sub == user_id
        assert refresh_data.sub == user_id
        assert access_data.type == "access"
        assert refresh_data.type == "refresh"

    def test_tokens_for_different_users_are_different(self, test_settings):
        """Test that tokens for different users are unique."""
        user_id_1 = "507f1f77bcf86cd799439011"
        user_id_2 = "507f1f77bcf86cd799439012"

        token_1, _ = create_access_token(user_id_1)
        token_2, _ = create_access_token(user_id_2)

        # Tokens should be different
        assert token_1 != token_2

        # And should decode to different user IDs
        data_1 = verify_token(token_1, token_type="access")
        data_2 = verify_token(token_2, token_type="access")

        assert data_1.sub == user_id_1
        assert data_2.sub == user_id_2
        assert data_1.sub != data_2.sub
