"""JSON file storage operations."""

import json
import shutil
from pathlib import Path
from typing import Optional

from paper_bartender.config.settings import Settings, get_settings
from paper_bartender.models.storage import StorageData


class JsonStore:
    """Handles JSON file storage with atomic writes and backups."""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """Initialize the JSON store."""
        self._settings = settings or get_settings()
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        """Ensure the data directory exists."""
        self._settings.data_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> StorageData:
        """Load data from the JSON file."""
        data_path = self._settings.data_path
        if not data_path.exists():
            return StorageData()

        with open(data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return StorageData.model_validate(data)

    def save(self, data: StorageData) -> None:
        """Save data to the JSON file with atomic write."""
        data_path = self._settings.data_path
        tmp_path = data_path.with_suffix('.tmp')

        json_str = data.model_dump_json(indent=2)
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(json_str)

        tmp_path.replace(data_path)

    def backup(self) -> Optional[Path]:
        """Create a backup of the data file."""
        data_path = self._settings.data_path
        if not data_path.exists():
            return None

        backup_path = data_path.with_suffix('.backup.json')
        shutil.copy2(data_path, backup_path)
        return Path(backup_path)

    def restore_backup(self) -> bool:
        """Restore from backup if it exists."""
        data_path = self._settings.data_path
        backup_path = data_path.with_suffix('.backup.json')

        if not backup_path.exists():
            return False

        shutil.copy2(backup_path, data_path)
        return True

    def clear(self) -> Optional[Path]:
        """Clear all data, creating a backup first.

        Returns:
            Path to the backup file, or None if no data existed.
        """
        backup_path = self.backup()
        self.save(StorageData())
        return backup_path
