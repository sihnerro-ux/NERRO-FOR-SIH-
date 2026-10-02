from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.auth.security import hash_password, verify_password
from app.db.database import SessionLocal
from app.db.tables import UserRow
from app.domain.models import AuthUser, UserRole


DEMO_USERS = [
    {"id": "USR-ADMIN-001", "username": "admin@ner.gov.in", "display_name": "Arun Kumar", "password": "NerDemo@2026", "role": UserRole.CONTROL_ROOM_ADMIN, "district": None},
    {"id": "USR-FIELD-001", "username": "field@ner.gov.in", "display_name": "Field Officer", "password": "FieldDemo@2026", "role": UserRole.FIELD_OFFICER, "district": "West Kameng"},
    {"id": "USR-LOGISTICS-001", "username": "logistics@ner.gov.in", "display_name": "Logistics Operator", "password": "LogisticsDemo@2026", "role": UserRole.LOGISTICS_OPERATOR, "district": None},
    {"id": "USR-DISTRICT-001", "username": "district@ner.gov.in", "display_name": "District Authority", "password": "DistrictDemo@2026", "role": UserRole.DISTRICT_AUTHORITY, "district": "East Khasi Hills"},
    {"id": "USR-VIEWER-001", "username": "viewer@ner.gov.in", "display_name": "Operations Viewer", "password": "ViewerDemo@2026", "role": UserRole.VIEWER, "district": None},
    {"id": "USR-DRIVER-001", "username": "driver@ner.gov.in", "display_name": "Demo Driver", "password": "DriverDemo@2026", "role": UserRole.DRIVER, "district": None},
]


class AuthService:
    def seed_demo_users(self) -> None:
        with SessionLocal.begin() as session:
            for user in DEMO_USERS:
                if session.get(UserRow, user["id"]):
                    continue
                session.add(UserRow(
                    id=user["id"], username=user["username"], display_name=user["display_name"],
                    password_hash=hash_password(user["password"]), role=user["role"].value,
                    district=user["district"], active=True, created_at=datetime.now(UTC),
                ))

    @staticmethod
    def _summary(row: UserRow) -> AuthUser:
        return AuthUser(id=row.id, username=row.username, display_name=row.display_name, role=UserRole(row.role), district=row.district)

    def authenticate(self, username: str, password: str) -> AuthUser | None:
        with SessionLocal() as session:
            row = session.scalar(select(UserRow).where(UserRow.username == username.lower(), UserRow.active.is_(True)))
            if row is None or not verify_password(password, row.password_hash):
                return None
            return self._summary(row)

    def get_user(self, user_id: str) -> AuthUser | None:
        with SessionLocal() as session:
            row = session.get(UserRow, user_id)
            return self._summary(row) if row and row.active else None

    def list_users(self) -> list[dict]:
        with SessionLocal() as session:
            rows = session.scalars(select(UserRow).order_by(UserRow.role, UserRow.display_name)).all()
            return [{
                "id": row.id, "username": row.username, "display_name": row.display_name,
                "role": row.role, "district": row.district, "active": row.active,
                "created_at": row.created_at,
            } for row in rows]


auth_service = AuthService()
