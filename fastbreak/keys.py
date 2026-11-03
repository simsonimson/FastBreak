"""Virtual-key constants and display names."""

VK_ESCAPE = 0x1B
VK_F8 = 0x77
VK_CONTROL, VK_LCONTROL, VK_RCONTROL = 0x11, 0xA2, 0xA3
VK_T = 0x54
VK_P = 0x50

DEFAULT_HOTKEY = VK_F8

# Keys FastBreak itself sends; they cannot be the hotkey.
RESERVED = frozenset({VK_CONTROL, VK_LCONTROL, VK_RCONTROL, VK_T, VK_P, 0x01})

_NAMES = {
    0x02: "Right Mouse", 0x04: "Middle Mouse", 0x05: "Mouse 4", 0x06: "Mouse 5",
    0x08: "Backspace", 0x09: "Tab", 0x0D: "Enter", 0x13: "Pause", 0x14: "Caps Lock",
    0x20: "Space", 0x21: "Page Up", 0x22: "Page Down", 0x23: "End", 0x24: "Home",
    0x25: "Left", 0x26: "Up", 0x27: "Right", 0x28: "Down", 0x2C: "Print",
    0x2D: "Insert", 0x2E: "Delete", 0x5B: "Left Win", 0x5C: "Right Win", 0x5D: "Menu",
    0x6A: "Num *", 0x6B: "Num +", 0x6D: "Num -", 0x6E: "Num .", 0x6F: "Num /",
    0x90: "Num Lock", 0x91: "Scroll Lock", 0xA0: "Left Shift", 0xA1: "Right Shift",
    0xA4: "Left Alt", 0xA5: "Right Alt",
}


def valid(vk: int) -> bool:
    return 0 < vk < 0xFF and vk not in RESERVED and vk != VK_ESCAPE


def name(vk: int) -> str:
    if vk in _NAMES:
        return _NAMES[vk]
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x6F}"
    if 0x60 <= vk <= 0x69:
        return f"Num {vk - 0x60}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    try:
        from .win32 import key_name_text
        text = key_name_text(vk)
    except Exception:
        text = ""
    return text or f"Key {vk:02X}"
