from __future__ import annotations

from pathlib import Path


def render_launch_agent(repo_root: Path, interval_seconds: int, label: str = "com.magonos.periodic-checks") -> str:
    repo_root = repo_root.resolve()
    stdout_path = repo_root / ".cache" / "launchd-periodic-checks.log"
    stderr_path = repo_root / ".cache" / "launchd-periodic-checks.err.log"
    python_bin = repo_root / ".venv" / "bin" / "python"
    runner = repo_root / "scripts" / "run_periodic_checks.py"
    path_value = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

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
      <string>{python_bin}</string>
      <string>{runner}</string>
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
