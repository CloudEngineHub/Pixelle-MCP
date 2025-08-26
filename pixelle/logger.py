# Copyright (C) 2025 AIDC-AI
# This project is licensed under the MIT License (SPDX-License-identifier: MIT).

from pixelle.filter import HealthCheckFilter
import logging

# 应用过滤器到访问日志记录器
logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())

# 设置引擎io和socketio的日志级别
logging.getLogger("socketio").setLevel(logging.WARNING)
logging.getLogger("engineio").setLevel(logging.WARNING)
logging.getLogger("numexpr").setLevel(logging.WARNING)

# log config
logger_level = logging.INFO
logging.basicConfig(
    level=logger_level,
    format='%(asctime)s- %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    force=True
)

logger = logging.getLogger("PM")
logger.setLevel(logger_level)
