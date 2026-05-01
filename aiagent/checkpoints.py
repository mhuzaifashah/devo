import json
import os
import shutil
import uuid
from datetime import datetime, timezone

Meta = dict[str, object]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


class Checkpoint:
    def __init__(self, root_dir: str, enabled: bool = True, auto_rollback: bool = False) -> None:
        self.root_dir = root_dir
        self.enabled = enabled
        self.auto_rollback = auto_rollback
        if enabled:
            os.makedirs(self.root_dir, exist_ok=True)

    def path_get(self, checkpoint_id: str) -> str:
        return os.path.join(self.root_dir, checkpoint_id)

    def start(
        self,
        tool_name: str,
        args: dict[str, object],
        workspace_name: str,
        workdir: str,
    ) -> str | None:
        if not self.enabled:
            return None
        stamp = utc_now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"{stamp}_{uuid.uuid4().hex[:8]}"
        folder = self.path_get(checkpoint_id)
        os.makedirs(folder, exist_ok=True)
        meta: Meta = {
            "id": checkpoint_id,
            "tool": tool_name,
            "args": args,
            "workspace": workspace_name,
            "workdir": workdir,
            "status": "started",
            "started_at": utc_iso(),
            "files": [],
        }
        self.meta_write(checkpoint_id, meta)
        return checkpoint_id

    def snapshot_file(self, checkpoint_id: str | None, abs_path: str, rel_path: str) -> None:
        if not self.enabled or not checkpoint_id:
            return
        meta = self.meta_read(checkpoint_id)
        if not meta:
            return
        entry: Meta = {"path": rel_path, "existed": os.path.isfile(abs_path)}
        if entry["existed"]:
            target = os.path.join(self.path_get(checkpoint_id), "files", rel_path)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(abs_path, target)
            entry["snapshot"] = os.path.relpath(target, self.path_get(checkpoint_id))
        files = meta.get("files", [])
        if isinstance(files, list):
            files.append(entry)
            meta["files"] = files
        self.meta_write(checkpoint_id, meta)

    def finish(
        self,
        checkpoint_id: str | None,
        status: str,
        result: object | None = None,
        error: str | None = None,
    ) -> None:
        if not self.enabled or not checkpoint_id:
            return
        meta = self.meta_read(checkpoint_id)
        if not meta:
            return
        meta["status"] = status
        meta["finished_at"] = utc_iso()
        if result is not None:
            meta["result"] = result
        if error is not None:
            meta["error"] = error
        self.meta_write(checkpoint_id, meta)

    def list_checkpoints(self) -> list[Meta]:
        if not self.enabled:
            return []
        rows: list[Meta] = []
        for name in os.listdir(self.root_dir):
            meta = self.meta_read(name)
            if meta:
                rows.append(meta)
        rows.sort(key=lambda item: str(item.get("started_at", "")), reverse=True)
        return rows

    def rollback(self, checkpoint_id: str) -> str:
        if not self.enabled:
            return "Checkpoints are disabled."
        meta = self.meta_read(checkpoint_id)
        if not meta:
            return "Checkpoint not found."
        restored: list[str] = []
        moved: list[str] = []
        files = meta.get("files", [])
        if not isinstance(files, list):
            files = []
        for entry in files:
            if not isinstance(entry, dict):
                continue
            rel_path = str(entry.get("path", ""))
            target_path = os.path.join(str(meta["workdir"]), rel_path)
            snapshot = entry.get("snapshot")
            if snapshot:
                snapshot_path = os.path.join(self.path_get(checkpoint_id), str(snapshot))
                if os.path.isfile(snapshot_path):
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    shutil.copy2(snapshot_path, target_path)
                    restored.append(rel_path)
                continue
            if os.path.isfile(target_path):
                quarantine = os.path.join(self.path_get(checkpoint_id), "quarantine")
                moved_path = os.path.join(quarantine, rel_path)
                os.makedirs(os.path.dirname(moved_path), exist_ok=True)
                shutil.move(target_path, moved_path)
                moved.append(rel_path)
        return (
            f"Rollback complete. Restored: {restored or 'none'}. "
            f"Quarantined new files: {moved or 'none'}."
        )

    def meta_write(self, checkpoint_id: str, meta: Meta) -> None:
        meta_path = os.path.join(self.path_get(checkpoint_id), "meta.json")
        with open(meta_path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, indent=2)

    def meta_read(self, checkpoint_id: str) -> Meta | None:
        meta_path = os.path.join(self.path_get(checkpoint_id), "meta.json")
        if not os.path.isfile(meta_path):
            return None
        with open(meta_path, "r", encoding="utf-8") as handle:
            value = json.load(handle)
        if isinstance(value, dict):
            return value
        return None


CheckpointManager = Checkpoint
