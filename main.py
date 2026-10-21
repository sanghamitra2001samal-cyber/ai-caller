import os
import json
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from twilio.twiml.voice_response import VoiceResponse, Connect
from twilio.rest import Client
from dotenv import load_dotenv
from app.stream import handle_media_stream

load_dotenv()

app = FastAPI()

# Twilio Config
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER') # Your Twilio number

@app.get("/")
async def root():
    return {"message": "BeepBoost AI Caller is Online"}

@app.post("/voice/incoming")
async def incoming_call(request: Request):
    """Handle incoming calls - Connects to the Media Stream"""
    response = VoiceResponse()
    response.say("Connecting you to Beep Boost.")
    host = request.headers.get("host")
    connect = Connect()
    connect.stream(url=f"wss://{host}/media-stream")
    response.append(connect)
    return Response(content=str(response), media_type="application/xml")

@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    """WebSocket endpoint for Twilio Media Stream"""
    await handle_media_stream(websocket)

@app.post("/call/outbound")
async def make_outbound_call(to_number: str, request: Request):
    """Initiate an outbound call to a customer"""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return JSONResponse(status_code=500, content={"error": "Twilio credentials missing"})

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # The URL that Twilio will fetch when the call is answered.
        # It must point to our /voice/incoming (or specific outbound TwiML)
        # For simplicity, reusing the incoming logic which connects to the stream.
        # In prod, you might want a distinct webhook.
        host = request.headers.get("host")
        if not host:
             # Fallback if host is missing (e.g. testing), usually provided in real request
             # You might need to set a PUBLIC_URL env var if behind ngrok
             host = os.getenv("PUBLIC_URL", "your-ngrok-url.ngrok.io")

        url = f"https://{host}/voice/incoming"

        call = client.calls.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            url=url
        )
        return {"message": "Call initiated", "call_sid": call.sid}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
