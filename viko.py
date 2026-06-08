import asyncio
import threading
import sys
import traceback
from pathlib import Path

import numpy as np
import sounddevice as sd
from google import genai
from google.genai import types

from viko.ui     import VikoUI
from viko.core.memory import (
    update_memory,
    should_extract_memory, extract_memory, remember,
)
from viko.core.conversation import (
    start_session as conv_start_session,
    end_session   as conv_end_session,
    save_message  as conv_save_message,
    get_recent_messages,
    summarize_session_async,
)
from viko.core.context_builder import build_system_context
from viko.core.vector_store import index_message as vs_index_message
from viko.core.logger import get_logger
from viko.core.speaker_verifier import SpeakerVerifier

_log = get_logger("main")

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


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR            = get_base_dir()
PROMPT_PATH         = BASE_DIR / "viko" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024
SPEECH_THRESHOLD    = 40    # int16 RMS — active speech (MacBook Air mic level)
SILENCE_CHUNKS      = 20    # ~1.3s silence ends an utterance
MIN_SPEECH_CHUNKS   = 8     # ~512ms minimum speech to process
SV_PASS_THRESHOLD  = 0.60  # similarity >= this → verified owner
SV_BLOCK_THRESHOLD = 0.55  # similarity <  this → blocked non-owner


def _get_api_key() -> str:
    from viko.core.config import get_gemini_key
    return get_gemini_key()


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are Viko, a sharp and efficient AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )


_last_memory_input = ""


def _update_memory_async(user_text: str, viko_text: str) -> None:
    global _last_memory_input

    user_text = (user_text or "").strip()
    viko_text = (viko_text or "").strip()

    if len(user_text) < 5 or user_text == _last_memory_input:
        return
    _last_memory_input = user_text

    try:
        api_key = _get_api_key()
        if not should_extract_memory(user_text, viko_text, api_key):
            return
        data = extract_memory(user_text, viko_text, api_key)
        if data:
            update_memory(data)
            print(f"[Memory] {list(data.keys())}")
    except Exception as e:
        if "429" not in str(e):
            print(f"[Memory] {e}")


TOOL_DECLARATIONS = [
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "weather_report",
        "description": "Shows the weather report for a city.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using the OS scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to file (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. US, ID"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text on screen, closing apps, fullscreen, dark mode, WiFi, restart, shutdown, "
            "scrolling, tab management, zoom, screenshots, lock screen, refresh/reload page. "
            "Use for ANY single computer control command. NEVER route to agent_task."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Optional value: volume level, text to type, etc."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Opens the EXTERNAL system browser (Chrome/Safari/Firefox) outside VIKO. "
            "Use ONLY when the user explicitly asks to open the external/system browser. "
            "For ALL other web tasks — navigation, search, browsing — use navigate_browser instead."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | press | close"},
                "url":         {"type": "STRING", "description": "URL for go_to action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up or down for scroll"},
                "key":         {"type": "STRING", "description": "Key name for press action"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "self_update",
        "description": (
            "Modifikasi kode VIKO sendiri: tambah skill baru, fix bug, ubah perilaku atau "
            "prompt, modifikasi UI, atau restore backup perubahan sebelumnya. "
            "Gunakan action='confirm' saat user menyetujui plan atau restart. "
            "Gunakan action='restore' untuk kembalikan perubahan terakhir. "
            "Gunakan action='history' untuk lihat log perubahan."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "intent": {
                    "type": "STRING",
                    "description": "Deskripsi lengkap perubahan yang diminta user"
                },
                "target_files": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "Opsional: file spesifik yang relevan, e.g. ['viko/skills/browser_tool.py']"
                },
                "action": {
                    "type": "STRING",
                    "description": "create_skill | fix_bug | modify_prompt | modify_ui | restore | history | confirm | cancel"
                }
            },
            "required": ["intent", "action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "cmd_control",
        "description": (
            "Runs shell/terminal commands or opens files with the default app. "
            "Use for: running scripts, opening files, executing system commands, "
            "terminal operations. Accepts natural language descriptions of what to do."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task":    {"type": "STRING", "description": "Natural language description or raw shell command"},
                "visible": {"type": "BOOLEAN", "description": "Open a visible terminal window (default: false)"},
            },
            "required": ["task"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data"},
                "text":        {"type": "STRING", "description": "Text to type or paste"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and reports the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to file"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "file_processor",
        "description": (
            "Processes any file that the user has uploaded or dropped onto the interface. "
            "Use this when the user refers to an uploaded file and wants an action on it. "
            "Supports: images (describe/ocr/resize/compress/convert), "
            "PDFs (summarize/extract_text/to_word), "
            "Word docs & text files (summarize/fix/reformat/translate), "
            "CSV/Excel (analyze/stats/filter/sort/convert), "
            "JSON/XML (validate/format/analyze), "
            "code files (explain/review/fix/optimize/run/document/test), "
            "audio (transcribe/trim/convert/info), "
            "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
            "archives (list/extract), "
            "presentations (summarize/extract_text). "
            "ALWAYS call this tool when a file has been uploaded and the user gives a command about it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path":   {"type": "STRING",  "description": "Full path to the file. Leave empty to use the currently uploaded file."},
                "action":      {"type": "STRING",  "description": "What to do with the file (e.g. summarize, describe, transcribe, extract_text, analyze, run, fix)"},
                "instruction": {"type": "STRING",  "description": "Free-form instruction if action doesn't cover it"},
                "format":      {"type": "STRING",  "description": "Target format for conversion"},
                "width":       {"type": "INTEGER", "description": "Target width for image resize"},
                "height":      {"type": "INTEGER", "description": "Target height for image resize"},
                "scale":       {"type": "NUMBER",  "description": "Scale factor for image resize"},
                "quality":     {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
                "start":       {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
                "end":         {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
                "timestamp":   {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
                "column":      {"type": "STRING",  "description": "Column name for CSV filter/sort"},
                "value":       {"type": "STRING",  "description": "Filter value for CSV filter"},
                "condition":   {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
                "ascending":   {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
                "save":        {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
                "destination": {"type": "STRING",  "description": "Output folder for archive extract"},
            },
            "required": []
        }
    },
    {
        "name": "navigate_browser",
        "description": (
            "PRIMARY browser tool — selalu gunakan ini untuk SEMUA tugas web. "
            "Membuka URL atau halaman pencarian di embedded browser VIKO (di dalam jendela VIKO). "
            "Gunakan untuk: membuka website, mencari sesuatu di web, navigasi halaman, "
            "melihat konten online. Jangan gunakan browser_control untuk tugas web biasa."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "URL lengkap (https://...) atau domain (github.com)"},
            },
            "required": ["url"]
        }
    },
    {
        "name": "render_content",
        "description": (
            "Generate HTML dan tampilkan langsung di browser VIKO. "
            "Gunakan untuk: wireframe, presentasi, dashboard, dokumen, atau output visual apapun. "
            "AI membuat HTML, lalu disimpan ke workspace/ dan otomatis dibuka di browser."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "content":  {"type": "STRING", "description": "Konten HTML lengkap yang akan di-render"},
                "filename": {"type": "STRING", "description": "Nama file, misal login-wireframe.html"},
                "category": {"type": "STRING", "description": "wireframes | presentations | documents | code"},
            },
            "required": ["content", "filename"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "Ambil screenshot halaman browser VIKO saat ini.",
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "get_page_content",
        "description": "Baca teks halaman browser VIKO saat ini untuk dianalisis AI.",
        "parameters": {"type": "OBJECT", "properties": {}, "required": []}
    },
    {
        "name": "browser_interact",
        "description": (
            "Kontrol embedded browser VIKO — click, type, scroll, baca konten, jalankan JS. "
            "Gunakan ini (BUKAN browser_control) untuk semua interaksi dengan halaman yang "
            "sedang terbuka di browser internal VIKO. "
            "Actions: click (klik elemen), type (isi input), scroll (gulir halaman), "
            "scroll_to (scroll ke elemen), get_text (ambil teks), get_links (daftar link), "
            "submit (submit form), run_js (jalankan JavaScript bebas)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "get_inputs | click | type | clear | scroll | scroll_to | get_text | get_links | submit | run_js"},
                "selector":  {"type": "STRING",  "description": "CSS selector, e.g. '#first-name', 'input[name=email]'"},
                "label":     {"type": "STRING",  "description": "Label/placeholder text to find input — e.g. 'First name', 'Search'. Use for type/clear/scroll_to when selector unknown."},
                "text":      {"type": "STRING",  "description": "Text content to find clickable element (for click action)"},
                "value":     {"type": "STRING",  "description": "Text to type into the input (for type action)"},
                "direction": {"type": "STRING",  "description": "up or down (for scroll)"},
                "amount":    {"type": "INTEGER", "description": "Pixels to scroll (default 400)"},
                "code":      {"type": "STRING",  "description": "JavaScript code to run (for run_js action)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "visual_control",
        "description": (
            "Kontrol browser VIKO menggunakan koordinat layar via agent-browser CDP. "
            "Lebih akurat dari browser_interact untuk klik visual (tombol ikon, canvas, dll). "
            "Aktif setelah agent-browser running (~5s setelah browser dibuka). "
            "Actions: click_xy (klik koordinat), scroll_xy (scroll koordinat), "
            "type_text (ketik teks), key (tekan tombol keyboard), "
            "screenshot (screenshot CDP), navigate (buka URL)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":  {"type": "STRING",  "description": "click_xy | scroll_xy | type_text | key | screenshot | navigate"},
                "x":       {"type": "INTEGER", "description": "Koordinat X layar browser (untuk click_xy, scroll_xy)"},
                "y":       {"type": "INTEGER", "description": "Koordinat Y layar browser (untuk click_xy, scroll_xy)"},
                "deltaX":  {"type": "INTEGER", "description": "Delta scroll horizontal (default 0)"},
                "deltaY":  {"type": "INTEGER", "description": "Delta scroll vertikal (default 400, negatif=naik)"},
                "text":    {"type": "STRING",  "description": "Teks untuk di-type (action: type_text)"},
                "key":     {"type": "STRING",  "description": "Tombol keyboard, e.g. Enter, Tab, Escape (action: key)"},
                "url":     {"type": "STRING",  "description": "URL untuk navigasi (action: navigate)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "shutdown_viko",
        "description": (
            "Shuts down the assistant completely. "
            "Call this when the user expresses intent to end the conversation, "
            "close the assistant, say goodbye, or stop Viko. "
            "The user can say this in ANY language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food)"},
                "value": {"type": "STRING", "description": "Concise value in English"},
            },
            "required": ["category", "key", "value"]
        }
    },
]


import re as _re
_CTRL_SEQ_RE = _re.compile(r'^<ctrl\d+>$', _re.IGNORECASE)

def _is_ctrl_seq(text: str) -> bool:
    return bool(_CTRL_SEQ_RE.match(text.strip()))


def _rms(pcm_bytes: bytes) -> float:
    """RMS energy of int16 PCM bytes. Returns 0.0 for empty input."""
    arr = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(arr ** 2))) if arr.size else 0.0


class VikoLive:

    SESSION_MAX_IDLE = 8 * 60  # seconds — reconnect if idle this long

    def __init__(self, ui: VikoUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self._last_active   = 0.0
        self._session_id    = 0
        self._offline_stt   = None  # pre-warmed OfflineSTT instance
        self._sv                  = SpeakerVerifier()
        self._verification_bypass = False
        self._enrolling           = False
        self._enroll_buf: list    = []
        self._enroll_target: int  = 0
        self._sv_verified:   bool = True   # updated by _verify_and_forward background loop
        self._viko_addressed: bool = False  # set when "viko" detected in input_transcription
        self._vad_model             = None  # loaded lazily in _listen_audio
        self.raw_queue            = None
        self.ui.on_text_command = self._on_text_command
        self.ui.on_file_command = self._on_file_command

    def _on_text_command(self, text: str):
        if self.ui.paused:
            return

        # Passphrase bypass — must check before logging to avoid exposing it on screen
        from viko.core.config import get_owner_passphrase
        passphrase = get_owner_passphrase()
        if passphrase and text.strip() == passphrase:
            self.ui.write_log("YOU: [passphrase]")
            def _reset_bypass():
                self._verification_bypass = False
                self.ui.write_log("SYS: Bypass verifikasi suara nonaktif.")
            self._verification_bypass = True
            if self._loop:
                self._loop.call_later(300, _reset_bypass)
            self.ui.write_log("SYS: Bypass aktif 5 menit.")
            return  # never sent to Gemini

        self.ui.write_log(f"YOU: {text}")

        # Re-enrollment phrase — requires bypass active
        if text.strip().lower() == "viko, kenali suaraku" and self._verification_bypass:
            if self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._start_re_enrollment(), self._loop
                )
            return  # never sent to Gemini

        if not self._loop or not self.session:
            self.ui.write_log("SYS: Session not ready — try again in a moment.")
            return
        fut = asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"role": "user", "parts": [{"text": text}]},
                turn_complete=True,
            ),
            self._loop,
        )
        def _on_done(f):
            try:
                f.result()
            except Exception as exc:
                self.ui.write_log(f"ERR: text send failed — {exc}")
        fut.add_done_callback(_on_done)

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
            self._loop
        )

    def _warmup_offline_stt(self) -> None:
        """Download and load faster-whisper model in background thread (called once after connect)."""
        try:
            from viko.core.offline_stt import OfflineSTT
            stt = OfflineSTT()
            stt._load()
            self._offline_stt = stt
            print("[Viko] Offline STT model ready")
            self.ui.write_log("SYS: Model offline siap.")
        except Exception as _e:
            print(f"[Viko] Offline STT warmup failed: {_e}")

    async def _enroll_voice(self) -> None:
        """Record 10 seconds of mic audio and save owner voice profile."""
        loop = asyncio.get_running_loop()
        audio_q: asyncio.Queue = asyncio.Queue()

        def _cb(indata, frames, time_info, status):
            loop.call_soon_threadsafe(audio_q.put_nowait, indata.tobytes())

        target = int(10 * SEND_SAMPLE_RATE / CHUNK_SIZE)  # ~156 chunks = 10s
        chunks = []

        with sd.InputStream(
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=_cb,
        ):
            for i in range(target):
                chunk = await audio_q.get()
                chunks.append(chunk)

        pcm = b"".join(chunks)
        await loop.run_in_executor(None, self._sv.enroll, pcm)

    async def _start_re_enrollment(self) -> None:
        """Signal _verify_and_forward() to collect 10s of audio for re-enrollment."""
        self.ui.write_log("SYS: Silakan berbicara bebas selama 10 detik untuk mendaftarkan suara baru...")
        self._enroll_buf    = []
        self._enroll_target = int(10 * SEND_SAMPLE_RATE / CHUNK_SIZE)
        self._enrolling     = True

    async def _offline_respond(self, text: str) -> None:
        """Get LLM reply for text and speak via macOS say. Used in offline mode."""
        loop = asyncio.get_running_loop()
        try:
            from viko.core.client import LLMClient
            system = (
                "Kamu adalah VIKO, asisten AI suara pribadi. "
                "Jawab dalam Bahasa Indonesia, singkat dan jelas (1-2 kalimat). "
                "Mode offline — tidak ada akses internet saat ini."
            )
            reply = await loop.run_in_executor(None, LLMClient().chat, text, system)
        except Exception as _e:
            print(f"[Viko] Offline LLM failed: {_e}")
            reply = "Maaf, saya sedang offline dan tidak bisa menjawab sekarang."

        self.ui.write_log(f"Viko [offline]: {reply}")
        try:
            proc = await asyncio.create_subprocess_exec(
                "say", "-v", "Damayanti", reply,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except Exception:
            try:
                proc = await asyncio.create_subprocess_exec("say", reply)
                await proc.wait()
            except Exception as _e2:
                print(f"[Viko] say failed: {_e2}")

    async def _offline_mode(self, max_seconds: int = 60) -> None:
        """Offline listen-and-respond loop using faster-whisper + LLM + macOS say.

        VAD constants:
          SPEECH_THRESHOLD=300  — int16 RMS above this = active speech
          SILENCE_CHUNKS=20     — ~1.3s silence (20 × 64ms) ends an utterance
          MIN_SPEECH_CHUNKS=8   — ~512ms min speech before transcribing
        """
        from viko.core.offline_stt import OfflineSTT

        stt = self._offline_stt or OfflineSTT()
        loop = asyncio.get_running_loop()
        audio_q: asyncio.Queue = asyncio.Queue()

        def _cb(indata, frames, time_info, status):
            if self.ui.muted or self.ui.paused:
                return
            loop.call_soon_threadsafe(audio_q.put_nowait, indata.tobytes())

        buf:           list[bytes] = []
        silence_count: int  = 0
        speech_count:  int  = 0
        in_speech:     bool = False
        deadline:      float = loop.time() + max_seconds

        with sd.InputStream(
            samplerate=SEND_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
            callback=_cb,
        ):
            self.ui.write_log("SYS: Mode offline. Whisper aktif.")
            print("[Viko] Offline STT active")

            while loop.time() < deadline:
                try:
                    chunk = await asyncio.wait_for(audio_q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                rms = _rms(chunk)

                if rms > SPEECH_THRESHOLD:
                    buf.append(chunk)
                    speech_count += 1
                    silence_count = 0
                    in_speech = True
                elif in_speech:
                    buf.append(chunk)
                    silence_count += 1
                    if silence_count >= SILENCE_CHUNKS:
                        if speech_count >= MIN_SPEECH_CHUNKS:
                            pcm = b"".join(buf)
                            sim = await loop.run_in_executor(
                                None, self._sv.similarity, pcm
                            )
                            is_owner = (
                                self._verification_bypass
                                or not self._sv.is_enrolled()
                                or sim >= SV_PASS_THRESHOLD
                            )
                            if is_owner:
                                text = await loop.run_in_executor(
                                    None, stt.transcribe_pcm, pcm
                                )
                                if text.strip():
                                    self.ui.write_log(f"You [offline]: {text}")
                                    await self._offline_respond(text)
                        buf           = []
                        silence_count = 0
                        speech_count  = 0
                        in_speech     = False

        print("[Viko] Offline mode ended — reconnecting")

    def _on_file_command(self, path: str):
        """Called when user uploads a file. Images are sent as vision input."""
        import mimetypes
        from pathlib import Path as _P
        p = _P(path)
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        is_image = mime.startswith("image/")
        size = p.stat().st_size
        size_str = (f"{size//1_048_576}MB" if size >= 1_048_576
                    else f"{size//1024}KB" if size >= 1024 else f"{size}B")
        self.ui.write_log(f"FILE: {p.name} ({size_str}) → {'vision' if is_image else 'text'}")

        if not self._loop or not self.session:
            self.ui.write_log("SYS: Session not ready.")
            return

        if is_image:
            # Send image data directly to Gemini Live vision
            async def _send_img():
                data = p.read_bytes()
                await self.session.send_realtime_input(
                    media=types.Blob(mime_type=mime, data=data)
                )
                await self.session.send_client_content(
                    turns={"role": "user",
                           "parts": [{"text": f"[Image uploaded: {p.name}] Analisa gambar ini."}]},
                    turn_complete=True,
                )
            fut = asyncio.run_coroutine_threadsafe(_send_img(), self._loop)
        else:
            # Non-image: just notify with text so VIKO can ask what to do
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size_str} | "
                f"File '{p.name}' sudah diupload. Tanya mau diapakan."
            )
            fut = asyncio.run_coroutine_threadsafe(
                self.session.send_client_content(
                    turns={"role": "user", "parts": [{"text": msg}]},
                    turn_complete=True,
                ),
                self._loop,
            )

        def _on_done(f):
            try:
                f.result()
            except Exception as exc:
                self.ui.write_log(f"ERR: file send failed — {exc}")
        fut.add_done_callback(_on_done)

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"{tool_name} encountered an error. {short}")

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        sys_prompt = _load_system_prompt()

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        history_ctx = build_system_context()

        parts = [time_ctx]
        if history_ctx:
            parts.append(history_ctx)
        parts.append(sys_prompt)

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": TOOL_DECLARATIONS}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            ),
        )

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[Viko] {name}  {args}")
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
        self.ui.set_state(_TOOL_STATE.get(name, "THINKING"))

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] save_memory: {category}/{key} = {value}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "cmd_control":
                r = await loop.run_in_executor(None, lambda: cmd_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "agent_task":
                from viko.agent.queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "navigate_browser":
                r = await loop.run_in_executor(None, lambda: navigate_browser(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "render_content":
                r = await loop.run_in_executor(None, lambda: render_content(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "browser_screenshot":
                r = await loop.run_in_executor(None, lambda: browser_screenshot(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "get_page_content":
                r = await loop.run_in_executor(None, lambda: get_page_content(parameters=args, player=self.ui))
                result = r or "(kosong)"

            elif name == "browser_interact":
                r = await loop.run_in_executor(None, lambda: browser_interact(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "visual_control":
                r = await loop.run_in_executor(None, lambda: visual_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "self_update":
                r = await loop.run_in_executor(None, lambda: self_update(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "shutdown_viko":
                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye.")

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
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[Viko] {name} → {str(result)[:80]}")

        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    async def _listen_audio(self):
        import threading as _threading

        if self._vad_model is None:
            from silero_vad import load_silero_vad
            self._vad_model = load_silero_vad()

        try:
            dev = sd.query_devices(kind='input')
            print(f"[Viko] Mic: {dev['name']} @ {SEND_SAMPLE_RATE}Hz")
        except Exception:
            print("[Viko] Mic started")

        loop = asyncio.get_running_loop()
        _stop = _threading.Event()
        _vad  = self._vad_model

        def _audio_thread():
            import numpy as _np
            import torch as _torch
            try:
                with sd.RawInputStream(
                    samplerate=SEND_SAMPLE_RATE,
                    channels=CHANNELS,
                    dtype="int16",
                    blocksize=CHUNK_SIZE,
                ) as stream:
                    print("[Viko] Mic stream open")
                    while not _stop.is_set():
                        data, _ = stream.read(CHUNK_SIZE)
                        with self._speaking_lock:
                            viko_speaking = self._is_speaking
                        if viko_speaking or self.ui.muted or self.ui.paused:
                            continue
                        pcm_f32 = _np.frombuffer(bytes(data), dtype=_np.int16).astype(_np.float32) / 32768.0
                        # Silero VAD requires 512-sample windows at 16kHz
                        half = pcm_f32[:512]
                        try:
                            with _torch.no_grad():
                                speech_prob = float(_vad(_torch.from_numpy(half), SEND_SAMPLE_RATE))
                        except Exception:
                            speech_prob = 1.0  # fallback: treat as speech on VAD error
                        item = {
                            "data":      bytes(data),
                            "mime_type": "audio/pcm",
                            "is_speech": speech_prob > 0.5,
                        }
                        try:
                            loop.call_soon_threadsafe(self.raw_queue.put_nowait, item)
                        except Exception:
                            pass  # drop if loop is closed
            except Exception as _e:
                print(f"[Viko] Mic error: {_e}")

        t = _threading.Thread(target=_audio_thread, daemon=True)
        t.start()

        try:
            await asyncio.Event().wait()
        finally:
            _stop.set()

    async def _verify_and_forward(self):
        """Input gate: forward audio to out_queue only when speaker is verified.

        Uses dual-threshold verification every ~2s to handle silence windows:
          similarity >= 0.65 → clear owner → gate OPEN
          similarity <  0.55 → clear non-owner → gate CLOSED
          0.55–0.65           → ambiguous (silence/transition) → keep current state

        Silence windows (0.45–0.65) don't flip the gate, so owner keeps getting
        responses even during pauses. Non-owner (0.36–0.54) consistently falls
        below 0.55 and is blocked within one 2-second window.
        """
        loop = asyncio.get_running_loop()
        verify_buf:       list[bytes] = []
        VERIFY_CHUNKS     = 32    # 32 × 64ms ≈ 2s — minimum for reliable resemblyzer embedding
        PASS_THRESHOLD    = SV_PASS_THRESHOLD
        BLOCK_THRESHOLD   = SV_BLOCK_THRESHOLD
        RECOVERY_WINDOWS  = 5    # after 5 ambiguous windows (~10s) without clear non-owner, reopen
        verified_ok       = True
        ambiguous_streak  = 0

        while True:
            item        = await self.raw_queue.get()
            chunk_bytes = item["data"]

            # Re-enrollment: collect audio, skip normal processing
            if self._enrolling:
                self._enroll_buf.append(item)
                if len(self._enroll_buf) >= self._enroll_target:
                    self._enrolling = False
                    pcm = b"".join(i["data"] for i in self._enroll_buf)
                    self._enroll_buf = []
                    await loop.run_in_executor(None, self._sv.enroll, pcm)
                    self.ui.write_log("SYS: Suara berhasil didaftarkan.")
                    verified_ok      = True
                    ambiguous_streak = 0
                    verify_buf       = []   # discard pre-enroll overlap
                continue

            # Accumulate for periodic verification
            verify_buf.append(chunk_bytes)
            if len(verify_buf) >= VERIFY_CHUNKS:
                pcm = b"".join(verify_buf)
                verify_buf = verify_buf[-8:]  # keep ~500ms overlap
                if self._sv.is_enrolled() and not self._verification_bypass:
                    # Skip verification on silence — don't let silence PCM close the gate
                    if _rms(pcm) < SPEECH_THRESHOLD:
                        print(f"[SV] silence window — gate unchanged (verified={verified_ok})")
                    else:
                        sim = await loop.run_in_executor(None, self._sv.similarity, pcm)
                        print(f"[SV] similarity={sim:.3f} verified={verified_ok}")
                        if sim >= PASS_THRESHOLD:
                            verified_ok      = True
                            ambiguous_streak = 0
                        elif sim < BLOCK_THRESHOLD:
                            verified_ok      = False
                            ambiguous_streak = 0
                        else:
                            # ambiguous (0.55–0.60): if blocked, count toward recovery
                            if not verified_ok:
                                ambiguous_streak += 1
                                if ambiguous_streak >= RECOVERY_WINDOWS:
                                    verified_ok      = True  # non-owner gone, reopen
                                    ambiguous_streak = 0
                                    print("[SV] auto-recovery: reopened after silence")

            # Gate: forward real audio when verified; silence otherwise to keep
            # Gemini connection alive and prevent WebSocket timeout
            # Strip is_speech — it's internal metadata, not a valid Gemini media field
            media_item = {"data": item["data"], "mime_type": item["mime_type"]}
            if self._verification_bypass or not self._sv.is_enrolled() or verified_ok:
                await self.out_queue.put(media_item)
            else:
                await self.out_queue.put({**media_item, "data": bytes(len(chunk_bytes))})

    async def _receive_audio(self):
        print("[Viko] Receive started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        try:
                            self.audio_in_queue.put_nowait(response.data)
                        except asyncio.QueueFull:
                            pass  # drop chunk under load; preferable to crashing

                    if response.server_content:
                        sc = response.server_content

                        if sc.interrupted:
                            while not self.audio_in_queue.empty():
                                try:
                                    self.audio_in_queue.get_nowait()
                                except Exception:
                                    break
                            self.set_speaking(False)
                            out_buf = []

                        if sc.output_transcription and sc.output_transcription.text:
                            self.set_speaking(True)
                            txt = sc.output_transcription.text
                            if txt and not _is_ctrl_seq(txt):
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = sc.input_transcription.text
                            if txt and not _is_ctrl_seq(txt):
                                in_buf.append(txt)

                        if sc.turn_complete:
                            self.set_speaking(False)
                            self._last_active = asyncio.get_event_loop().time()

                            full_in = "".join(in_buf).strip()
                            if full_in:
                                self.ui.write_log(f"You: {full_in}")
                            in_buf = []

                            full_out = "".join(out_buf).strip()
                            if full_out:
                                self.ui.write_log(f"Viko: {full_out}")
                            out_buf = []

                            if full_in and len(full_in) > 5:
                                # Keyword trigger: "viko, ingat ini..."
                                _lower = full_in.lower()
                                if "ingat ini" in _lower:
                                    _after = full_in[_lower.find("ingat ini") + 9:].strip().lstrip(":").strip()
                                    if _after:
                                        _key = f"note_{int(asyncio.get_event_loop().time())}"
                                        threading.Thread(
                                            target=remember,
                                            args=(_key, _after, "notes"),
                                            daemon=True
                                        ).start()
                                        self.speak("Oke, sudah saya ingat.")

                                # Save to SQLite + ChromaDB in background
                                _sid = self._session_id
                                def _persist(user_txt=full_in, viko_txt=full_out, sid=_sid):
                                    try:
                                        mid = conv_save_message(sid, "user", user_txt)
                                        vs_index_message(user_txt, "user", sid, mid)
                                        if viko_txt:
                                            mid2 = conv_save_message(sid, "viko", viko_txt)
                                            vs_index_message(viko_txt, "viko", sid, mid2)
                                    except Exception as _e:
                                        print(f"[Memory] Persist failed: {_e}")
                                threading.Thread(target=_persist, daemon=True).start()

                                threading.Thread(
                                    target=_update_memory_async,
                                    args=(full_in, full_out),
                                    daemon=True
                                ).start()

                    if response.tool_call:
                        fn_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"[Viko] Tool: {fc.name}")
                            fr = await self._execute_tool(fc)
                            fn_responses.append(fr)
                        await self.session.send_tool_response(
                            function_responses=fn_responses
                        )

        except Exception as e:
            print(f"[Viko] Receive error: {e}")
            traceback.print_exc()
            raise

    async def _play_audio(self):
        try:
            dev = sd.query_devices(kind='output')
            print(f"[Viko] Output: {dev['name']} @ {RECEIVE_SAMPLE_RATE}Hz")
        except Exception:
            print("[Viko] Audio playback started")

        # latency='high' gives PortAudio a larger internal ring-buffer (~200-500ms)
        # so the device keeps playing even if asyncio is briefly delayed by tools.
        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=0,       # let PortAudio choose optimal block size
            latency="high",    # bigger internal buffer = stutter-resistant
        )
        stream.start()
        loop = asyncio.get_running_loop()
        _speak_off_handle = None
        try:
            while True:
                # Wait for first chunk
                chunk = await self.audio_in_queue.get()
                # Cancel any pending speaking=False — new audio arrived
                if _speak_off_handle is not None:
                    _speak_off_handle.cancel()
                    _speak_off_handle = None
                self.set_speaking(True)
                # Drain any queued chunks without waiting (batch write reduces
                # asyncio round-trips and keeps PortAudio buffer fed)
                chunks = [chunk]
                while True:
                    try:
                        chunks.append(self.audio_in_queue.get_nowait())
                    except asyncio.QueueEmpty:
                        break
                data = b"".join(chunks)
                await asyncio.to_thread(stream.write, data)
                if self.audio_in_queue.empty():
                    # Debounce: schedule speaking=False 150ms from now.
                    # call_later doesn't block consumption so the queue stays drained.
                    _speak_off_handle = loop.call_later(0.15, self.set_speaking, False)
        except Exception as e:
            print(f"[Viko] Playback error: {e}")
            raise
        finally:
            if _speak_off_handle is not None:
                _speak_off_handle.cancel()
            self.set_speaking(False)
            stream.stop()
            stream.close()

    async def _session_watchdog(self):
        while True:
            await asyncio.sleep(30)
            if self._last_active == 0.0:
                continue
            idle = asyncio.get_event_loop().time() - self._last_active
            if idle >= self.SESSION_MAX_IDLE and not self._is_speaking:
                print(f"[Viko] Session idle {idle:.0f}s — refreshing connection")
                self.ui.write_log("SYS: Refreshing connection...")
                raise RuntimeError("Session idle refresh")

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        self.ui.write_log("SYS: App dimulai ulang.")

        # Boot phase 1: loading memory + context
        self.ui.set_boot_progress(0.1, "LOADING MEMORY...")
        await asyncio.sleep(0.05)
        self.ui.set_boot_progress(0.35, "BUILDING CONTEXT...")
        await asyncio.sleep(0.05)

        # Enrollment: first launch (no voice profile yet)
        if not self._sv.is_enrolled():
            self.ui.set_boot_progress(0.45, "MENDAFTARKAN SUARA...")
            self.ui.write_log("SYS: Silakan berbicara bebas selama 10 detik...")
            await self._enroll_voice()
            self.ui.write_log("SYS: Suara berhasil didaftarkan.")

        _first_connect = True

        while True:
            try:
                if _first_connect:
                    self.ui.set_boot_progress(0.6, "CONNECTING...")
                print("[Viko] Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue(maxsize=200)  # ~200 chunks × 42ms = ~8s headroom
                    self.out_queue      = asyncio.Queue(maxsize=200)  # sized to hold full utterance burst from _verify_and_forward
                    self.raw_queue      = asyncio.Queue(maxsize=200)
                    self._last_active   = asyncio.get_event_loop().time()
                    self._enrolling     = False
                    self._enroll_buf    = []

                    # Start a new SQLite session
                    try:
                        self._session_id = conv_start_session()
                        print(f"[Conversation] Session started: {self._session_id}")
                    except Exception as _e:
                        print(f"[Conversation] Session start failed: {_e}")
                        self._session_id = 0

                    if _first_connect:
                        self.ui.set_boot_progress(1.0, "ONLINE")
                        _first_connect = False

                    print("[Viko] Connected.")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: Viko online.")

                    # Pre-load offline STT model in background so offline mode starts instantly
                    if self._offline_stt is None:
                        self.ui.write_log("SYS: Mempersiapkan model offline...")
                        threading.Thread(target=self._warmup_offline_stt, daemon=True).start()

                    # Announce self-update restart if flag was set by restarter.py
                    try:
                        from viko.self_engineer.restarter import check_and_clear_flag
                        _restart_msg = check_and_clear_flag()
                        if _restart_msg:
                            self.ui.write_log("SYS: Restarted after self-update.")
                            async def _announce_restart(msg=_restart_msg):
                                await asyncio.sleep(2.0)
                                await session.send_client_content(
                                    turns={"parts": [{"text": msg}]},
                                    turn_complete=True
                                )
                            tg.create_task(_announce_restart())
                    except Exception as _re:
                        print(f"[SelfEngineer] Restart check failed: {_re}")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(self._session_watchdog())
                    tg.create_task(self._verify_and_forward())

            except Exception as e:
                print(f"[Viko] {e}")
                traceback.print_exc()

            # End session + trigger background summarization
            if self._session_id:
                try:
                    conv_end_session(self._session_id)
                    msgs = get_recent_messages(30)
                    summarize_session_async(self._session_id, msgs)
                except Exception as _e:
                    print(f"[Conversation] Session end failed: {_e}")

            self.set_speaking(False)
            self.ui.set_state("OFFLINE")
            print("[Viko] Connection lost — offline mode")
            await self._offline_mode()
            self.ui.set_state("THINKING")
            print("[Viko] Reconnecting...")
            await asyncio.sleep(1)


def main():
    _log.info("=" * 60)
    _log.info("VIKO startup")
    ui = VikoUI("face.png")
    ui.set_boot_progress(0.0, "INITIALIZING...")

    def runner():
        ui.wait_for_api_key()
        viko = VikoLive(ui)
        try:
            asyncio.run(viko.run())
        except KeyboardInterrupt:
            _log.info("VIKO shutdown (keyboard interrupt)")
            print("\nShutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()
    _log.info("VIKO shutdown")


if __name__ == "__main__":
    main()
