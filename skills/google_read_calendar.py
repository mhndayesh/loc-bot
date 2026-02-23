"""
name: read_calendar_events
description: "Fetches the next 5 upcoming events on the authenticated user's primary Google Calendar."
"""
def read_calendar_events():
    import sys
    import os
    import datetime
    
    # Path routing to find the integrations folder dynamically
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        
    try:
        from integrations.google_auth import auth_manager
    except ImportError as e:
        return f"Error importing auth_manager: {e}. Is the integrations folder configured correctly?"

    service = auth_manager.get_service('calendar', 'v3')
    if not service:
        return "ERROR: Google authentication failed. Ensure credentials.json exists and browser authorization is complete."

    try:
        # Call the Calendar API
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=5, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return 'No upcoming events found.'
            
        output = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'No Title')
            desc = event.get('description', 'No Description')
            output.append(f"START: {start}\nEVENT: {summary}\nDESC: {desc}\n---")

        return "\n".join(output)
            
    except Exception as e:
        return f"An error occurred fetching Calendar details: {e}"
