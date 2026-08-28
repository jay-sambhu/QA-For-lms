"""
Centralized device configuration manager for Playwright device emulation.
"""

from typing import Dict, Any


class DeviceConfigManager:
    """Provides centralized Playwright device definitions and descriptors."""

    DEFAULT_DESKTOP = {
        "name": "Desktop Chrome",
        "viewport": {"width": 1366, "height": 768},
        "is_mobile": False,
        "device_scale_factor": 1.0,
    }

    @classmethod
    def get_devices_config(cls, playwright_instance=None) -> Dict[str, Dict[str, Any]]:
        """
        Build Playwright context kwargs for supported devices.
        
        Devices supported:
        - Desktop Chrome (1366x768)
        - iPhone 13 (Playwright device profile)
        - iPad (gen 7) (Playwright device profile)
        """
        desktop_kwargs = {
            "viewport": {"width": 1366, "height": 768},
            "is_mobile": False,
            "has_touch": False,
            "device_scale_factor": 1.0,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        if playwright_instance and hasattr(playwright_instance, "devices"):
            devices = playwright_instance.devices
            iphone_kwargs = dict(devices.get("iPhone 13", {
                "viewport": {"width": 390, "height": 844},
                "is_mobile": True,
                "has_touch": True,
                "device_scale_factor": 3.0,
            }))
            ipad_kwargs = dict(devices.get("iPad (gen 7)", {
                "viewport": {"width": 810, "height": 1080},
                "is_mobile": True,
                "has_touch": True,
                "device_scale_factor": 2.0,
            }))
        else:
            iphone_kwargs = {
                "viewport": {"width": 390, "height": 844},
                "is_mobile": True,
                "has_touch": True,
                "device_scale_factor": 3.0,
            }
            ipad_kwargs = {
                "viewport": {"width": 810, "height": 1080},
                "is_mobile": True,
                "has_touch": True,
                "device_scale_factor": 2.0,
            }

        return {
            "Desktop Chrome": desktop_kwargs,
            "iPhone 13": iphone_kwargs,
            "iPad (gen 7)": ipad_kwargs,
        }

    @classmethod
    def get_viewport_dimensions(cls, dev_name: str, dev_config: Dict[str, Any]) -> Dict[str, int]:
        """Extract viewport width and height safely."""
        vp = dev_config.get("viewport") or {}
        return {
            "width": vp.get("width", 1366 if "Desktop" in dev_name else 390),
            "height": vp.get("height", 768 if "Desktop" in dev_name else 844),
        }
