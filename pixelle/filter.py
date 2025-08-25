# 配置日志 - 过滤健康检查的访问日志
import logging


class HealthCheckFilter(logging.Filter):
    """过滤健康检查的访问日志"""

    def filter(self, record):
        if hasattr(record, 'getMessage'):
            message = record.getMessage()
            # 过滤掉健康检查的访问日志
            if 'GET /health HTTP/1.1' in message:
                return False
        return True