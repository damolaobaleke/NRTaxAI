"""
Partnership Service - CRUD operations for universities and partnerships
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID
from sqlalchemy import text
from fastapi import HTTPException, status

from app.models.university import (
    University, UniversityCreate, UniversityUpdate, UniversityInDB,
    Partnership, PartnershipCreate, PartnershipUpdate, PartnershipInDB,
    PartnershipModelType, PartnershipStatus, UniversityStatus
)


async def create_university(db, university_data: UniversityCreate) -> UniversityInDB:
    """Create a new university"""
    try:
        result = await db.execute(
            text("""
                INSERT INTO universities (name, slug, domain, logo_url, colors_json, contact_email, status)
                VALUES (:name, :slug, :domain, :logo_url, :colors_json, :contact_email, :status)
                RETURNING id, name, slug, domain, logo_url, colors_json, contact_email, status, created_at, updated_at
            """),
            {
                "name": university_data.name,
                "slug": university_data.slug,
                "domain": university_data.domain,
                "logo_url": university_data.logo_url,
                "colors_json": university_data.colors_json,
                "contact_email": university_data.contact_email,
                "status": university_data.status.value
            }
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create university")
        
        return UniversityInDB(**dict(row))
    except Exception as e:
        if "unique constraint" in str(e).lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="University with this slug already exists")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_university_by_id(db, university_id: UUID) -> Optional[UniversityInDB]:
    """Get university by ID"""
    result = await db.execute(
        text("""
            SELECT id, name, slug, domain, logo_url, colors_json, contact_email, status, created_at, updated_at
            FROM universities WHERE id = :id
        """),
        {"id": university_id}
    )
    row = result.fetchone()
    if not row:
        return None
    return UniversityInDB(**dict(row))


async def get_university_by_slug(db, slug: str) -> Optional[UniversityInDB]:
    """Get university by slug"""
    result = await db.execute(
        text("""
            SELECT id, name, slug, domain, logo_url, colors_json, contact_email, status, created_at, updated_at
            FROM universities WHERE slug = :slug
        """),
        {"slug": slug}
    )
    row = result.fetchone()
    if not row:
        return None
    return UniversityInDB(**dict(row))


async def list_universities(db, status_filter: Optional[UniversityStatus] = None) -> List[UniversityInDB]:
    """List all universities"""
    if status_filter:
        result = await db.execute(
            text("""
                SELECT id, name, slug, domain, logo_url, colors_json, contact_email, status, created_at, updated_at
                FROM universities WHERE status = :status
                ORDER BY name
            """),
            {"status": status_filter.value}
        )
    else:
        result = await db.execute(
            text("""
                SELECT id, name, slug, domain, logo_url, colors_json, contact_email, status, created_at, updated_at
                FROM universities
                ORDER BY name
            """)
        )
    
    rows = result.fetchall()
    return [UniversityInDB(**dict(row)) for row in rows]


async def update_university(db, university_id: UUID, university_data: UniversityUpdate) -> UniversityInDB:
    """Update university"""
    # Build dynamic update query
    updates = []
    params = {"id": university_id}
    
    if university_data.name is not None:
        updates.append("name = :name")
        params["name"] = university_data.name
    if university_data.domain is not None:
        updates.append("domain = :domain")
        params["domain"] = university_data.domain
    if university_data.logo_url is not None:
        updates.append("logo_url = :logo_url")
        params["logo_url"] = university_data.logo_url
    if university_data.colors_json is not None:
        updates.append("colors_json = :colors_json")
        params["colors_json"] = university_data.colors_json
    if university_data.contact_email is not None:
        updates.append("contact_email = :contact_email")
        params["contact_email"] = university_data.contact_email
    if university_data.status is not None:
        updates.append("status = :status")
        params["status"] = university_data.status.value
    
    if not updates:
        return await get_university_by_id(db, university_id)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    result = await db.execute(
        text(f"""
            UPDATE universities
            SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id, name, slug, domain, logo_url, colors_json, contact_email, status, created_at, updated_at
        """),
        params
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    
    return UniversityInDB(**dict(row))


async def create_partnership(db, partnership_data: PartnershipCreate) -> PartnershipInDB:
    """Create a new partnership"""
    # Verify university exists
    university = await get_university_by_id(db, partnership_data.university_id)
    if not university:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    
    try:
        result = await db.execute(
            text("""
                INSERT INTO partnerships (
                    university_id, model_type, pricing_tier, price_per_seat, commission_percent,
                    contract_start, contract_end, status, metadata_json
                )
                VALUES (
                    :university_id, :model_type, :pricing_tier, :price_per_seat, :commission_percent,
                    :contract_start, :contract_end, :status, :metadata_json
                )
                RETURNING id, university_id, model_type, pricing_tier, price_per_seat, commission_percent,
                          contract_start, contract_end, status, metadata_json, created_at, updated_at
            """),
            {
                "university_id": partnership_data.university_id,
                "model_type": partnership_data.model_type.value,
                "pricing_tier": partnership_data.pricing_tier,
                "price_per_seat": partnership_data.price_per_seat,
                "commission_percent": partnership_data.commission_percent,
                "contract_start": partnership_data.contract_start,
                "contract_end": partnership_data.contract_end,
                "status": partnership_data.status.value,
                "metadata_json": partnership_data.metadata_json
            }
        )
        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create partnership")
        
        return PartnershipInDB(**dict(row))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def get_partnership_by_id(db, partnership_id: UUID) -> Optional[PartnershipInDB]:
    """Get partnership by ID"""
    result = await db.execute(
        text("""
            SELECT id, university_id, model_type, pricing_tier, price_per_seat, commission_percent,
                   contract_start, contract_end, status, metadata_json, created_at, updated_at
            FROM partnerships WHERE id = :id
        """),
        {"id": partnership_id}
    )
    row = result.fetchone()
    if not row:
        return None
    
    row_dict = dict(row)
    row_dict["model_type"] = PartnershipModelType(row_dict["model_type"])
    row_dict["status"] = PartnershipStatus(row_dict["status"])
    return PartnershipInDB(**row_dict)


async def list_partnerships(
    db,
    university_id: Optional[UUID] = None,
    model_type: Optional[PartnershipModelType] = None,
    status_filter: Optional[PartnershipStatus] = None
) -> List[PartnershipInDB]:
    """List partnerships with optional filters"""
    conditions = []
    params = {}
    
    if university_id:
        conditions.append("university_id = :university_id")
        params["university_id"] = university_id
    if model_type:
        conditions.append("model_type = :model_type")
        params["model_type"] = model_type.value
    if status_filter:
        conditions.append("status = :status")
        params["status"] = status_filter.value
    
    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    
    result = await db.execute(
        text(f"""
            SELECT id, university_id, model_type, pricing_tier, price_per_seat, commission_percent,
                   contract_start, contract_end, status, metadata_json, created_at, updated_at
            FROM partnerships
            {where_clause}
            ORDER BY created_at DESC
        """),
        params
    )
    
    rows = result.fetchall()
    partnerships = []
    for row in rows:
        row_dict = dict(row)
        row_dict["model_type"] = PartnershipModelType(row_dict["model_type"])
        row_dict["status"] = PartnershipStatus(row_dict["status"])
        partnerships.append(PartnershipInDB(**row_dict))
    
    return partnerships


async def update_partnership(db, partnership_id: UUID, partnership_data: PartnershipUpdate) -> PartnershipInDB:
    """Update partnership"""
    updates = []
    params = {"id": partnership_id}
    
    if partnership_data.pricing_tier is not None:
        updates.append("pricing_tier = :pricing_tier")
        params["pricing_tier"] = partnership_data.pricing_tier
    if partnership_data.price_per_seat is not None:
        updates.append("price_per_seat = :price_per_seat")
        params["price_per_seat"] = partnership_data.price_per_seat
    if partnership_data.commission_percent is not None:
        updates.append("commission_percent = :commission_percent")
        params["commission_percent"] = partnership_data.commission_percent
    if partnership_data.contract_start is not None:
        updates.append("contract_start = :contract_start")
        params["contract_start"] = partnership_data.contract_start
    if partnership_data.contract_end is not None:
        updates.append("contract_end = :contract_end")
        params["contract_end"] = partnership_data.contract_end
    if partnership_data.status is not None:
        updates.append("status = :status")
        params["status"] = partnership_data.status.value
    if partnership_data.metadata_json is not None:
        updates.append("metadata_json = :metadata_json")
        params["metadata_json"] = partnership_data.metadata_json
    
    if not updates:
        return await get_partnership_by_id(db, partnership_id)
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    result = await db.execute(
        text(f"""
            UPDATE partnerships
            SET {', '.join(updates)}
            WHERE id = :id
            RETURNING id, university_id, model_type, pricing_tier, price_per_seat, commission_percent,
                      contract_start, contract_end, status, metadata_json, created_at, updated_at
        """),
        params
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    
    row_dict = dict(row)
    row_dict["model_type"] = PartnershipModelType(row_dict["model_type"])
    row_dict["status"] = PartnershipStatus(row_dict["status"])
    return PartnershipInDB(**row_dict)


async def renew_partnership(db, partnership_id: UUID, new_end_date: date) -> PartnershipInDB:
    """Renew partnership contract"""
    result = await db.execute(
        text("""
            UPDATE partnerships
            SET contract_end = :contract_end,
                status = 'active',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
            RETURNING id, university_id, model_type, pricing_tier, price_per_seat, commission_percent,
                      contract_start, contract_end, status, metadata_json, created_at, updated_at
        """),
        {"id": partnership_id, "contract_end": new_end_date}
    )
    row = result.fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partnership not found")
    
    row_dict = dict(row)
    row_dict["model_type"] = PartnershipModelType(row_dict["model_type"])
    row_dict["status"] = PartnershipStatus(row_dict["status"])
    return PartnershipInDB(**row_dict)

