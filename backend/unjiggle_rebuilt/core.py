from __future__ import annotations

import hashlib
import base64
import json
import math
import plistlib
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


APP_SUPPORT = Path.home() / "Library" / "Application Support" / "Liping"
TYPE_TAG = "__unjiggle_plist_type__"


def to_jsonable(value: Any) -> Any:
    """Encode plist-native values without losing data needed for restore/apply."""
    if isinstance(value, datetime):
        return {TYPE_TAG: "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {TYPE_TAG: "date", "value": value.isoformat()}
    if isinstance(value, bytes):
        return {TYPE_TAG: "bytes", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, plistlib.UID):
        return {TYPE_TAG: "uid", "value": value.data}
    if isinstance(value, dict):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"不支持的布局数据类型：{type(value).__name__}")


def from_jsonable(value: Any) -> Any:
    if isinstance(value, list):
        return [from_jsonable(item) for item in value]
    if isinstance(value, dict):
        kind = value.get(TYPE_TAG)
        if kind == "datetime":
            return datetime.fromisoformat(value["value"])
        if kind == "date":
            return date.fromisoformat(value["value"])
        if kind == "bytes":
            return base64.b64decode(value["value"])
        if kind == "uid":
            return plistlib.UID(value["value"])
        return {key: from_jsonable(item) for key, item in value.items()}
    return value


def load_json(path: Path) -> Any:
    return from_jsonable(json.loads(path.read_text(encoding="utf-8")))


def canonical(value: Any) -> bytes:
    return json.dumps(to_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(to_jsonable(value), ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


@dataclass(frozen=True)
class Icon:
    bundle_id: str
    name: str
    page: int
    position: int
    folder: str | None = None

    @property
    def category(self) -> str:
        text = f"{self.bundle_id} {self.name}".lower()
        categories = {
            "Social": ("social", "chat", "message", "instagram", "twitter", "wechat", "whatsapp"),
            "Work": ("work", "office", "slack", "notion", "docs", "mail", "calendar", "zoom"),
            "Media": ("music", "video", "photo", "camera", "podcast", "spotify", "youtube"),
            "Finance": ("bank", "wallet", "pay", "finance", "stock"),
            "Health": ("health", "fitness", "sleep", "workout"),
            "Travel": ("maps", "travel", "flight", "uber", "rail", "taxi"),
        }
        for category, needles in categories.items():
            if any(needle in text for needle in needles):
                return category
        return "Other"


def _identity(node: dict[str, Any]) -> tuple[str, str] | None:
    bundle_keys = ("displayIdentifier", "bundleIdentifier", "applicationIdentifier", "bundleID", "bundle-id", "identifier")
    name_keys = ("displayName", "name", "display-name", "title")
    bundle = next((node.get(key) for key in bundle_keys if isinstance(node.get(key), str)), None)
    name = next((node.get(key) for key in name_keys if isinstance(node.get(key), str)), None)
    if bundle:
        return bundle, name or bundle.rsplit(".", 1)[-1]
    return None


def flatten_icons(layout: Any) -> list[Icon]:
    """Read both SpringBoard format-v2 trees and our explicit demo representation."""
    icons: list[Icon] = []

    def walk(node: Any, page: int, folder: str | None = None) -> None:
        if isinstance(node, list):
            for position, child in enumerate(node):
                walk(child, page, folder)
            return
        if not isinstance(node, dict):
            return
        ident = _identity(node)
        nested = next((node.get(key) for key in ("iconLists", "icons", "children") if isinstance(node.get(key), list)), None)
        folder_name = node.get("displayName") or node.get("name") if nested is not None else folder
        if ident and nested is None:
            icons.append(Icon(ident[0], ident[1], page, len(icons), folder))
        if nested is not None:
            walk(nested, page, str(folder_name) if folder_name else folder)

    pages = layout
    if isinstance(layout, dict):
        pages = layout.get("pages") or layout.get("iconLists") or [layout]
    if not isinstance(pages, list):
        pages = [pages]
    for page_index, page in enumerate(pages):
        walk(page, page_index)
    return icons


def diagnose(layout: Any) -> dict[str, Any]:
    icons = flatten_icons(layout)
    page_count = max((icon.page for icon in icons), default=-1) + 1
    foldered = sum(icon.folder is not None for icon in icons)
    categories = Counter(icon.category for icon in icons)
    first_page = sum(icon.page == 0 for icon in icons)
    efficiency = max(0, 100 - max(0, page_count - 2) * 12 - max(0, len(icons) - 48) // 4)
    folders = min(100, round((foldered / max(1, len(icons))) * 150))
    focus = max(0, 100 - max(0, first_page - 20) * 4)
    balance = 100 if not categories else max(30, 100 - (max(categories.values()) - min(categories.values())) * 3)
    score = round(efficiency * .35 + folders * .2 + focus * .3 + balance * .15)
    if page_count >= 5:
        archetype = "收藏家"
    elif first_page > 22:
        archetype = "极繁主义者"
    elif foldered > len(icons) * .6:
        archetype = "图书管理员"
    else:
        archetype = "目标明确型"
    return {
        "score": score,
        "archetype": archetype,
        "summary": f"共 {len(icons)} 个应用，分布在 {page_count} 页。",
        "metrics": {"efficiency": efficiency, "foldering": folders, "focus": focus, "balance": balance},
        "counts": {"apps": len(icons), "pages": page_count, "foldered": foldered},
        "categories": dict(categories.most_common()),
        "recommendations": recommendations(icons, page_count),
    }


def recommendations(icons: list[Icon], page_count: int) -> list[str]:
    results: list[str] = []
    if page_count > 3:
        results.append("把低频应用归入分类文件夹，尽量把主屏幕控制在三页以内。")
    if sum(icon.page == 0 for icon in icons) > 20:
        results.append("第一页只保留每天使用的操作，偶尔使用的应用移到后页。")
    if sum(icon.folder is not None for icon in icons) < len(icons) // 4:
        results.append("把不常用的应用归入少量、名称清楚的文件夹。")
    if not results:
        results.append("当前布局已经比较紧凑，可以围绕一个明确目标继续精简第一页。")
    return results


def swipe_tax(layout: Any, daily_opens: int = 45) -> dict[str, Any]:
    icons = flatten_icons(layout)
    weighted_swipes = sum(icon.page + (1 if icon.folder else 0) for icon in icons)
    average = weighted_swipes / max(1, len(icons))
    daily = round(average * daily_opens, 1)
    yearly_minutes = round(daily * 365 * 0.42 / 60)
    worst = sorted(icons, key=lambda item: (item.page + bool(item.folder), item.name), reverse=True)[:5]
    return {
        "dailySwipes": daily,
        "yearlyMinutes": yearly_minutes,
        "averagePath": round(average, 2),
        "costliest": [{"name": icon.name, "swipes": icon.page + int(bool(icon.folder))} for icon in worst],
    }


def mirror(layout: Any) -> dict[str, Any]:
    report = diagnose(layout)
    category = next(iter(report["categories"]), "Other")
    category_name = {"Social": "社交", "Work": "工作", "Media": "影音", "Finance": "财务", "Health": "健康", "Travel": "出行", "Other": "综合"}.get(category, category)
    return {
        "headline": f"你的主屏幕首先照顾“{category_name}”，其余内容则在争夺注意力。",
        "body": (
            f"这个布局共有 {report['counts']['apps']} 个应用，分布在 {report['counts']['pages']} 页。"
            "真正值得关注的不是它看起来是否整齐，而是第一页能否在习惯替你做决定之前，"
            "先提醒你真正想做的事情。"
        ),
        "generatedBy": "local-rule-engine",
    }


def obituary(layout: Any) -> dict[str, Any]:
    tax = swipe_tax(layout)
    report = diagnose(layout)
    return {
        "title": "纪念那些无意识的滑动",
        "body": (
            f"这里躺着一个拥有 {report['counts']['apps']} 个应用的旧布局。手指经常造访，目标却常常缺席。"
            f"它每年大约消耗 {tax['yearlyMinutes']} 分钟在寻找和滑动上。"
            "愿新的布局更精简、更安静，也更容易撤销。"
        ),
        "generatedBy": "local-rule-engine",
    }


def make_demo_layout() -> list[list[dict[str, Any]]]:
    names = [
        ("Mail", "com.apple.mobilemail"), ("Calendar", "com.apple.mobilecal"),
        ("Maps", "com.apple.Maps"), ("Photos", "com.apple.mobileslideshow"),
        ("Camera", "com.apple.camera"), ("Music", "com.apple.Music"),
        ("Messages", "com.apple.MobileSMS"), ("Notes", "com.apple.mobilenotes"),
        ("Slack", "com.tinyspeck.chatlyio"), ("Notion", "notion.id"),
        ("YouTube", "com.google.ios.youtube"), ("Spotify", "com.spotify.client"),
        ("Health", "com.apple.Health"), ("Wallet", "com.apple.Passbook"),
        ("Weather", "com.apple.weather"), ("Books", "com.apple.iBooks"),
        ("Files", "com.apple.DocumentsApp"), ("Podcasts", "com.apple.podcasts"),
        ("Stocks", "com.apple.stocks"), ("FaceTime", "com.apple.facetime"),
        ("Reminders", "com.apple.reminders"), ("Clock", "com.apple.mobiletimer"),
        ("App Store", "com.apple.AppStore"), ("Settings", "com.apple.Preferences"),
        ("Translate", "com.apple.Translate"), ("Shortcuts", "com.apple.shortcuts"),
        ("Home", "com.apple.Home"), ("Fitness", "com.apple.Fitness"),
    ]
    pages = []
    for start in range(0, len(names), 12):
        pages.append([{"displayName": name, "bundleIdentifier": bundle} for name, bundle in names[start:start + 12]])
    return pages


def _top_level_pages(layout: Any) -> list[list[dict[str, Any]]]:
    pages = layout.get("pages") if isinstance(layout, dict) else layout
    if not isinstance(pages, list) or not all(isinstance(page, list) for page in pages):
        raise ValueError("Unsupported icon-state shape; expected a page array")
    if not all(isinstance(item, dict) for page in pages for item in page):
        raise ValueError("Unsupported icon-state item; refusing to create a writable plan")
    return pages


def _item_sort_key(item: dict[str, Any], priority: dict[str, int]) -> tuple[int, str]:
    found: list[tuple[str, str]] = []

    def visit(node: Any) -> None:
        if found:
            return
        if isinstance(node, dict):
            ident = _identity(node)
            if ident:
                found.append(ident)
                return
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(item)
    if not found:
        return (99, str(item.get("displayName", "Widget")))
    sample = Icon(found[0][0], found[0][1], 0, 0)
    return (priority.get(sample.category, priority.get("Other", 50)), sample.name.lower())


def plan(layout: Any, preset: str) -> dict[str, Any]:
    pages = _top_level_pages(layout)
    preset = preset.lower()
    if preset not in {"focus", "relax", "minimal", "beautiful"}:
        raise ValueError(f"Unknown preset: {preset}")
    if preset == "focus":
        priority = {"Work": 0, "Other": 1, "Health": 2, "Travel": 3, "Finance": 4, "Media": 5, "Social": 6}
        page_size = 16
    elif preset == "relax":
        priority = {"Health": 0, "Media": 1, "Social": 2, "Other": 3, "Travel": 4, "Work": 5, "Finance": 6}
        page_size = 16
    elif preset == "minimal":
        priority = {"Other": 0, "Work": 1, "Health": 2, "Travel": 3, "Finance": 4, "Media": 5, "Social": 6}
        page_size = 20
    else:
        priority = {"Media": 0, "Social": 1, "Health": 2, "Travel": 3, "Work": 4, "Finance": 5, "Other": 6}
        page_size = 12
    ordered = sorted((item for page in pages for item in page), key=lambda item: _item_sort_key(item, priority))
    proposed = [ordered[start:start + page_size] for start in range(0, len(ordered), page_size)]
    plan_id = digest({"source": digest(layout), "preset": preset, "proposed": proposed})[:16]
    return {
        "id": plan_id,
        "preset": {"focus": "专注", "relax": "放松", "minimal": "极简", "beautiful": "美观"}[preset],
        "sourceHash": digest(layout),
        "sourceApps": sorted(icon.bundle_id for icon in flatten_icons(layout)),
        "proposed": proposed,
        "before": diagnose(layout),
        "after": diagnose(proposed),
        "warning": "这里只生成预览。真正应用前会重新检查设备，并先创建备份。",
    }


def backup_record(device: dict[str, Any], layout: Any, reason: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    backup_id = f"{now.strftime('%Y%m%dT%H%M%SZ')}-{digest(layout)[:10]}"
    record = {
        "schema": 1,
        "id": backup_id,
        "createdAt": now.isoformat(),
        "reason": reason,
        "device": device,
        "layoutHash": digest(layout),
        "layout": layout,
    }
    atomic_json(APP_SUPPORT / "backups" / f"{backup_id}.json", record)
    return record


def list_backups() -> list[dict[str, Any]]:
    records = []
    for path in sorted((APP_SUPPORT / "backups").glob("*.json"), reverse=True):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            records.append({key: value[key] for key in ("id", "createdAt", "reason", "layoutHash")})
        except (OSError, ValueError, KeyError):
            continue
    return records
