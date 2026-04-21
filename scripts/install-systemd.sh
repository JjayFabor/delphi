#!/usr/bin/env bash
# Install and enable all systemd user units for claude-command-center.
# Safe to re-run — idempotent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"

echo "Installing systemd user units..."
mkdir -p "$SYSTEMD_USER_DIR"

UNITS=(
    claude-main.service
    claude-memory-dreaming.service
    claude-memory-dreaming.timer
    claude-backup.service
    claude-backup.timer
)

for unit in "${UNITS[@]}"; do
    cp "$ROOT/systemd/$unit" "$SYSTEMD_USER_DIR/$unit"
    echo "  Copied $unit"
done

# Make scripts executable
chmod +x "$ROOT/scripts/backup.sh" "$ROOT/scripts/update.sh"

systemctl --user daemon-reload
echo "  Reloaded systemd daemon"

# Enable lingering so units survive user logout (important for WSL / headless servers)
if command -v loginctl &>/dev/null; then
    loginctl enable-linger "$USER" 2>/dev/null && echo "  Enabled linger for $USER" || true
fi

echo ""
echo "Enabling units..."
systemctl --user enable --now claude-main.service
echo "  claude-main.service — enabled + started"

systemctl --user enable --now claude-memory-dreaming.timer
echo "  claude-memory-dreaming.timer — enabled"

systemctl --user enable --now claude-backup.timer
echo "  claude-backup.timer — enabled"

echo ""
echo "Done. Useful commands:"
echo "  systemctl --user status claude-main.service"
echo "  journalctl --user -u claude-main.service -f"
echo "  systemctl --user restart claude-main.service"
echo "  systemctl --user list-timers"
