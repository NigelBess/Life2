import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Command:
    type: str
    path: Optional[str] = None
    content: Optional[str] = None
    hunks: list = field(default_factory=list)


@dataclass
class Hunk:
    old: str
    new: str


@dataclass
class AgentResponse:
    to_user: Optional[str]
    commands: list[Command]
    to_self: str


def parse_response(raw: str) -> AgentResponse:
    match = re.search(r"<agent_response>.*?</agent_response>", raw, re.DOTALL)
    if not match:
        return AgentResponse(to_user=None, commands=[], to_self=raw.strip())

    try:
        root = ET.fromstring(match.group(0))
    except ET.ParseError:
        return AgentResponse(to_user=None, commands=[], to_self=raw.strip())

    to_user_el = root.find("to_user")
    to_user = to_user_el.text.strip() if to_user_el is not None and to_user_el.text else None

    to_self_el = root.find("to_self")
    to_self = to_self_el.text.strip() if to_self_el is not None and to_self_el.text else ""

    commands = []
    commands_el = root.find("commands")
    if commands_el is not None:
        for cmd_el in commands_el.findall("command"):
            cmd_type = cmd_el.get("type", "")

            if cmd_type == "read":
                path_el = cmd_el.find("path")
                path = path_el.text.strip() if path_el is not None and path_el.text else ""
                commands.append(Command(type="read", path=path))

            elif cmd_type == "write":
                path_el = cmd_el.find("path")
                path = path_el.text.strip() if path_el is not None and path_el.text else ""
                hunks = []
                patch_el = cmd_el.find("patch")
                if patch_el is not None:
                    for hunk_el in patch_el.findall("hunk"):
                        old_el = hunk_el.find("old")
                        new_el = hunk_el.find("new")
                        old = old_el.text if old_el is not None and old_el.text is not None else ""
                        new = new_el.text if new_el is not None and new_el.text is not None else ""
                        hunks.append(Hunk(old=old, new=new))
                commands.append(Command(type="write", path=path, hunks=hunks))

            elif cmd_type == "evolve":
                commands.append(Command(type="evolve"))

    return AgentResponse(to_user=to_user, commands=commands, to_self=to_self)
