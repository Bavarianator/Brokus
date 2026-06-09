"""Abstract base class and data types for cloud upload."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class UploadResult:
    """Result of a single file upload to a cloud provider."""

    success: bool
    provider: str
    remote_path: str
    share_link: Optional[str] = None
    error: Optional[str] = None

    def __str__(self):
        if self.success:
            link = f" → {self.share_link}" if self.share_link else ""
            return f"✅ {self.provider}: {self.remote_path}{link}"
        return f"❌ {self.provider}: {self.error}"


class CloudUploader(ABC):
    """Abstract base class for cloud storage providers.

    Subclasses must implement :meth:`upload` and :meth:`test_connection`.
    """

    name: str = "Unknown"

    @abstractmethod
    def upload(self, local_path: Path, remote_folder: str = "brokus/") -> UploadResult:
        """Upload a local file to the cloud provider.

        Args:
            local_path: Path to the local file to upload.
            remote_folder: Destination folder path on the remote.

        Returns:
            An :class:`UploadResult` describing the outcome.
        """
        ...

    @abstractmethod
    def test_connection(self) -> bool:
        """Return ``True`` if the provider is reachable and credentials work."""
        ...

    @property
    def is_ready(self) -> bool:
        """Convenience: can this uploader be used right now?"""
        return self.test_connection()
