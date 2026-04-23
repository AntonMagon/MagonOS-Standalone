from __future__ import annotations

from pathlib import Path


def render_launch_agent(repo_root: Path, interval_seconds: int, label: str = "com.magonos.periodic-checks") -> str:
    repo_root = repo_root.resolve()
    stdout_path = repo_root / ".cache" / "launchd-periodic-checks.log"
    stderr_path = repo_root / ".cache" / "launchd-periodic-checks.err.log"
    shell_bin = "/bin/bash"
    wrapper = repo_root / "scripts" / "run_launchd_repo_python.sh"
    path_value = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    # RU: wrapper нужен именно здесь, потому что launchd запускает агент в урезанном окружении.
    # RU: LaunchAgent обязан звать wrapper через bash, а не через zsh, иначе repo bash-contract может умереть до самого periodic runner.
    # RU: LaunchAgent держим repo-aware: он всегда запускает именно versioned periodic-check script из текущего standalone repo.
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>{label}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>StartInterval</key>
    <integer>{interval_seconds}</integer>
    <key>WorkingDirectory</key>
    <string>{repo_root}</string>
    <key>ProgramArguments</key>
    <array>
      <string>{shell_bin}</string>
      <string>{wrapper}</string>
      <string>scripts/run_periodic_checks.py</string>
      <string>--mode</string>
      <string>launchd</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
      <key>PATH</key>
      <string>{path_value}</string>
      <key>PYTHONDONTWRITEBYTECODE</key>
      <string>1</string>
    </dict>
    <key>StandardOutPath</key>
    <string>{stdout_path}</string>
    <key>StandardErrorPath</key>
    <string>{stderr_path}</string>
  </dict>
</plist>
"""
