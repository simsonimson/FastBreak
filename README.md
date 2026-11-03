<p align="center"><img src="assets/icon-256.png" width="96" alt="FastBreak"></p>

<h1 align="center">FastBreak</h1>

Hold a hotkey → `CTRL+T`, then `P` is held.
Release it → `P` is released, then `CTRL+T` again.

## Download

Get `FastBreak.exe` from [Releases](../../releases/latest) and run it. No installation, no Python needed.

## Usage

1. **Change** → press any key or mouse button (Esc cancels).
2. **START**.
3. Hold the hotkey in any application.

The hotkey is saved automatically. If the target application runs as administrator, run FastBreak as administrator too.

## Build from source

```bat
pip install -r requirements.txt pyinstaller
python main.py
pyinstaller --noconfirm --clean FastBreak.spec
```

Pushing a tag like `v1.0.0` builds `FastBreak.exe` and publishes it as a GitHub release.

## License

MIT
