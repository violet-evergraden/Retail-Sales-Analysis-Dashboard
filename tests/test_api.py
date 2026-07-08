"""测试 - API 端点"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAPI:
    """测试API端点（基础结构验证）"""

    def test_import_api_module(self):
        from src.api import app
        assert app is not None

    def test_app_has_routes(self):
        from src.api import app
        routes = [r.path for r in app.routes]
        assert "/" in routes
        assert "/api/health" in routes
        assert "/api/kpi" in routes
