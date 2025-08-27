# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import Response

from pixelle.upload.file_service import file_service
from pixelle.upload.base import FileInfo

# 创建路由器
router = APIRouter(
    tags=["files"],
    responses={404: {"description": "Not found"}},
)


@router.post("/upload", response_model=FileInfo)
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件
    
    Args:
        file: 上传的文件
        
    Returns:
        FileInfo: 文件信息
    """
    return await file_service.upload_file(file)


@router.get("/{file_id}")
async def get_file(file_id: str):
    """
    获取文件
    
    Args:
        file_id: 文件ID
        
    Returns:
        文件内容
    """
    # 获取文件信息
    file_info = await file_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")

    # 获取文件内容
    file_content = await file_service.get_file(file_id)
    if not file_content:
        raise HTTPException(status_code=404, detail="File content not found")

    # 返回文件流
    return Response(
        content=file_content,
        media_type=file_info.content_type,
        headers={
            "Content-Disposition": f"inline; filename={file_info.filename}"
        }
    )


@router.get("/{file_id}/info", response_model=FileInfo)
async def get_file_info(file_id: str):
    """
    获取文件信息
    
    Args:
        file_id: 文件ID
        
    Returns:
        FileInfo: 文件信息
    """
    file_info = await file_service.get_file_info(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="File not found")
    return file_info


# 暂不开放, 防止数据丢失
# @router.delete("/{file_id}")
async def delete_file(file_id: str):
    """
    删除文件
    
    Args:
        file_id: 文件ID
        
    Returns:
        删除结果
    """
    success = await file_service.delete_file(file_id)
    if not success:
        raise HTTPException(status_code=404, detail="File not found or delete failed")
    return {"message": "File deleted successfully"}


@router.get("/{file_id}/exists")
async def check_file_exists(file_id: str):
    """
    检查文件是否存在
    
    Args:
        file_id: 文件ID
        
    Returns:
        存在性检查结果
    """
    exists = await file_service.file_exists(file_id)
    return {"exists": exists}
