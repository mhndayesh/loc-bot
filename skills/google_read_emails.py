"""
name: read_recent_emails
description: "Fetches the most recent unread emails from the authenticated user's Gmail inbox. Maximum 5."
"""
def read_recent_emails(max_results=5):
    import sys
    import os
    
    # Path routing to find the integrations folder dynamically
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        
    try:
        from integrations.google_auth import auth_manager
    except ImportError as e:
        return f"Error importing auth_manager: {e}. Is the integrations folder configured correctly?"

    service = auth_manager.get_service('gmail', 'v1')
    if not service:
        return "ERROR: Google authentication failed. Ensure credentials.json exists and browser authorization is complete."

    try:
        # Call the Gmail API to get a list of unread messages
        results = service.users().messages().list(userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results).execute()
        messages = results.get('messages', [])

        if not messages:
            return "You have no new unread emails."

        output = []
        for msg in messages:
            try:
                msg_id = msg['id']
                message = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['From', 'Subject', 'Date']).execute()
                
                headers = message.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                snippet = message.get('snippet', '')
                
                output.append(f"FROM: {sender}\nSUBJECT: {subject}\nDATE: {date}\nSNIPPET: {snippet}\n---")
            except Exception as e:
                output.append(f"Error reading message {msg.get('id', 'unknown')}: {e}")

        return "\n".join(output)
    except Exception as e:
        return f"An error occurred while fetching emails: {e}"
