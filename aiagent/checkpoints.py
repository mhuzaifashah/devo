import json
import os
import shutil
import uuid
from datetime import datetime


class CheckpointManager:
    def __init__(self, root_dir, enabled=True, auto_rollback=False):
        self.root_dir = root_dir
        self.enabled = enabled
        self.auto_rollback = auto_rollback
        if self.enabled:
            os.makedirs(self.root_dir, exist_ok=True)

    def _checkpoint_dir(self, checkpoint_id):
        return os.path.join(self.root_dir, checkpoint_id)

    def start(self, tool_name, args, workspace_name, workdir):
        if not self.enabled:
            return None
        checkpoint_id = f"{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        checkpoint_dir = self._checkpoint_dir(checkpoint_id)
        os.makedirs(checkpoint_dir, exist_ok=True)
        meta = {
            "id": checkpoint_id,
            "tool": tool_name,
            "args": args,
            "workspace": workspace_name,
            "workdir": workdir,
            "status": "started",
            "started_at": datetime.utcnow().isoformat() + "Z",
            "files": [],
        }
        self._write_meta(checkpoint_id, meta)
        return checkpoint_id

    def snapshot_file(self, checkpoint_id, abs_path, rel_path):
        if not self.enabled or not checkpoint_id:
            return
        meta = self._read_meta(checkpoint_id)
        entry = {"path": rel_path, "existed": os.path.isfile(abs_path)}
        if entry["existed"]:
            target = os.path.join(self._checkpoint_dir(checkpoint_id), "files", rel_path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(abs_path, target)
            entry["snapshot"] = os.path.relpath(target, self._checkpoint_dir(checkpoint_id))
        meta["files"].append(entry)
        self._write_meta(checkpoint_id, meta)

    def finish(self, checkpoint_id, status, result=None, error=None):
        if not self.enabled or not checkpoint_id:
            return
        meta = self._read_meta(checkpoint_id)
        meta["status"] = status
        meta["finished_at"] = datetime.utcnow().isoformat() + "Z"
        if result is not None:
            meta["result"] = result
        if error is not None:
            meta["error"] = error
        self._write_meta(checkpoint_id, meta)

    def list_checkpoints(self):
        if not self.enabled:
            return []
        entries = []
        for name in os.listdir(self.root_dir):
            meta_path = os.path.join(self.root_dir, name, "meta.json")
            if os.path.isfile(meta_path):
                entries.append(self._read_meta(name))
        entries.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        return entries

    def rollback(self, checkpoint_id):
        if not self.enabled:
            return "Checkpoints are disabled."
        meta = self._read_meta(checkpoint_id)
        restored = []
        moved = []
        for entry in meta.get("files", []):
            rel_path = entry["path"]
            target_path = os.path.join(meta["workdir"], rel_path)
            if entry.get("snapshot"):
                snapshot_path = os.path.join(
                    self._checkpoint_dir(checkpoint_id), entry["snapshot"]
                )
                if os.path.isfile(snapshot_path):
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(snapshot_path, target_path)
                    restored.append(rel_path)
            else:
                if os.path.isfile(target_path):
                    quarantine_dir = os.path.join(
                        self._checkpoint_dir(checkpoint_id), "quarantine"
                    )
                    os.makedirs(os.path.dirname(os.path.join(quarantine_dir, rel_path)), exist_ok=True)
                    shutil.move(target_path, os.path.join(quarantine_dir, rel_path))
                    moved.append(rel_path)
        return (
            f"Rollback complete. Restored: {restored or 'none'}. "
            f"Quarantined new files: {moved or 'none'}."
        )

    def _write_meta(self, checkpoint_id, meta):
        meta_path = os.path.join(self._checkpoint_dir(checkpoint_id), "meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

    def _read_meta(self, checkpoint_id):
        meta_path = os.path.join(self._checkpoint_dir(checkpoint_id), "meta.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
