import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class AgentContext:
    messages: list = field(default_factory=list)
    work_dir: str = ""
    parent_to_delete: Optional[str] = None
    generation: int = 0
    ui_port: Optional[int] = None

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "AgentContext":
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)
