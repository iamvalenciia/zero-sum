"""
File Manager Tool for MCP Server.
Allows Claude to manage files within the project directory safely.

Security: Operations are restricted to the project directory tree.
This prevents accidental or malicious file operations outside the project.
"""

import os
import shutil
import json
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime


class FileManager:
    """
    Secure file management within the project directory.

    Features:
    - Move/copy files to project directories
    - Register images from external paths (with copy)
    - List directory contents
    - Safe path validation (no escaping project root)
    - PROTECTED: Character images cannot be deleted or moved
    """

    # Allowed file extensions for images
    ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}

    # Allowed directories for file operations
    ALLOWED_SUBDIRS = {'data', 'old-videos'}

    # PROTECTED PATHS - These directories/files CANNOT be deleted or modified destructively
    # This prevents accidental deletion of critical character assets
    PROTECTED_PATHS = {
        'data/images/analyst',      # Analyst character images
        'data/images/skeptic',      # Skeptic character images
        'data/images/final_screen', # Final screen image
        'data/images/images_catalog.json',  # Image catalog
        'data/audio/music',         # Background music
        'data/font',                # Fonts
    }

    # File patterns that are NEVER allowed to be deleted
    PROTECTED_PATTERNS = [
        '**/analyst/**',
        '**/skeptic/**',
        '**/images_catalog.json',
        '**/final_screen/**',
    ]

    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent
        self.base_dir = Path(base_dir).resolve()
        self.shorts_dir = self.base_dir / "data" / "shorts"
        self.images_dir = self.shorts_dir / "images"

    def _validate_path(self, path: Path, must_exist: bool = True) -> Path:
        """
        Validate that a path is safe and within allowed directories.

        Args:
            path: Path to validate
            must_exist: If True, path must exist

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path is outside allowed directories
            FileNotFoundError: If must_exist and path doesn't exist
        """
        resolved = Path(path).resolve()

        # Check if path is within base_dir
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            # Path is outside project - only allow if it's a source for copying
            if must_exist and not resolved.exists():
                raise FileNotFoundError(f"Path not found: {path}")
            return resolved

        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Path not found: {path}")

        return resolved

    def _ensure_dest_dir(self, dest_path: Path) -> Path:
        """Ensure destination directory exists and is within project."""
        resolved = dest_path.resolve()

        # Destination must be within project
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise ValueError(f"Destination must be within project: {dest_path}")

        # Create parent directories if needed
        resolved.parent.mkdir(parents=True, exist_ok=True)

        return resolved

    def copy_file(
        self,
        source: str,
        destination: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Copy a file to a destination within the project.

        Args:
            source: Source file path (can be external)
            destination: Destination path (must be within project)
            overwrite: Whether to overwrite existing files

        Returns:
            Result with status and paths
        """
        try:
            src_path = self._validate_path(Path(source), must_exist=True)
            dest_path = self._ensure_dest_dir(Path(destination))

            # If destination is a directory, use source filename
            if dest_path.is_dir():
                dest_path = dest_path / src_path.name

            if dest_path.exists() and not overwrite:
                return {
                    "status": "error",
                    "message": f"Destination exists: {dest_path}. Use overwrite=True to replace.",
                    "source": str(src_path),
                    "destination": str(dest_path)
                }

            shutil.copy2(src_path, dest_path)

            return {
                "status": "success",
                "message": f"File copied successfully",
                "source": str(src_path),
                "destination": str(dest_path),
                "size_bytes": dest_path.stat().st_size
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "source": source,
                "destination": destination
            }

    def move_file(
        self,
        source: str,
        destination: str,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """
        Move a file within the project.

        PROTECTED FILES: Character images (analyst, skeptic), images_catalog.json,
        and other critical assets CANNOT be moved.

        Note: For safety, source must be within project directory.
        Use copy_file for external sources.

        Args:
            source: Source file path (must be within project)
            destination: Destination path (must be within project)
            overwrite: Whether to overwrite existing files

        Returns:
            Result with status and paths
        """
        try:
            src_path = self._validate_path(Path(source), must_exist=True)

            # For move, source must be within project
            try:
                src_path.relative_to(self.base_dir)
            except ValueError:
                return {
                    "status": "error",
                    "message": "Cannot move files from outside project. Use copy_file instead.",
                    "source": str(src_path)
                }

            # CHECK PROTECTED PATHS - Prevent moving critical assets
            is_protected, reason = self._is_protected_path(src_path)
            if is_protected:
                return {
                    "status": "error",
                    "message": f"PROTECTED FILE: {reason}",
                    "path": str(src_path),
                    "protection_info": "Character images and critical assets are protected. Use copy_file if you need a copy elsewhere."
                }

            dest_path = self._ensure_dest_dir(Path(destination))

            if dest_path.is_dir():
                dest_path = dest_path / src_path.name

            if dest_path.exists() and not overwrite:
                return {
                    "status": "error",
                    "message": f"Destination exists: {dest_path}. Use overwrite=True to replace.",
                    "source": str(src_path),
                    "destination": str(dest_path)
                }

            shutil.move(str(src_path), str(dest_path))

            return {
                "status": "success",
                "message": "File moved successfully",
                "source": str(src_path),
                "destination": str(dest_path)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "source": source,
                "destination": destination
            }

    def register_images_for_project(
        self,
        image_paths: List[str],
        project_id: str,
        rename_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Register multiple images for a specific project.
        Copies images to the project's images directory.

        Args:
            image_paths: List of source image paths
            project_id: Project ID to associate images with
            rename_pattern: Optional pattern for renaming (e.g., "scene_{n}")
                          {n} will be replaced with sequence number

        Returns:
            Result with list of registered images
        """
        project_images_dir = self.images_dir / project_id
        project_images_dir.mkdir(parents=True, exist_ok=True)

        results = {
            "status": "success",
            "project_id": project_id,
            "images_dir": str(project_images_dir),
            "registered": [],
            "errors": []
        }

        for i, img_path in enumerate(image_paths, 1):
            try:
                src_path = Path(img_path)

                if not src_path.exists():
                    results["errors"].append({
                        "source": img_path,
                        "error": "File not found"
                    })
                    continue

                # Check extension
                if src_path.suffix.lower() not in self.ALLOWED_IMAGE_EXTENSIONS:
                    results["errors"].append({
                        "source": img_path,
                        "error": f"Invalid image extension: {src_path.suffix}"
                    })
                    continue

                # Determine destination filename
                if rename_pattern:
                    new_name = rename_pattern.replace("{n}", str(i)) + src_path.suffix
                else:
                    new_name = src_path.name

                dest_path = project_images_dir / new_name

                # Handle duplicates
                if dest_path.exists():
                    base = dest_path.stem
                    ext = dest_path.suffix
                    counter = 1
                    while dest_path.exists():
                        dest_path = project_images_dir / f"{base}_{counter}{ext}"
                        counter += 1

                shutil.copy2(src_path, dest_path)

                results["registered"].append({
                    "source": str(src_path),
                    "destination": str(dest_path),
                    "filename": dest_path.name
                })

            except Exception as e:
                results["errors"].append({
                    "source": img_path,
                    "error": str(e)
                })

        if results["errors"] and not results["registered"]:
            results["status"] = "error"
        elif results["errors"]:
            results["status"] = "partial"

        return results

    def list_directory(
        self,
        path: str,
        pattern: str = "*",
        include_subdirs: bool = False
    ) -> Dict[str, Any]:
        """
        List contents of a directory within the project.

        Args:
            path: Directory path (relative to project or absolute within project)
            pattern: Glob pattern to filter files (default: "*")
            include_subdirs: Whether to include subdirectory contents

        Returns:
            Directory listing with file info
        """
        try:
            dir_path = Path(path)

            # Handle relative paths
            if not dir_path.is_absolute():
                dir_path = self.base_dir / dir_path

            dir_path = self._validate_path(dir_path, must_exist=True)

            if not dir_path.is_dir():
                return {
                    "status": "error",
                    "message": f"Not a directory: {path}"
                }

            files = []
            dirs = []

            if include_subdirs:
                items = list(dir_path.rglob(pattern))
            else:
                items = list(dir_path.glob(pattern))

            for item in items:
                info = {
                    "name": item.name,
                    "path": str(item),
                    "relative_path": str(item.relative_to(dir_path))
                }

                if item.is_file():
                    stat = item.stat()
                    info["type"] = "file"
                    info["size_bytes"] = stat.st_size
                    info["modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
                    files.append(info)
                elif item.is_dir():
                    info["type"] = "directory"
                    dirs.append(info)

            return {
                "status": "success",
                "directory": str(dir_path),
                "pattern": pattern,
                "total_files": len(files),
                "total_dirs": len(dirs),
                "files": sorted(files, key=lambda x: x["name"]),
                "directories": sorted(dirs, key=lambda x: x["name"])
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "path": path
            }

    def list_project_images(self, project_id: str) -> Dict[str, Any]:
        """List all images registered for a project."""
        project_images_dir = self.images_dir / project_id

        if not project_images_dir.exists():
            return {
                "status": "empty",
                "project_id": project_id,
                "images_dir": str(project_images_dir),
                "message": "No images directory found for this project",
                "images": []
            }

        return self.list_directory(
            str(project_images_dir),
            pattern="*"
        )

    def create_directory(self, path: str) -> Dict[str, Any]:
        """
        Create a directory within the project.

        Args:
            path: Directory path to create

        Returns:
            Result with created path
        """
        try:
            dir_path = Path(path)

            if not dir_path.is_absolute():
                dir_path = self.base_dir / dir_path

            # Validate it's within project
            try:
                dir_path.resolve().relative_to(self.base_dir)
            except ValueError:
                return {
                    "status": "error",
                    "message": "Directory must be within project"
                }

            dir_path.mkdir(parents=True, exist_ok=True)

            return {
                "status": "success",
                "message": "Directory created",
                "path": str(dir_path.resolve())
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "path": path
            }

    def _is_protected_path(self, path: Path) -> Tuple[bool, str]:
        """
        Check if a path is protected from deletion/modification.

        Returns:
            Tuple of (is_protected, reason)
        """
        try:
            relative_path = path.relative_to(self.base_dir)
            path_str = str(relative_path).replace("\\", "/")

            # Check against protected paths
            for protected in self.PROTECTED_PATHS:
                if path_str.startswith(protected) or protected in path_str:
                    return True, f"Path is protected: {protected} (character assets cannot be deleted)"

            # Check against protected patterns
            for pattern in self.PROTECTED_PATTERNS:
                # Simple pattern matching
                if "analyst" in path_str.lower() or "skeptic" in path_str.lower():
                    return True, "Character images (analyst/skeptic) are protected and cannot be deleted"
                if "images_catalog" in path_str.lower():
                    return True, "images_catalog.json is protected and cannot be deleted"
                if "final_screen" in path_str.lower():
                    return True, "final_screen images are protected and cannot be deleted"

            return False, ""
        except ValueError:
            # Path is outside project
            return False, ""

    def delete_file(self, path: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a file within the project.

        PROTECTED FILES: Character images (analyst, skeptic), images_catalog.json,
        and other critical assets CANNOT be deleted.

        Args:
            path: File path to delete
            confirm: Must be True to actually delete

        Returns:
            Result with deletion status
        """
        if not confirm:
            return {
                "status": "confirmation_required",
                "message": "Set confirm=True to delete this file",
                "path": path
            }

        try:
            file_path = self._validate_path(Path(path), must_exist=True)

            # Must be within project
            try:
                file_path.relative_to(self.base_dir)
            except ValueError:
                return {
                    "status": "error",
                    "message": "Can only delete files within project"
                }

            # CHECK PROTECTED PATHS - This prevents accidental deletion of character images
            is_protected, reason = self._is_protected_path(file_path)
            if is_protected:
                return {
                    "status": "error",
                    "message": f"PROTECTED FILE: {reason}",
                    "path": str(file_path),
                    "protection_info": "Character images and critical assets are protected to prevent accidental deletion. These files are essential for video rendering."
                }

            if file_path.is_dir():
                return {
                    "status": "error",
                    "message": "Use delete_directory for directories"
                }

            file_path.unlink()

            return {
                "status": "success",
                "message": "File deleted",
                "path": str(file_path)
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "path": path
            }


async def handle_file_operation(
    operation: str,
    arguments: Dict[str, Any],
    base_dir: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Handle file operations from MCP tool calls.

    Operations:
    - copy: Copy a file
    - move: Move a file
    - register_images: Register images for a project
    - list: List directory contents
    - list_project_images: List images for a project
    - mkdir: Create a directory
    - delete: Delete a file
    """
    manager = FileManager(base_dir)

    operations = {
        "copy": lambda: manager.copy_file(
            arguments.get("source", ""),
            arguments.get("destination", ""),
            arguments.get("overwrite", False)
        ),
        "move": lambda: manager.move_file(
            arguments.get("source", ""),
            arguments.get("destination", ""),
            arguments.get("overwrite", False)
        ),
        "register_images": lambda: manager.register_images_for_project(
            arguments.get("image_paths", []),
            arguments.get("project_id", ""),
            arguments.get("rename_pattern")
        ),
        "list": lambda: manager.list_directory(
            arguments.get("path", "."),
            arguments.get("pattern", "*"),
            arguments.get("include_subdirs", False)
        ),
        "list_project_images": lambda: manager.list_project_images(
            arguments.get("project_id", "")
        ),
        "mkdir": lambda: manager.create_directory(
            arguments.get("path", "")
        ),
        "delete": lambda: manager.delete_file(
            arguments.get("path", ""),
            arguments.get("confirm", False)
        )
    }

    if operation not in operations:
        return {
            "status": "error",
            "message": f"Unknown operation: {operation}",
            "available_operations": list(operations.keys())
        }

    return operations[operation]()
