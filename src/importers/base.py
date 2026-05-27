from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ImportResult:
    account_id: str
    inserted: int
    skipped_duplicates: int
    total_read: int

    def summary(self) -> str:
        return (
            f"account={self.account_id} read={self.total_read} "
            f"inserted={self.inserted} skipped_dups={self.skipped_duplicates}"
        )
