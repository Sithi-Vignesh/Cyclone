from langgraph.prebuilt import create_react_agent
from app.backend.core.llm import agent_llm
from datetime import datetime
from app.backend.tools.system_tools import open_application, open_file, get_battery_status, read_clipboard, clipboard_write, get_active_window, get_all_windows, set_volume, adjust_volume, mute_unmute_mic, set_brightness, adjust_brightness, take_screenshot, lock_screen, shutdown_system, restart_system, request_shutdown, request_restart
from app.backend.tools.memory_tools import delete_all_memory, get_upcoming_events, get_mood_summary
from app.backend.tools.window_tool import minimize_window, maximize_window, close_window, focus_window, split_screen, show_task_view
from app.backend.tools.folder_tools import open_folder
from app.backend.tools.spotify_tools import (
    spotify_play_song,
    spotify_play_pause,
    spotify_next_track,
    spotify_previous_track,
    spotify_toggle_shuffle,
    spotify_toggle_repeat,
    spotify_like_current_song,
    spotify_play_liked_songs
)
from app.backend.tools.whatsapp_tools import call_contact, text_contact
from app.backend.tools.web_tools import get_weather, web_search

tools = [
    open_application,
    open_file,
    open_folder,
    take_screenshot,
    spotify_play_song,
    spotify_play_pause,
    spotify_next_track,
    spotify_previous_track,
    spotify_toggle_shuffle,
    spotify_toggle_repeat,
    spotify_like_current_song,
    spotify_play_liked_songs,
    call_contact,
    text_contact,
    get_weather,
    get_battery_status,
    web_search,
    read_clipboard,
    clipboard_write,
    get_active_window,
    get_all_windows,
    delete_all_memory,
    get_upcoming_events,
    get_mood_summary,
    set_volume,
    adjust_volume,
    mute_unmute_mic,
    set_brightness,
    adjust_brightness,
    minimize_window,
    maximize_window,
    close_window,
    focus_window,
    split_screen,
    show_task_view,
    lock_screen,
    request_shutdown,
    request_restart,
    shutdown_system,
    restart_system,
]

agent_executor = create_react_agent(
    agent_llm, 
    tools,
    prompt=f"""You are a helpful research assistant. Today's date is {datetime.now().strftime('%Y-%m-%d')}. Always use the current year when searching for recent information.
    Keep your final response concise and conversational — no tables, no markdown headers, no bullet lists unless explicitly asked."""
)