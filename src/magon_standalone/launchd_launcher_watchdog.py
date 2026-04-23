from __future__ import annotations

from pathlib import Path


def render_launcher_watchdog_agent(
    repo_root: Path,
    interval_seconds: int,
    label: str = "com.magonos.launcher-watchdog",
    launchd_root: Path | None = None,
    program_path: Path | None = None,
) -> str:
    repo_root = repo_root.resolve()
    launchd_root = (launchd_root or (Path.home() / ".codex" / "launchd-support" / label)).expanduser().resolve()
    program_path = (program_path or (launchd_root / "run-agent.sh")).expanduser().resolve()
    stdout_path = launchd_root / "stdout.log"
    stderr_path = launchd_root / "stderr.log"
    shell_bin = "/bin/bash"
    path_value = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    # RU: LaunchAgent живёт вне Desktop repo, чтобы macOS launchd не упирался в защищённый WorkingDirectory/log path под TCC.
    # RU: Helper script держим в home-support path и зовём через bash, а уже он переводит выполнение в versioned standalone repo.
    # RU: Launcher watchdog всё равно обязан смотреть именно в текущий standalone repo и поднимать тот же Start_Platform.command,
    # а не случайный внешний shell script из пользовательского окружения.
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
    <string>{launchd_root}</string>
    <key>ProgramArguments</key>
    <array>
      <string>{shell_bin}</string>
      <string>{program_path}</string>
      <string>scripts/run_launcher_watchdog.py</string>
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
