from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Envelope:
    type: str
    payload: dict = field(default_factory=dict)
    request_id: Optional[str] = None
    ts: Optional[int] = None

    def to_dict(self) -> dict:
        data: dict[str, Any] = {"type": self.type, "payload": self.payload}
        if self.request_id is not None:
            data["request_id"] = self.request_id
        if self.ts is not None:
            data["ts"] = self.ts
        return data

    @staticmethod
    def from_dict(data: dict) -> "Envelope":
        return Envelope(
            type=data["type"],
            payload=data.get("payload", {}),
            request_id=data.get("request_id"),
            ts=data.get("ts"),
        )
