def self_update(parameters: dict, player=None, speak=None) -> str:
    intent       = (parameters.get("intent") or "").strip()
    action       = (parameters.get("action") or "").strip()
    target_files = parameters.get("target_files") or None

    if not intent:
        return "Tolong deskripsikan apa yang ingin diubah."

    from viko.self_engineer.engine import run
    return run(intent=intent, action=action, target_files=target_files, speak=speak)
