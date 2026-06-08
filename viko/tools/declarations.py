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
