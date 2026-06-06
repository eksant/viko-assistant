import platform
import subprocess
import sys
from pathlib import Path


def _get_shell() -> tuple[str, list[str]]:
    os_name = platform.system().lower()
    if os_name == "windows":
        return "windows", ["cmd.exe", "/c"]
    elif os_name == "darwin":
        return "mac", ["/bin/zsh", "-c"]
    else:
        return "linux", ["/bin/bash", "-c"]


def _interpret_task(task: str) -> str:
    try:
        from viko.client import client
        os_name, _ = _get_shell()
        result = client.chat(
            f"Convert this natural language task to a shell command for {os_name}.\n"
            f"Return ONLY the shell command, no explanation, no markdown.\n\n"
            f"Task: {task}",
            system="You are a shell command expert. Return only the raw command string."
        )
        return result.strip().strip("`")
    except Exception as e:
        print(f"[CmdControl] LLM interpretation failed: {e}")
        return task


def cmd_control(parameters: dict, player=None) -> str:
    task    = parameters.get("task", "").strip()
    visible = parameters.get("visible", False)

    if not task:
        return "No task specified."

    os_name, shell_prefix = _get_shell()

    is_natural = any(c in task for c in [" ", "open", "run", "launch", "show", "create", "delete"])
    command = _interpret_task(task) if is_natural else task

    print(f"[CmdControl] Running: {command}")

    try:
        if visible and os_name == "windows":
            subprocess.Popen(
                f'start cmd.exe /k "{command}"',
                shell=True
            )
            return f"Opened terminal with: {command}"
        elif visible and os_name == "mac":
            apple_script = f'tell application "Terminal" to do script "{command}"'
            subprocess.Popen(["osascript", "-e", apple_script])
            return f"Opened terminal with: {command}"
        elif visible and os_name == "linux":
            for term in ["gnome-terminal", "xterm", "konsole"]:
                try:
                    subprocess.Popen([term, "--", "bash", "-c", f"{command}; read -p 'Press Enter to close...'"])
                    return f"Opened terminal with: {command}"
                except FileNotFoundError:
                    continue
            return "No terminal emulator found."
        else:
            result = subprocess.run(
                shell_prefix + [command],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(Path.home())
            )
            output = result.stdout.strip()
            error  = result.stderr.strip()

            if result.returncode == 0:
                return output if output else "Command completed."
            else:
                return f"Command failed: {error[:300]}" if error else "Command failed."

    except subprocess.TimeoutExpired:
        return "Command timed out after 30 seconds."
    except Exception as e:
        return f"Error running command: {e}"
