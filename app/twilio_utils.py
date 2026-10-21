import os
from twilio.rest import Client

# You should set these in your .env file
ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
# The Ringba number or Destination number provided by the client
RINGBA_TARGET_NUMBER = os.getenv('RINGBA_TARGET_NUMBER')

def get_twilio_client():
    if not ACCOUNT_SID or not AUTH_TOKEN:
        raise ValueError("Twilio credentials not found in environment variables.")
    return Client(ACCOUNT_SID, AUTH_TOKEN)

def warm_transfer_call(call_sid: str):
    """
    Executes a warm transfer.
    In a real scenario, this is complex:
    1. Update the current call to put user on hold?
    2. Dial the agent (Ringba).
    3. Bridge them.
    
    Simpler approach (Cold Transfer / Refer):
    Update the call TwiML to <Dial> the new number.
    """
    client = get_twilio_client()
    
    # Using TwiML update to redirect the call (Blind Transfer)
    # For Warm Transfer, you'd typically use Conference or multiple call legs.
    # Here is a simple redirect example:
    twiml = f'<Response><Say>Transferring you now.</Say><Dial>{RINGBA_TARGET_NUMBER}</Dial></Response>'
    
    client.calls(call_sid).update(twiml=twiml)
    print(f"Transferring call {call_sid} to {RINGBA_TARGET_NUMBER}")
