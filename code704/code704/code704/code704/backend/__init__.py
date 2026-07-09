# -*- coding: utf-8 -*-
"""Backend — FastAPI application factory and service layer."""
from .main import app

def create_app():
    """Application factory for testing and deployment."""
    return app

__all__ = ["app", "create_app"]
