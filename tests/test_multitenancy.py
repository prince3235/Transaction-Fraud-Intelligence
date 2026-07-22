import pytest
from src.models import Organization, User
from src.auth import create_access_token, decode_access_token

def test_organization_model(db_session):
    """Verify Organization model creation and foreign key relationships."""
    org = Organization(name="FinTech Corp", slug="fintech-corp", created_at="2026-07-22T00:00:00Z")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    
    assert org.id is not None
    assert org.slug == "fintech-corp"

    user = User(
        organization_id=org.id,
        username="org_admin",
        password_hash="dummy_hash",
        role="Admin",
        created_at="2026-07-22T00:00:00Z"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.organization_id == org.id

def test_jwt_embeds_organization_id():
    """Verify JWT tokens correctly embed and decode organization_id."""
    payload = {"sub": "org_user", "id": 42, "role": "Compliance_Officer", "organization_id": 99}
    token = create_access_token(payload)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["organization_id"] == 99
