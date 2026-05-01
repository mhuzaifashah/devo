import json
import os
import uuid
from datetime import datetime, timezone

Meta = dict[str, object]
Message = dict[str, object]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


class Session:
    def __init__(self, base_dir: str) -> None:
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def list_sessions(self) -> list[Meta]:
        sessions: list[Meta] = []
        if not os.path.isdir(self.base_dir):
            return sessions

        for name in os.listdir(self.base_dir):
            meta_path = os.path.join(self.base_dir, name, "meta.json")
            if not os.path.isfile(meta_path):
                continue
            meta = self.meta_read(name)
            if meta:
                sessions.append(meta)

        sessions.sort(key=lambda item: str(item.get("last_used_at", "")), reverse=True)
        return sessions

    def create_session(
        self,
        provider: str,
        model: str,
        workspaces: list[tuple[str, str]],
    ) -> str:
        now = utc_iso()
        session_id = utc_now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        folder = self.path_get(session_id)
        os.makedirs(folder, exist_ok=True)
        meta: Meta = {
            "session_id": session_id,
            "created_at": now,
            "last_used_at": now,
            "provider": provider,
            "model": model,
            "workspaces": workspaces,
        }
        self.meta_write(session_id, meta)
        summary_path = os.path.join(folder, "summary.md")
        if not os.path.isfile(summary_path):
            with open(summary_path, "w", encoding="utf-8") as handle:
                handle.write("")
        return session_id

    def session_exists(self, session_id: str) -> bool:
        return os.path.isdir(self.path_get(session_id))

    def load_session(self, session_id: str) -> tuple[str, list[Message]]:
        summary = ""
        summary_path = os.path.join(self.path_get(session_id), "summary.md")
        if os.path.isfile(summary_path):
            with open(summary_path, "r", encoding="utf-8") as handle:
                summary = handle.read().strip()

        messages: list[Message] = []
        messages_path = os.path.join(self.path_get(session_id), "messages.jsonl")
        if not os.path.isfile(messages_path):
            return summary, messages

        with open(messages_path, "r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                item = self.message_load(text)
                if item:
                    messages.append(item)

        return summary, messages

    def append_messages(self, session_id: str, messages: list[Message]) -> None:
        if not messages:
            return
        messages_path = os.path.join(self.path_get(session_id), "messages.jsonl")
        with open(messages_path, "a", encoding="utf-8") as handle:
            for item in messages:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        self.touch_session(session_id)

    def write_summary(self, session_id: str, summary: str) -> None:
        summary_path = os.path.join(self.path_get(session_id), "summary.md")
        with open(summary_path, "w", encoding="utf-8") as handle:
            handle.write(summary or "")
        self.touch_session(session_id)

    def touch_session(self, session_id: str) -> None:
        meta = self.meta_read(session_id)
        if not meta:
            return
        meta["last_used_at"] = utc_iso()
        self.meta_write(session_id, meta)

    def path_get(self, session_id: str) -> str:
        return os.path.join(self.base_dir, session_id)

    def message_load(self, line: str) -> Message | None:
        try:
            value = json.loads(line)
        except Exception:
            return None
        if isinstance(value, dict):
            return value
        return None

    def meta_read(self, session_id: str) -> Meta | None:
        meta_path = os.path.join(self.path_get(session_id), "meta.json")
        if not os.path.isfile(meta_path):
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as handle:
                value = json.load(handle)
        except Exception:
            return None
        if isinstance(value, dict):
            return value
        return None

    def meta_write(self, session_id: str, meta: Meta) -> None:
        meta_path = os.path.join(self.path_get(session_id), "meta.json")
        with open(meta_path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, indent=2)


SessionStore = Session
