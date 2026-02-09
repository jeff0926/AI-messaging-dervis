"""Function Catalog — persistent store for reusable function definitions.

Each function is stored as a JSON file in data/functions/ with:
  - name: unique identifier (snake_case)
  - description: what the function does
  - parameters: expected input schema
  - returns: expected output schema
  - source: the Python source code
  - tags: searchable labels
  - created_by: user who created it
  - created_at: timestamp
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FUNCTIONS_DIR = Path(os.getenv("FUNCTIONS_DIR", "data/functions"))


class FunctionEntry:
    """A single function in the catalog."""

    def __init__(
        self,
        name: str,
        description: str = "",
        parameters: dict[str, Any] | None = None,
        returns: dict[str, Any] | None = None,
        source: str = "",
        tags: list[str] | None = None,
        created_by: str = "",
        created_at: str | None = None,
    ) -> None:
        self.name = name
        self.description = description
        self.parameters = parameters or {"query": "string"}
        self.returns = returns or {"result": "string"}
        self.source = source
        self.tags = tags or []
        self.created_by = created_by
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "returns": self.returns,
            "source": self.source,
            "tags": self.tags,
            "created_by": self.created_by,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FunctionEntry:
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            parameters=data.get("parameters"),
            returns=data.get("returns"),
            source=data.get("source", ""),
            tags=data.get("tags", []),
            created_by=data.get("created_by", ""),
            created_at=data.get("created_at"),
        )

    def summary(self) -> str:
        """One-line summary for listing."""
        tag_str = f" [{', '.join(self.tags)}]" if self.tags else ""
        return f"{self.name} — {self.description}{tag_str}"


class FunctionCatalog:
    """Persistent catalog of reusable function definitions.

    Functions are saved as JSON files in FUNCTIONS_DIR.
    """

    def __init__(self, functions_dir: Path | None = None) -> None:
        self._dir = functions_dir or FUNCTIONS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, FunctionEntry] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all function definitions from disk."""
        for path in self._dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                entry = FunctionEntry.from_dict(data)
                self._cache[entry.name] = entry
            except Exception:
                logger.exception("Failed to load function from %s", path)
        if self._cache:
            logger.info("Loaded %d functions from catalog", len(self._cache))

    def save(self, entry: FunctionEntry) -> None:
        """Save a function to the catalog (creates or overwrites)."""
        self._cache[entry.name] = entry
        path = self._dir / f"{entry.name}.json"
        path.write_text(json.dumps(entry.to_dict(), indent=2))
        logger.info("Saved function: %s", entry.name)

    def get(self, name: str) -> FunctionEntry | None:
        """Look up a function by name."""
        return self._cache.get(name)

    def delete(self, name: str) -> bool:
        """Remove a function from the catalog. Returns True if it existed."""
        if name not in self._cache:
            return False
        del self._cache[name]
        path = self._dir / f"{name}.json"
        path.unlink(missing_ok=True)
        logger.info("Deleted function: %s", name)
        return True

    def list_all(self) -> list[FunctionEntry]:
        """Return all functions sorted by name."""
        return sorted(self._cache.values(), key=lambda e: e.name)

    def search(self, query: str) -> list[FunctionEntry]:
        """Search functions by name, description, or tags."""
        q = query.lower()
        results = []
        for entry in self._cache.values():
            if (
                q in entry.name.lower()
                or q in entry.description.lower()
                or any(q in tag.lower() for tag in entry.tags)
            ):
                results.append(entry)
        return sorted(results, key=lambda e: e.name)

    def stats(self) -> dict[str, Any]:
        """Return catalog statistics."""
        all_tags = set()
        for e in self._cache.values():
            all_tags.update(e.tags)
        return {
            "total_functions": len(self._cache),
            "tags": sorted(all_tags),
        }
