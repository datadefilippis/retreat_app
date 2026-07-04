import logging
import os
import re
import json
import base64
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import List, Optional
from models import DatasetResponse, UploadResponse, DatasetType
from auth import get_current_user, get_verified_user, require_admin
from repositories import dataset_repository
from services import dataset_service
from services.dataset_service import UPLOAD_DIR, analyze_columns_for_mapping, check_row_duplicates, filter_duplicate_rows
from services.kpi_snapshot_service import refresh_for_org
from database import temp_uploads_collection, datasets_collection
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Maximum upload size: 50 MB.  A CSV with 100k rows × 20 columns is ~15 MB;
# a formatted XLSX can reach ~30 MB.  50 MB covers any realistic PMI dataset.
_MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

# Regex: keep only safe characters in filenames sent via Content-Disposition.
_SAFE_FILENAME_RE = re.compile(r'[^\w\s.\-()]', re.UNICODE)

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("/upload", response_model=UploadResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(...),
    dataset_type: DatasetType = Form(...),
    confirm_duplicate: bool = Form(False),
    skip_duplicate_rows: bool = Form(False),
    current_user: dict = Depends(get_verified_user)
):
    """Upload a new dataset (CSV, XLSX, or XLS).

    Returns UploadResponse which extends DatasetResponse with per-upload
    reporting fields (errors, validation_rows_skipped, validation_rules_active,
    total_rows_attempted).  All new fields default to 0 / [] so existing
    clients that ignore them are unaffected.

    Max upload size: 50 MB (F4 hardening).
    """
    content = await file.read()

    # F4: reject oversized uploads before any parsing
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File troppo grande. Dimensione massima consentita: {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    try:
        # v3.0: Pre-analyze columns to detect mapping needs
        analysis = await analyze_columns_for_mapping(
            content=content,
            filename=file.filename,
            dataset_type=dataset_type,
            org_id=current_user['organization_id'],
        )

        if analysis["status"] == "needs_column_mapping":
            # Store file temporarily (TTL 1h auto-expire) and return 422
            temp_id = f"temp_{current_user['user_id']}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            await temp_uploads_collection.insert_one({
                "_id": temp_id,
                "content_b64": base64.b64encode(content).decode("ascii"),
                "filename": file.filename,
                "name": name,
                "dataset_type": dataset_type.value,
                "organization_id": current_user['organization_id'],
                "user_id": current_user['user_id'],
                "created_at": datetime.now(timezone.utc),
            })
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "status": "needs_column_mapping",
                    "temp_upload_id": temp_id,
                    "recognized_columns": analysis["recognized_columns"],
                    "unmapped_columns": analysis["unmapped_columns"],
                    "missing_required": analysis["missing_required"],
                    "target_fields": analysis["target_fields"],
                    "preview_rows": analysis["preview_rows"],
                    "all_file_columns": analysis["all_file_columns"],
                },
            )

        # v3.1: Combined pre-upload duplicate detection (file-level + row-level)
        # Runs AFTER column analysis succeeds but BEFORE data is inserted.
        if not confirm_duplicate:
            org_id = current_user['organization_id']

            # 1) File-level: same filename already uploaded?
            file_dupes = []
            existing_dupes = await datasets_collection.find(
                {
                    "organization_id": org_id,
                    "dataset_type": dataset_type.value,
                    "original_filename": file.filename,
                },
                {"_id": 0, "id": 1, "name": 1, "row_count": 1, "created_at": 1, "is_active": 1},
            ).sort("created_at", -1).to_list(10)

            if existing_dupes:
                for d in existing_dupes:
                    ca = d.get("created_at", "")
                    if hasattr(ca, "isoformat"):
                        ca = ca.isoformat()
                    file_dupes.append({
                        "name": d.get("name", ""),
                        "row_count": d.get("row_count", 0),
                        "created_at": str(ca),
                        "is_active": d.get("is_active", True),
                    })

            # 2) Row-level: individual rows that already exist in DB?
            # Reuse column_map from analysis to avoid redundant DB query.
            row_dup_info = await check_row_duplicates(
                content, file.filename, dataset_type, org_id,
                column_map=analysis.get("_column_map"),
            )

            # Raise 409 if either check found duplicates
            has_file_dupes = len(file_dupes) > 0
            has_row_dupes = row_dup_info["duplicate_row_count"] > 0

            if has_file_dupes or has_row_dupes:
                msg_parts = []
                if has_file_dupes:
                    msg_parts.append(
                        f"Trovati {len(file_dupes)} caricamenti precedenti con lo stesso "
                        f"nome file \"{file.filename}\""
                    )
                if has_row_dupes:
                    msg_parts.append(
                        f"Trovate {row_dup_info['duplicate_row_count']} righe "
                        f"potenzialmente duplicate su {row_dup_info['total_new_rows']} "
                        f"righe totali nel file"
                    )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "duplicate_found",
                        "duplicates": file_dupes,
                        "count": len(file_dupes),
                        "row_duplicates": row_dup_info,
                        "message": ". ".join(msg_parts) + ".",
                    },
                )

        # All required columns auto-mapped, no duplicates (or confirmed) — proceed
        # Reuse column_map from analysis to avoid redundant DB query.
        result = await dataset_service.parse_and_save_dataset(
            content=content,
            filename=file.filename,
            name=name,
            dataset_type=dataset_type,
            org_id=current_user['organization_id'],
            user_id=current_user['user_id'],
            skip_duplicate_rows=skip_duplicate_rows,
            column_map=analysis.get("_column_map"),
        )

        created_at = result['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return UploadResponse(
            id=result['id'],
            name=result['name'],
            dataset_type=result['dataset_type'],
            row_count=result['row_count'],
            organization_id=result['organization_id'],
            uploaded_by=result['uploaded_by'],
            created_at=created_at,
            is_active=result['is_active'],
            # ── v2.2 reporting fields ─────────────────────────────────────
            errors=result.get('errors', []),
            validation_rows_skipped=result.get('validation_rows_skipped', 0),
            validation_rules_active=result.get('validation_rules_active', 0),
            total_rows_attempted=result.get('total_rows_attempted', result['row_count']),
            # ── v3.0 accumulative upload ─────────────────────────────────
            duplicate_warning=result.get('duplicate_warning'),
            # ── v3.1 skip duplicate rows ──────────────────────────────
            duplicate_rows_skipped=result.get('duplicate_rows_skipped', 0),
            # ── v7.0 entity linking ──────────────────────────────────
            entity_linking_stats=result.get('entity_linking_stats'),
        )
    except HTTPException:
        raise  # re-raise 409 (duplicate) and 422 (column mapping)
    except ValueError as e:
        logger.warning("upload_dataset parse error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("upload_dataset unexpected error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante il caricamento. Riprova più tardi.",
        )


@router.post("/upload-with-mapping", response_model=UploadResponse)
async def upload_with_mapping(
    temp_upload_id: str = Form(...),
    column_mapping: str = Form(...),  # JSON string: {"file_col": "target_field", ...}
    save_mapping: bool = Form(False),
    confirm_duplicate: bool = Form(False),
    skip_duplicate_rows: bool = Form(False),
    current_user: dict = Depends(get_verified_user),
):
    """Complete an upload using user-provided column mapping.

    Called after a 422 response from /upload with status='needs_column_mapping'.
    Retrieves the temporarily stored file and processes it with the user's mapping.
    """
    # 1. Retrieve temp upload
    temp_doc = await temp_uploads_collection.find_one({
        "_id": temp_upload_id,
        "organization_id": current_user['organization_id'],
    })
    if not temp_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload temporaneo non trovato o scaduto. Ricarica il file.",
        )

    # 2. Parse the column mapping JSON
    try:
        user_mapping = json.loads(column_mapping)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Formato mapping non valido.",
        )

    # 3. Decode the stored file content
    content = base64.b64decode(temp_doc["content_b64"])
    filename = temp_doc["filename"]
    name = temp_doc["name"]
    dataset_type = DatasetType(temp_doc["dataset_type"])

    try:
        # 3.5. Row-level duplicate check (file-level was already checked in /upload)
        if not confirm_duplicate:
            org_id = current_user['organization_id']
            row_dup_info = await check_row_duplicates(
                content, filename, dataset_type, org_id,
                user_column_mapping=user_mapping,
            )
            # Also check file-level duplicates (in case file was uploaded
            # between the original /upload call and this mapping step)
            file_dupes = []
            existing_dupes = await datasets_collection.find(
                {
                    "organization_id": org_id,
                    "dataset_type": dataset_type.value,
                    "original_filename": filename,
                },
                {"_id": 0, "id": 1, "name": 1, "row_count": 1, "created_at": 1, "is_active": 1},
            ).sort("created_at", -1).to_list(10)

            if existing_dupes:
                for d in existing_dupes:
                    ca = d.get("created_at", "")
                    if hasattr(ca, "isoformat"):
                        ca = ca.isoformat()
                    file_dupes.append({
                        "name": d.get("name", ""),
                        "row_count": d.get("row_count", 0),
                        "created_at": str(ca),
                        "is_active": d.get("is_active", True),
                    })

            has_file_dupes = len(file_dupes) > 0
            has_row_dupes = row_dup_info["duplicate_row_count"] > 0

            if has_file_dupes or has_row_dupes:
                msg_parts = []
                if has_file_dupes:
                    msg_parts.append(
                        f"Trovati {len(file_dupes)} caricamenti precedenti con lo stesso "
                        f"nome file \"{filename}\""
                    )
                if has_row_dupes:
                    msg_parts.append(
                        f"Trovate {row_dup_info['duplicate_row_count']} righe "
                        f"potenzialmente duplicate su {row_dup_info['total_new_rows']} "
                        f"righe totali nel file"
                    )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "status": "duplicate_found",
                        "duplicates": file_dupes,
                        "count": len(file_dupes),
                        "row_duplicates": row_dup_info,
                        "message": ". ".join(msg_parts) + ".",
                    },
                )

        # 4. Process with user mapping
        result = await dataset_service.parse_and_save_dataset(
            content=content,
            filename=filename,
            name=name,
            dataset_type=dataset_type,
            org_id=current_user['organization_id'],
            user_id=current_user['user_id'],
            user_column_mapping=user_mapping,
            skip_duplicate_rows=skip_duplicate_rows,
        )

        # 5. Optionally save the mapping for future use
        if save_mapping and user_mapping:
            try:
                from repositories.column_mapping_repository import save_user_mapping
                await save_user_mapping(
                    org_id=current_user['organization_id'],
                    dataset_type=dataset_type.value,
                    mapping=user_mapping,
                )
            except Exception as exc:
                logger.warning("Could not save user column mapping: %s", exc)

        # 6. Clean up temp upload
        await temp_uploads_collection.delete_one({"_id": temp_upload_id})

        created_at = result['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return UploadResponse(
            id=result['id'],
            name=result['name'],
            dataset_type=result['dataset_type'],
            row_count=result['row_count'],
            organization_id=result['organization_id'],
            uploaded_by=result['uploaded_by'],
            created_at=created_at,
            is_active=result['is_active'],
            errors=result.get('errors', []),
            validation_rows_skipped=result.get('validation_rows_skipped', 0),
            validation_rules_active=result.get('validation_rules_active', 0),
            total_rows_attempted=result.get('total_rows_attempted', result['row_count']),
            duplicate_warning=result.get('duplicate_warning'),
            duplicate_rows_skipped=result.get('duplicate_rows_skipped', 0),
            entity_linking_stats=result.get('entity_linking_stats'),
        )
    except HTTPException:
        raise  # re-raise 409 (duplicate) so the frontend can show the confirmation dialog
    except ValueError as e:
        logger.warning("upload_with_mapping parse error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error("upload_with_mapping unexpected error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Errore durante il caricamento. Riprova più tardi.",
        )


@router.get("", response_model=List[DatasetResponse])
async def list_datasets(
    dataset_type: Optional[DatasetType] = None,
    current_user: dict = Depends(get_verified_user)
):
    """List all datasets for the organization"""
    datasets = await dataset_repository.find_by_org(
        current_user['organization_id'],
        dataset_type=dataset_type
    )
    
    result = []
    for doc in datasets:
        created_at = doc['created_at']
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        result.append(DatasetResponse(
            id=doc['id'],
            name=doc['name'],
            dataset_type=DatasetType(doc['dataset_type']),
            row_count=doc['row_count'],
            organization_id=doc['organization_id'],
            uploaded_by=doc['uploaded_by'],
            created_at=created_at,
            is_active=doc.get('is_active', True)
        ))
    
    return result


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Get a specific dataset"""
    doc = await dataset_repository.find_by_id(
        dataset_id,
        current_user['organization_id']
    )
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    created_at = doc['created_at']
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    
    return DatasetResponse(
        id=doc['id'],
        name=doc['name'],
        dataset_type=DatasetType(doc['dataset_type']),
        row_count=doc['row_count'],
        organization_id=doc['organization_id'],
        uploaded_by=doc['uploaded_by'],
        created_at=created_at,
        is_active=doc.get('is_active', True)
    )


@router.get("/{dataset_id}/download")
async def download_dataset(
    dataset_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Download the original dataset file"""
    doc = await dataset_repository.find_by_id(
        dataset_id,
        current_user['organization_id']
    )
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    file_path = doc.get('file_path')
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset file not found"
        )

    # F3: defense-in-depth — verify the resolved path is under UPLOAD_DIR.
    # Prevents arbitrary file read if the DB document were ever tampered with.
    resolved = Path(file_path).resolve()
    if not resolved.is_relative_to(UPLOAD_DIR.resolve()):
        logger.error(
            "download_dataset: path %s is outside UPLOAD_DIR for dataset %s",
            resolved, dataset_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accesso al file non consentito.",
        )

    # F7: sanitize the original filename for the Content-Disposition header.
    raw_filename = doc.get('original_filename', f"{doc['name']}.csv")
    safe_filename = _SAFE_FILENAME_RE.sub('_', raw_filename).strip() or "dataset.csv"

    return FileResponse(
        path=str(resolved),
        filename=safe_filename,
        media_type='application/octet-stream'
    )


@router.get("/{dataset_id}/preview")
async def preview_dataset(
    dataset_id: str,
    limit: int = Query(20, le=100),
    current_user: dict = Depends(get_verified_user)
):
    """Preview dataset records"""
    doc = await dataset_repository.find_by_id(
        dataset_id,
        current_user['organization_id']
    )
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Get records based on type
    if doc['dataset_type'] == 'sales':
        records = await dataset_repository.get_sales_preview(dataset_id, limit)
    elif doc['dataset_type'] == 'purchases':
        records = await dataset_repository.get_purchase_preview(dataset_id, limit)
    elif doc['dataset_type'] == 'fixed_costs':
        records = await dataset_repository.get_fixed_cost_preview(dataset_id, limit)
    else:
        records = await dataset_repository.get_expense_preview(dataset_id, limit)
    
    return {
        "dataset_id": dataset_id,
        "dataset_type": doc['dataset_type'],
        "total_rows": doc['row_count'],
        "preview_rows": records
    }


@router.delete("/{dataset_id}")
async def delete_dataset(
    dataset_id: str,
    current_user: dict = Depends(get_verified_user)
):
    """Delete a dataset and its records (cascade deletes associated records)."""
    doc = await dataset_repository.find_by_id(
        dataset_id,
        current_user['organization_id']
    )
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    
    # Delete records based on type
    if doc['dataset_type'] == 'sales':
        await dataset_repository.delete_sales_records_by_dataset(dataset_id)
    elif doc['dataset_type'] == 'purchases':
        await dataset_repository.delete_purchase_records_by_dataset(dataset_id)
    elif doc['dataset_type'] == 'fixed_costs':
        await dataset_repository.delete_fixed_cost_records_by_dataset(dataset_id)
    else:
        await dataset_repository.delete_expense_records_by_dataset(dataset_id)
    
    # Delete dataset (org_id included in query for defense-in-depth — see F6)
    await dataset_repository.delete(dataset_id, current_user['organization_id'])
    
    # Delete file
    try:
        file_path = doc.get('file_path')
        if file_path:
            os.remove(file_path)
    except Exception:
        pass

    # Invalidate stale KPI snapshots and recompute from remaining data.
    # Fire-and-forget: errors are caught inside refresh_for_org — never raises.
    org_id = current_user['organization_id']
    try:
        await refresh_for_org(org_id, module_key="cashflow_monitor")
    except Exception as exc:  # belt-and-suspenders; should never reach here
        logger.warning("delete_dataset: snapshot refresh failed for org=%s: %s", org_id, exc)

    return {"message": "Dataset deleted successfully"}


@router.patch("/{dataset_id}/toggle-active")
async def toggle_dataset_active(
    dataset_id: str,
    current_user: dict = Depends(get_verified_user),
):
    """Toggle a dataset's is_active status.

    Clicking the status badge in the frontend calls this endpoint to
    activate or deactivate a dataset without deleting it or its records.
    """
    doc = await dataset_repository.find_by_id(
        dataset_id, current_user['organization_id']
    )
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset non trovato",
        )

    new_is_active = not doc.get('is_active', True)
    await dataset_repository.update(dataset_id, {"is_active": new_is_active})

    return {"id": dataset_id, "is_active": new_is_active}
