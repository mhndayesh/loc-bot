"""
name: send_email
description: "Sends an email using the authenticated user's Gmail account. Requires recipient email, subject, and body text."
"""
def send_email(to_email, subject, body_text):
    import sys
    import os
    import base64
    from email.message import EmailMessage
    
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
        # Create the email message
        message = EmailMessage()
        message.set_content(body_text)
        message['To'] = to_email
        message['From'] = 'me' # Gmail API uses 'me' for the authenticated user
        message['Subject'] = subject

        # Encode and send
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        # Call the Gmail API to send the email
        send_message = service.users().messages().send(userId='me', body=create_message).execute()
        return f"SUCCESS: Email sent to {to_email}. Message Id: {send_message['id']}"
        
    except Exception as e:
        return f"An error occurred while sending the email: {e}"
