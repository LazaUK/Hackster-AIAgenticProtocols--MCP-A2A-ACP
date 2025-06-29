from mcp.server.fastmcp import FastMCP
from typing import Literal, Optional
from datetime import datetime
import json

# Initialize the MCP server
mcp = FastMCP("Home Automation")

# Initial device states
DEVICES = {
    "living_room_light": {
        "name": "Living Room Light",
        "type": "light",
        "state": "off",
        "brightness": 50
    },
    "thermostat": {
        "name": "Home Thermostat",
        "type": "thermostat",
        "temperature": 22.0,
        "target_temperature": 22.0
    },
    "front_door": {
        "name": "Front Door Lock",
        "type": "lock",
        "state": "locked"
    }
}

# Simple event log
EVENT_LOG = []

def log_event(device_id: str, action: str):
    """Log device events"""
    # Handle special case for scene control
    device_name = DEVICES.get(device_id, {}).get("name", device_id)
    
    event = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "device": device_name,
        "action": action
    }
    EVENT_LOG.append(event)
    # Keep only last 10 events
    if len(EVENT_LOG) > 10:
        EVENT_LOG.pop(0)

# TOOLS - Functions that AI can call to perform actions
@mcp.tool()
def list_devices() -> str:
    """List all available devices and their current states"""
    result = "📱 Home Devices Status:\n\n"
    
    for device_id, device in DEVICES.items():
        result += f"🔹 {device['name']} ({device_id})\n"
        
        if device['type'] == 'light':
            result += f"   State: {device['state']}\n"
            result += f"   Brightness: {device['brightness']}%\n"
        elif device['type'] == 'thermostat':
            result += f"   Current: {device['temperature']}°C\n"
            result += f"   Target: {device['target_temperature']}°C\n"
        elif device['type'] == 'lock':
            result += f"   State: {device['state']}\n"
        
        result += "\n"
    
    return result

@mcp.tool()
def control_light(action: Literal["on", "off", "toggle"], brightness: Optional[int] = None) -> str:
    """Control the living room light (on/off/toggle) and optionally set brightness (0-100)"""
    device = DEVICES["living_room_light"]
    
    # Handle brightness first (but don't change state yet)
    if brightness is not None:
        if 0 <= brightness <= 100:
            device['brightness'] = brightness
        else:
            return "❌ Error: Brightness must be between 0 and 100"
    
    if action == "on":
        device['state'] = "on"
    elif action == "off":
        device['state'] = "off"
    elif action == "toggle":
        device['state'] = "on" if device['state'] == "off" else "off"
    
    # If brightness is 0, force the light off regardless of action
    if brightness == 0:
        device['state'] = "off"
    
    log_event("living_room_light", f"Light turned {device['state']}" + 
              (f" at {device['brightness']}%" if device['state'] == "on" else ""))
    
    return f"✅ Living Room Light is now {device['state']}" + (
        f" at {device['brightness']}% brightness" if device['state'] == "on" else ""
    )

@mcp.tool()
def set_temperature(target_temperature: float) -> str:
    """Set the target temperature for the thermostat (16-30°C)"""
    if not (16 <= target_temperature <= 30):
        return "❌ Error: Temperature must be between 16°C and 30°C"
    
    device = DEVICES["thermostat"]
    old_target = device['target_temperature']
    device['target_temperature'] = target_temperature
    
    # Simulate gradual temperature change
    temp_diff = target_temperature - device['temperature']
    device['temperature'] = round(device['temperature'] + (temp_diff * 0.2), 1)
    
    log_event("thermostat", f"Temperature set to {target_temperature}°C")
    
    return f"🌡️ Thermostat set to {target_temperature}°C (was {old_target}°C)\nCurrent temperature: {device['temperature']}°C"

@mcp.tool()
def control_door_lock(action: Literal["lock", "unlock"]) -> str:
    """Lock or unlock the front door"""
    device = DEVICES["front_door"]
    
    if action == "lock":
        device['state'] = "locked"
    elif action == "unlock":
        device['state'] = "unlocked"
    
    log_event("front_door", f"Door {action}ed")
    
    return f"🚪 Front door is now {device['state']}"

@mcp.tool()
def activate_scene(scene: Literal["evening", "morning", "away"]) -> str:
    """Activate a preset scene that controls multiple devices"""
    actions = []
    
    if scene == "evening":
        # Evening: Light on at 70%, comfortable temperature
        DEVICES["living_room_light"]["state"] = "on"
        DEVICES["living_room_light"]["brightness"] = 70
        DEVICES["thermostat"]["target_temperature"] = 19.0
        DEVICES["front_door"]["state"] = "locked"
        actions = ["Living room light on at 70%", "Temperature set to 19°C", "Front door locked"]
        
    elif scene == "morning":
        # Morning: Light on bright, slightly warmer
        DEVICES["living_room_light"]["state"] = "on"
        DEVICES["living_room_light"]["brightness"] = 90
        DEVICES["thermostat"]["target_temperature"] = 23.0
        DEVICES["front_door"]["state"] = "unlocked"
        actions = ["Living room light on at 90%", "Temperature set to 23°C", "Front door unlocked"]
        
    elif scene == "away":
        # Away: Everything off/secure
        DEVICES["living_room_light"]["state"] = "off"
        DEVICES["thermostat"]["target_temperature"] = 15.0
        DEVICES["front_door"]["state"] = "locked"
        actions = ["Light turned off", "Temperature lowered to 15°C", "Front door locked"]
    
    log_event("scene_control", f"Scene '{scene}' activated")
    
    return f"🎬 Scene '{scene}' activated!\n✅ " + "\n✅ ".join(actions)

# RESOURCE - Data that AI can access for context
@mcp.resource("home://device_status")
def get_device_status() -> str:
    """Get current status of all devices in JSON format"""
    status = {
        "devices": DEVICES,
        "last_updated": datetime.now().isoformat(),
        "recent_events": EVENT_LOG[-5:]  # Last 5 events
    }
    return json.dumps(status, indent=2)

# PROMPT - Template to guide AI interactions
@mcp.prompt("home_status_report")
def home_status_prompt() -> str:
    """Generate a comprehensive home status report"""
    return """Please create a friendly home status report. Use the list_devices tool to get current device states, then provide:

1. 🏠 **Current Status**: Brief overview of all devices
2. 💡 **Suggestions**: Any recommendations for comfort or energy savings
3. 🔒 **Security**: Check if the home is properly secured

Make the report conversational and helpful, as if you're a smart home assistant."""

if __name__ == "__main__":
    mcp.run()