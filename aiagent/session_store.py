import json
import os
import uuid
from datetime import datetime


class SessionStore:
    def __init__(self, base_dir):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def list_sessions(self):
        sessions = []
        if not os.path.isdir(self.base_dir):
            return sessions
        for name in os.listdir(self.base_dir):
            meta_path = os.path.join(self.base_dir, name, "meta.json")
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    sessions.append(meta)
                except Exception:
                    continue
        sessions.sort(key=lambda x: x.get("last_used_at", ""), reverse=True)
        return sessions

    def create_session(self, provider, model, workspaces):
        session_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        session_dir = self._session_dir(session_id)
        os.makedirs(session_dir, exist_ok=True)
        meta = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_used_at": datetime.utcnow().isoformat() + "Z",
            "provider": provider,
            "model": model,
            "workspaces": workspaces,
        }
        self._write_meta(session_id, meta)
        summary_path = os.path.join(session_dir, "summary.md")
        if not os.path.isfile(summary_path):
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write("")
        return session_id

    def session_exists(self, session_id):
        return os.path.isdir(self._session_dir(session_id))

    def load_session(self, session_id):
        summary = ""
        summary_path = os.path.join(self._session_dir(session_id), "summary.md")
        if os.path.isfile(summary_path):
            with open(summary_path, "r", encoding="utf-8") as f:
                summary = f.read().strip()
        messages = []
        messages_path = os.path.join(self._session_dir(session_id), "messages.jsonl")
        if os.path.isfile(messages_path):
            with open(messages_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        messages.append(json.loads(line))
                    except Exception:
                        continue
        return summary, messages

    def append_messages(self, session_id, messages):
        if not messages:
            return
        messages_path = os.path.join(self._session_dir(session_id), "messages.jsonl")
        with open(messages_path, "a", encoding="utf-8") as f:
            for msg in messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self.touch_session(session_id)

    def write_summary(self, session_id, summary):
        summary_path = os.path.join(self._session_dir(session_id), "summary.md")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary or "")
        self.touch_session(session_id)

    def touch_session(self, session_id):
        meta = self._read_meta(session_id)
        if not meta:
            return
        meta["last_used_at"] = datetime.utcnow().isoformat() + "Z"
        self._write_meta(session_id, meta)

    def _session_dir(self, session_id):
        return os.path.join(self.base_dir, session_id)

    def _read_meta(self, session_id):
        meta_path = os.path.join(self._session_dir(session_id), "meta.json")
        if not os.path.isfile(meta_path):
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def _write_meta(self, session_id, meta):
        meta_path = os.path.join(self._session_dir(session_id), "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
