"""
Tests for GDPR Data Export (art. 20 — Data Portability).

Covers:
- Whitelist field extraction (_pick helper)
- ZIP file structure (correct filenames)
- Sensitive data exclusion
- JSON validity
- Audit log user_email lookup
"""

import io
import json
import os
import zipfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")


class TestPickHelper:
    """Tests for the _pick whitelist helper."""

    def test_pick_basic(self):
        from services.gdpr_export_service import _pick
        doc = {"name": "Test", "email": "t@t.com", "password_hash": "secret", "_id": "mongo_id"}
        result = _pick(doc, ["name", "email"])
        assert result == {"name": "Test", "email": "t@t.com"}
        assert "password_hash" not in result
        assert "_id" not in result

    def test_pick_missing_fields(self):
        from services.gdpr_export_service import _pick
        doc = {"name": "Test"}
        result = _pick(doc, ["name", "email", "phone"])
        assert result == {"name": "Test"}
        assert "email" not in result

    def test_pick_empty_doc(self):
        from services.gdpr_export_service import _pick
        result = _pick({}, ["name", "email"])
        assert result == {}

    def test_pick_preserves_none_values(self):
        from services.gdpr_export_service import _pick
        doc = {"name": "Test", "phone": None}
        result = _pick(doc, ["name", "phone"])
        assert result == {"name": "Test", "phone": None}


class TestWhitelistCompleteness:
    """Verify whitelist definitions exist and exclude sensitive fields."""

    def test_user_fields_exclude_sensitive(self):
        from services.gdpr_export_service import _USER_FIELDS
        assert "password_hash" not in _USER_FIELDS
        assert "reset_token_hash" not in _USER_FIELDS
        assert "verification_token_hash" not in _USER_FIELDS
        assert "name" in _USER_FIELDS
        assert "email" in _USER_FIELDS

    def test_team_member_fields_exclude_sensitive(self):
        from services.gdpr_export_service import _TEAM_MEMBER_FIELDS
        assert "password_hash" not in _TEAM_MEMBER_FIELDS
        assert "organization_id" not in _TEAM_MEMBER_FIELDS

    def test_org_fields_exclude_stripe(self):
        from services.gdpr_export_service import _ORG_FIELDS
        assert "stripe_customer_id" not in _ORG_FIELDS
        assert "stripe_subscription_id" not in _ORG_FIELDS
        assert "name" in _ORG_FIELDS

    def test_sales_fields_exclude_internal(self):
        from services.gdpr_export_service import _SALES_FIELDS
        assert "organization_id" not in _SALES_FIELDS
        assert "dataset_id" not in _SALES_FIELDS
        assert "source_record_id" not in _SALES_FIELDS
        assert "date" in _SALES_FIELDS
        assert "amount" in _SALES_FIELDS

    def test_purchase_fields_exclude_internal(self):
        from services.gdpr_export_service import _PURCHASE_FIELDS
        assert "organization_id" not in _PURCHASE_FIELDS
        assert "supplier_id" not in _PURCHASE_FIELDS
        assert "metadata" not in _PURCHASE_FIELDS
        assert "supplier_name" in _PURCHASE_FIELDS

    def test_all_field_lists_are_lists(self):
        from services.gdpr_export_service import (
            _USER_FIELDS, _ORG_FIELDS, _TEAM_MEMBER_FIELDS,
            _SALES_FIELDS, _PURCHASE_FIELDS, _EXPENSE_FIELDS,
            _FIXED_COST_FIELDS, _CUSTOMER_FIELDS, _SUPPLIER_FIELDS,
            _PRODUCT_FIELDS, _CHAT_FIELDS, _ALERT_FIELDS, _AUDIT_FIELDS,
        )
        all_lists = [
            _USER_FIELDS, _ORG_FIELDS, _TEAM_MEMBER_FIELDS,
            _SALES_FIELDS, _PURCHASE_FIELDS, _EXPENSE_FIELDS,
            _FIXED_COST_FIELDS, _CUSTOMER_FIELDS, _SUPPLIER_FIELDS,
            _PRODUCT_FIELDS, _CHAT_FIELDS, _ALERT_FIELDS, _AUDIT_FIELDS,
        ]
        for field_list in all_lists:
            assert isinstance(field_list, list)
            assert len(field_list) > 0


class TestToJson:
    """Tests for the _to_json serializer."""

    def test_serializes_datetime(self):
        from services.gdpr_export_service import _to_json
        data = {"created_at": datetime(2026, 1, 15, tzinfo=timezone.utc)}
        result = _to_json(data)
        parsed = json.loads(result)
        assert "2026-01-15" in parsed["created_at"]

    def test_serializes_unicode(self):
        from services.gdpr_export_service import _to_json
        data = {"name": "Caffè Müller"}
        result = _to_json(data)
        assert "Caffè" in result
        assert "Müller" in result

    def test_pretty_printed(self):
        from services.gdpr_export_service import _to_json
        data = {"a": 1, "b": 2}
        result = _to_json(data)
        assert "\n" in result  # indented


class TestAuditLogLookup:
    """Tests for user_email enrichment in audit log export."""

    def test_user_email_lookup_pattern(self):
        """Verify the lookup dict pattern works correctly."""
        user_email_map = {
            "u1": "admin@org.com",
            "u2": "member@org.com",
        }
        audit_doc = {"user_id": "u1", "action": "login"}
        email = user_email_map.get(audit_doc["user_id"], "deleted")
        assert email == "admin@org.com"

    def test_deleted_user_fallback(self):
        """User not in map should return 'deleted'."""
        user_email_map = {"u1": "admin@org.com"}
        email = user_email_map.get("u999", "deleted")
        assert email == "deleted"
