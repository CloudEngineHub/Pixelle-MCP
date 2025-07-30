# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

"""
Pixelle Base Service
基于FastAPI的基础服务，提供文件存储和共用服务能力
"""

import uvicorn
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from services.file_service import file_service
from storage import FileInfo


# 配置日志 - 过滤健康检查的访问日志
class HealthCheckFilter(logging.Filter):
    """过滤健康检查的访问日志"""
    def filter(self, record):
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            # 过滤掉健康检查的访问日志
            if 'GET /health HTTP/1.1' in message:
                return False
        return True

# 应用过滤器到访问日志记录器
access_logger = logging.getLogger("uvicorn.access")
access_logger.addFilter(HealthCheckFilter())

# 创建FastAPI应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基础服务，提供文件存储和共用服务能力"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """根路径"""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "storage_type": settings.storage_type,
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "storage_type": settings.storage_type}


@app.post(f"/upload", response_model=FileInfo)
async def upload_file(file: UploadFile = File(...)):
    """
    上传文件
    
    Args:
        file: 上传的文件
        
    Returns:
        FileInfo: 文件信息
    """
    return await file_service.upload_file(file)


@app.get(f"/files/{{file_id}}")
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


@app.get(f"/files/{{file_id}}/info", response_model=FileInfo)
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
# @app.delete(f"/files/{{file_id}}")
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


@app.get(f"/files/{{file_id}}/exists")
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


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=settings.debug
    ) 