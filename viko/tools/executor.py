import asyncio
import threading
import traceback

from google.genai import types

from viko.core.memory import update_memory
from viko.skills.file_processor    import file_processor
from viko.skills.flight_finder     import flight_finder
from viko.skills.open_app          import open_app
from viko.skills.weather_report    import weather_action
from viko.skills.send_message      import send_message
from viko.skills.reminder          import reminder
from viko.skills.computer_settings import computer_settings
from viko.skills.screen_processor  import screen_process
from viko.skills.youtube_video     import youtube_video
from viko.skills.desktop           import desktop_control
from viko.skills.browser_control   import browser_control
from viko.skills.file_controller   import file_controller
from viko.skills.code_helper       import code_helper
from viko.skills.dev_agent         import dev_agent
from viko.skills.web_search        import web_search as web_search_action
from viko.skills.computer_control  import computer_control
from viko.skills.cmd_control       import cmd_control
from viko.skills.browser_tool import (
    navigate_browser, render_content,
    take_screenshot as browser_screenshot,
    get_page_content, browser_interact, visual_control,
)
from viko.skills.self_update import self_update

_TOOL_STATE = {
    "code_helper":      "CODING",
    "dev_agent":        "CODING",
    "self_update":      "CODING",
    "agent_task":       "WORKING",
    "file_controller":  "WORKING",
    "cmd_control":      "WORKING",
    "desktop_control":  "WORKING",
    "computer_control": "WORKING",
    "computer_settings":"WORKING",
    "browser_control":  "WORKING",
    "web_search":       "WORKING",
    "flight_finder":    "WORKING",
    "file_processor":   "WORKING",
    "youtube_video":    "WORKING",
    "send_message":     "WORKING",
    "screen_process":   "WORKING",
    "navigate_browser": "WORKING",
    "render_content":   "WORKING",
    "browser_interact": "WORKING",
    "visual_control":   "WORKING",
}

_ACT_LABEL = {
    "web_search":       "🔍 Mencari di internet…",
    "weather_report":   "🌦️ Cek cuaca…",
    "navigate_browser": "🌐 Membuka halaman…",
    "browser_interact": "🖱️ Mengoperasikan halaman…",
    "get_page_content": "📄 Membaca halaman…",
    "screen_process":   "👁️ Menganalisa layar…",
    "youtube_video":    "▶️ Membuka YouTube…",
    "send_message":     "✉️ Mengirim pesan…",
    "flight_finder":    "✈️ Mencari penerbangan…",
    "agent_task":       "🛠️ Mengerjakan tugas…",
    "code_helper":      "💻 Menulis kode…",
    "dev_agent":        "💻 Dev agent bekerja…",
}


async def execute_tool(fc, *, ui, speak, speak_error) -> types.FunctionResponse:
    name = fc.name
    args = dict(fc.args or {})

    print(f"[Viko] {name}  {args}")
    ui.set_state(_TOOL_STATE.get(name, "THINKING"))

    if name not in ("save_memory", "shutdown_viko"):
        ui.write_log(f"SYS: {_ACT_LABEL.get(name, f'⚙️ {name}…')}")

    if name == "save_memory":
        category = args.get("category", "notes")
        key      = args.get("key", "")
        value    = args.get("value", "")
        if key and value:
            update_memory({category: {key: {"value": value}}})
            print(f"[Memory] save_memory: {category}/{key} = {value}")
        if not ui.muted:
            ui.set_state("LISTENING")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": "ok", "silent": True}
        )

    loop   = asyncio.get_event_loop()
    result = "Done."

    try:
        if name == "open_app":
            r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=ui))
            result = r or f"Opened {args.get('app_name')}."

        elif name == "weather_report":
            r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=ui))
            result = r or "Weather delivered."

        elif name == "browser_control":
            r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=ui))
            result = r or "Done."

        elif name == "file_controller":
            r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=ui))
            result = r or "Done."

        elif name == "send_message":
            r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=ui, session_memory=None))
            result = r or f"Message sent to {args.get('receiver')}."

        elif name == "reminder":
            r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=ui))
            result = r or "Reminder set."

        elif name == "youtube_video":
            r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=ui))
            result = r or "Done."

        elif name == "file_processor":
            if not args.get("file_path") and ui.current_file:
                args["file_path"] = ui.current_file
            r = await loop.run_in_executor(
                None,
                lambda: file_processor(parameters=args, player=ui, speak=speak)
            )
            result = r or "Done."

        elif name == "screen_process":
            threading.Thread(
                target=screen_process,
                kwargs={"parameters": args, "response": None,
                        "player": ui, "session_memory": None},
                daemon=True
            ).start()
            result = "Vision module activated. Stay completely silent — vision module will speak directly."

        elif name == "computer_settings":
            r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=ui))
            result = r or "Done."

        elif name == "desktop_control":
            r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=ui))
            result = r or "Done."

        elif name == "code_helper":
            r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=ui, speak=speak))
            result = r or "Done."

        elif name == "dev_agent":
            r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=ui, speak=speak))
            result = r or "Done."

        elif name == "cmd_control":
            r = await loop.run_in_executor(None, lambda: cmd_control(parameters=args, player=ui))
            result = r or "Done."

        elif name == "agent_task":
            from viko.agent.queue import get_queue, TaskPriority
            priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
            priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
            task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=speak)
            result   = f"Task started (ID: {task_id})."

        elif name == "web_search":
            r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=ui))
            result = r or "Done."

        elif name == "computer_control":
            r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=ui))
            result = r or "Done."

        elif name == "flight_finder":
            r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=ui))
            result = r or "Done."

        elif name == "navigate_browser":
            r = await loop.run_in_executor(None, lambda: navigate_browser(parameters=args, player=ui))
            result = r or "Done."

        elif name == "render_content":
            r = await loop.run_in_executor(None, lambda: render_content(parameters=args, player=ui))
            result = r or "Done."

        elif name == "browser_screenshot":
            r = await loop.run_in_executor(None, lambda: browser_screenshot(parameters=args, player=ui))
            result = r or "Done."

        elif name == "get_page_content":
            r = await loop.run_in_executor(None, lambda: get_page_content(parameters=args, player=ui))
            result = r or "(kosong)"

        elif name == "browser_interact":
            r = await loop.run_in_executor(None, lambda: browser_interact(parameters=args, player=ui))
            result = r or "Done."

        elif name == "visual_control":
            r = await loop.run_in_executor(None, lambda: visual_control(parameters=args, player=ui))
            result = r or "Done."

        elif name == "self_update":
            r = await loop.run_in_executor(None, lambda: self_update(parameters=args, player=ui, speak=speak))
            result = r or "Done."

        elif name == "shutdown_viko":
            ui.write_log("SYS: Shutdown requested.")
            speak("Goodbye.")

            def _shutdown():
                import time
                import os
                time.sleep(1)
                os._exit(0)

            threading.Thread(target=_shutdown, daemon=True).start()

        else:
            result = f"Unknown tool: {name}"

    except Exception as e:
        result = f"Tool '{name}' failed: {e}"
        traceback.print_exc()
        speak_error(name, e)

    if not ui.muted:
        ui.set_state("LISTENING")

    print(f"[Viko] {name} → {str(result)[:80]}")

    return types.FunctionResponse(
        id=fc.id, name=name,
        response={"result": result}
    )
