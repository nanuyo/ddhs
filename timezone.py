from datetime import datetime
from zoneinfo import ZoneInfo

def get_system_timezone():
    # Get the current time and system's timezone
    local_time = datetime.now()
    timezone = local_time.astimezone().tzinfo
    return timezone

# Example usage
system_timezone = get_system_timezone()
print("System Time Zone:", system_timezone)
