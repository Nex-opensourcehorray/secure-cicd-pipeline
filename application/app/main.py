"""Minimal FastAPI service for the secure CI/CD portfolio project."""

import os

from fastapi import FastAPI


APP_NAME = os.getenv("APP_NAME", "secure-cicd-demo")
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
APP_ENV = os.getenv("APP_ENV", "development")

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.get("/")
async def root() -> dict[str, str]:
    """Return the service identity and runtime status."""
    return {"service": APP_NAME, "status": "running"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Return a dependency-free health response."""
    return {"status": "healthy"}


@app.get("/version")
async def version() -> dict[str, str]:
    """Return non-sensitive application metadata."""
    return {"version": APP_VERSION, "environment": APP_ENV}
