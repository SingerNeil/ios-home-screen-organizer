from __future__ import annotations

import asyncio
from typing import Any


class DeviceUnavailable(RuntimeError):
    pass


async def devices(attempts: int = 4, delay: float = 0.35) -> list[dict[str, Any]]:
    try:
        from pymobiledevice3.usbmux import list_devices
    except ImportError as exc:
        raise DeviceUnavailable("pymobiledevice3 is not installed; run make bootstrap") from exc
    found = []
    for attempt in range(attempts):
        found = await list_devices()
        if found or attempt == attempts - 1:
            break
        await asyncio.sleep(delay)
    return [
        {"udid": item.serial, "connectionType": item.connection_type, "isUSB": item.is_usb}
        for item in found
    ]


async def read_layout(udid: str | None = None) -> tuple[dict[str, Any], Any]:
    try:
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.springboard import SpringBoardServicesService
    except ImportError as exc:
        raise DeviceUnavailable("pymobiledevice3 is not installed; run make bootstrap") from exc
    candidates = await devices()
    chosen = next((item for item in candidates if udid is None or item["udid"] == udid), None)
    if chosen is None:
        raise DeviceUnavailable("没有检测到已配对的 USB iPhone 或 iPad。请保持设备解锁、确认“信任此电脑”，并检查数据线。")
    lockdown = None
    last_error = None
    for attempt in range(3):
        try:
            lockdown = await create_using_usbmux(serial=chosen["udid"], connection_type="USB")
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(0.5)
    if lockdown is None:
        raise DeviceUnavailable(f"设备已出现但无法建立配对会话：{last_error}")
    try:
        chosen.update({
            "name": getattr(lockdown, "display_name", None) or getattr(lockdown, "product_type", None) or "iOS 设备",
            "productType": getattr(lockdown, "product_type", None),
            "productVersion": getattr(lockdown, "product_version", None),
        })
        async with SpringBoardServicesService(lockdown) as service:
            return chosen, await service.get_icon_state(format_version="2")
    finally:
        await lockdown.close()


async def write_layout(udid: str, layout: Any) -> None:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.springboard import SpringBoardServicesService

    lockdown = await create_using_usbmux(serial=udid, connection_type="USB")
    try:
        async with SpringBoardServicesService(lockdown) as service:
            await service.set_icon_state(layout)
    finally:
        await lockdown.close()
