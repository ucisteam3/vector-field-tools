"""
Project Manager - CRUD for video clipping projects.
Each project = one analyzed video with clips.
"""

import json
import os
import shutil
import string
import random
from pathlib import Path
from datetime import datetime
from typing import Optional

# Project root (parent of backend/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = PROJECT_ROOT / "projects"


def _ensure_projects_dir():
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


def _generate_id() -> str:
    """Generate short project ID (e.g. A82K1)"""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=5))


def create_project(title: str = "Untitled", youtube_url: str = None) -> dict:
    """Create a new empty project. Returns project metadata."""
    _ensure_projects_dir()
    pid = _generate_id()
    while (PROJECTS_DIR / pid).exists():
        pid = _generate_id()

    project_dir = PROJECTS_DIR / pid
    project_dir.mkdir(parents=True)
    (project_dir / "clips").mkdir(exist_ok=True)

    meta = {
        "project_id": pid,
        "title": title,
        "youtube_url": youtube_url or None,
        "video_path": None,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "clips": [],
        "status": "pending",  # pending | analyzing | ready | error
        "error": None,
    }
    _save_metadata(pid, meta)
    return meta


def delete_project(project_id: str) -> bool:
    """Delete a project and its files. Returns True if deleted."""
    project_dir = PROJECTS_DIR / project_id
    if not project_dir.exists():
        return False
    try:
        shutil.rmtree(project_dir)
        return True
    except Exception:
        return False


def get_project(project_id: str) -> Optional[dict]:
    """Get project metadata by ID."""
    meta_path = PROJECTS_DIR / project_id / "metadata.json"
    if not meta_path.exists():
        return None
    with open(meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_projects() -> list:
    """List all projects, sorted by updated_at descending."""
    _ensure_projects_dir()
    projects = []
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir():
            meta = get_project(d.name)
            if meta:
                projects.append(meta)
    projects.sort(key=lambda p: p.get("updated_at", ""), reverse=True)
    return projects


def update_project(project_id: str, **kwargs) -> Optional[dict]:
    """Update project metadata. Returns updated metadata or None."""
    meta = get_project(project_id)
    if not meta:
        return None
    meta.update(kwargs)
    meta["updated_at"] = datetime.utcnow().isoformat() + "Z"
    _save_metadata(project_id, meta)
    return meta


def _save_metadata(project_id: str, meta: dict):
    path = PROJECTS_DIR / project_id / "metadata.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def get_project_dir(project_id: str) -> Path:
    """Return the project directory path."""
    return PROJECTS_DIR / project_id


def get_video_path(project_id: str) -> Optional[Path]:
    """Return path to video file if it exists."""
    meta = get_project(project_id)
    if not meta or not meta.get("video_path"):
        return None
    p = PROJECTS_DIR / project_id / meta["video_path"]
    return p if p.exists() else None


def get_clip_path(project_id: str, clip_filename: str) -> Optional[Path]:
    """Return path to a clip file."""
    p = PROJECTS_DIR / project_id / "clips" / clip_filename
    return p if p.exists() else None
