# Linux Flatpak sandbox and helper limits (HZ-050)

Source decision: `spikes/D5.md` (Linux Flatpak row). Helper design: `helper` D2 (polkit + `pkexec`).

## Problem

Flatpak apps run in a sandbox. Host polkit agents and absolute `pkexec` paths for a host-installed helper are **not** freely available to the sandboxed app. Privileged Hertzline actions that need `hertzline-helper` therefore cannot assume the same path as AppImage / deb / rpm.

## Chosen policy (v1)

1. **Preferred:** Install the privileged helper on the **host** (deb/rpm/AUR or a documented companion package) and keep Flatpak for the unprivileged UI when that path is productized later.
2. **Inside Flatpak alone:** Any action that requires elevation reports **not-possible** with an explanation that points to the host helper / native package. Never fake success.
3. **finish-args:** The draft manifest requests only what Tauri needs for a window (Wayland / X11 fallback, DRI, IPC). It does **not** request `--talk-name=org.freedesktop.PolicyKit1` or host filesystem write for helper install. Expanding permissions needs a deliberate security review (HZ-055).

## Manifest draft notes

File: `flatpak/org.hertzline.Hertzline.yml`

- Builds from a release `.deb` (Tauri Flathub guide pattern).
- App ID: `org.hertzline.Hertzline`.
- Runtime: `org.gnome.Platform` / `org.gnome.Sdk` version **47** (stable Flathub runtime at authoring time; re-verify before Flathub PR -- Tauri docs also mention newer GNOME runtimes).
- No Flathub submission without owner approval.

## polkit policy on host packages

deb / rpm / AUR install `org.hertzline.helper.policy` to `/usr/share/polkit-1/actions/` with `HELPER_INSTALL_PATH` replaced by the real helper path (default `/usr/bin/hertzline-helper`). Flatpak does not ship that policy into the sandbox as a substitute for host elevation.

## Verification expectations

| Claim | Evidence |
|---|---|
| AppImage / deb / rpm can use helper | Host binary + polkit policy present; D2 allow-list |
| Flatpak privileged apply | not-possible unless host helper path is documented and implemented |
| Uninstall restore in Flatpak | Host helper / native package; sandbox uninstall alone is insufficient |
