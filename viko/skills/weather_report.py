import webbrowser
import urllib.parse


def weather_action(parameters: dict, player=None) -> str:
    city = parameters.get("city", "")
    if not city:
        return "No city specified."

    query = urllib.parse.quote(f"weather in {city}")
    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Opened weather for {city}."
