from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from uuid import UUID
from io import BytesIO

from app.services.export_service import ExportService
from app.schemas.response import SuccessResponse
from app.core.dependencies import get_current_active_user

router = APIRouter()


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported export formats"""
    try:
        service = ExportService()
        formats = service.get_supported_formats()

        return SuccessResponse(data={
            "formats": formats,
            "total": len(formats)
        })
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve supported formats"
        )


@router.get("/{export_id}/status")
async def get_export_status(
        export_id: str,
        current_user: dict = Depends(get_current_active_user)
):
    """Get the status of an export job"""
    try:
        service = ExportService()
        job_status = service.get_export_status(export_id)

        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found or expired"
            )

        # Verify user owns the export job
        if job_status.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this export job"
            )

        return SuccessResponse(data=job_status)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export status"
        )


@router.get("/{export_id}/download")
async def download_export(
        export_id: str,
        current_user: dict = Depends(get_current_active_user)
):
    """Download the exported file"""
    try:
        service = ExportService()

        # Check export status first
        job_status = service.get_export_status(export_id)
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found or expired"
            )

        # Verify user owns the export job
        if job_status.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this export job"
            )

        # Check if export is completed
        if job_status["status"] != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Export is not ready. Current status: {job_status['status']}"
            )

        # Get the file content
        file_content = service.get_export_file(export_id)
        if not file_content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export file not found"
            )

        # Determine file details based on format
        export_format = job_status.get("export_format", "pdf")
        resume_title = job_status.get("resume_title", "resume")

        # Clean title for filename
        safe_title = "".join(c for c in resume_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')

        if export_format == "pdf":
            media_type = "application/pdf"
            filename = f"{safe_title}.pdf"
        elif export_format == "docx":
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"{safe_title}.docx"
        elif export_format == "html":
            media_type = "text/html"
            filename = f"{safe_title}.html"
        else:
            media_type = "application/octet-stream"
            filename = f"{safe_title}.{export_format}"

        # Create streaming response
        file_stream = BytesIO(file_content)

        return StreamingResponse(
            iter([file_content]),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(file_content))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download export file"
        )


@router.delete("/{export_id}")
async def delete_export(
        export_id: str,
        current_user: dict = Depends(get_current_active_user)
):
    """Delete an export job and its associated file"""
    try:
        service = ExportService()

        # Check export status first
        job_status = service.get_export_status(export_id)
        if not job_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )

        # Verify user owns the export job
        if job_status.get("user_id") != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this export job"
            )

        # Clean up the export job
        success = service.cleanup_export_job(export_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete export job"
            )

        return SuccessResponse(
            message="Export job deleted successfully",
            data={"export_id": export_id}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete export job"
        )


@router.get("/stats/overview")
async def get_export_stats(
        current_user: dict = Depends(get_current_active_user)
):
    """Get export statistics for the current user"""
    try:
        service = ExportService()
        stats = service.get_export_statistics(current_user["id"])

        return SuccessResponse(data=stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export statistics"
        )