from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .core import APP_SUPPORT, atomic_json, backup_record, diagnose, digest, flatten_icons, list_backups, load_json, make_demo_layout, mirror, obituary, plan, swipe_tax, to_jsonable
from .device import DeviceUnavailable, devices, read_layout, write_layout


async def acquire(demo: bool, udid: str | None) -> tuple[dict[str, Any], Any]:
    if demo:
        return {"udid": "DEMO-DEVICE", "name": "演示 iPhone", "productVersion": "演示", "isDemo": True}, make_demo_layout()
    return await read_layout(udid)


async def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "version":
        return {"version": __version__}
    if args.command == "status":
        if args.demo:
            found = [{"udid": "DEMO-DEVICE", "name": "演示 iPhone", "isDemo": True, "isUSB": True}]
        else:
            found = await devices()
        return {"connected": bool(found), "devices": found, "backend": __version__}
    if args.command == "backups":
        return {"backups": list_backups()}
    device, layout = await acquire(args.demo, args.udid)
    if args.command == "scan":
        return {"device": device, "layoutHash": digest(layout), "report": diagnose(layout), "layout": layout}
    if args.command == "diagnose":
        return {"device": device, "layoutHash": digest(layout), "report": diagnose(layout)}
    if args.command == "swipe-tax":
        return {"device": device, "layoutHash": digest(layout), "report": swipe_tax(layout, args.daily_opens)}
    if args.command == "mirror":
        return {"device": device, "layoutHash": digest(layout), "report": mirror(layout)}
    if args.command == "obituary":
        return {"device": device, "layoutHash": digest(layout), "report": obituary(layout)}
    if args.command == "preview":
        value = plan(layout, args.preset)
        value["device"] = device
        atomic_json(APP_SUPPORT / "plans" / f"{value['id']}.json", value)
        return value
    if args.command == "backup":
        return {"backup": backup_record(device, layout, "manual")}
    if args.command == "apply":
        if args.demo:
            raise ValueError("演示模式不能写入设备")
        if args.confirm != "APPLY":
            raise ValueError("应用布局需要明确确认")
        path = APP_SUPPORT / "plans" / f"{args.plan}.json"
        value = load_json(path)
        if value["device"]["udid"] != device["udid"] or value["sourceHash"] != digest(layout):
            raise ValueError("设备或布局在预览后发生了变化，请重新扫描并生成预览")
        if value["sourceApps"] != sorted(icon.bundle_id for icon in flatten_icons(value["proposed"])):
            raise ValueError("预览方案中的应用集合与原布局不一致，已拒绝写入")
        backup = backup_record(device, layout, f"before-plan-{args.plan}")
        await write_layout(device["udid"], value["proposed"])
        return {"applied": True, "plan": args.plan, "backup": backup["id"]}
    if args.command == "restore":
        if args.demo:
            raise ValueError("演示模式不能恢复设备")
        if args.confirm != "RESTORE":
            raise ValueError("恢复布局需要明确确认")
        value = load_json(APP_SUPPORT / "backups" / f"{args.backup}.json")
        if value["device"]["udid"] != device["udid"]:
            raise ValueError("这个备份属于另一台设备")
        safety = backup_record(device, layout, f"before-restore-{args.backup}")
        await write_layout(device["udid"], value["layout"])
        return {"restored": True, "backup": args.backup, "safetyBackup": safety["id"]}
    raise ValueError(f"Unsupported command: {args.command}")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="unjiggle-backend")
    value.add_argument("command", choices=("version", "status", "scan", "diagnose", "swipe-tax", "mirror", "obituary", "preview", "backup", "backups", "apply", "restore"))
    value.add_argument("--demo", action="store_true")
    value.add_argument("--udid")
    value.add_argument("--daily-opens", type=int, default=45)
    value.add_argument("--preset", default="focus")
    value.add_argument("--plan")
    value.add_argument("--backup")
    value.add_argument("--confirm")
    return value


def main() -> None:
    args = parser().parse_args()
    try:
        result = asyncio.run(execute(args))
        print(json.dumps(to_jsonable({"ok": True, **result}), ensure_ascii=False))
    except (DeviceUnavailable, ValueError, OSError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "type": type(exc).__name__}, ensure_ascii=False))
        raise SystemExit(2)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "type": type(exc).__name__}, ensure_ascii=False))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
