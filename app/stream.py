import os
import json
import base64
import asyncio
import websockets
from fastapi import WebSocket
from app.agent import SYSTEM_PROMPT
from app.tools import validate_debt_amount, is_valid_state
from app.tool_schemas import TOOLS
from app.twilio_utils import warm_transfer_call

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
VOICE = 'ash'  # 'alloy', 'ash', 'ballad', 'coral', 'echo', 'sage', 'shimmer', 'verse'

# Log events for debugging
LOG_EVENTS = False

async def handle_media_stream(websocket: WebSocket):
    await websocket.accept()
    print("Twilio Client Connected")

    async with websockets.connect(
        'wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01',
        extra_headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "OpenAI-Beta": "realtime=v1",
        }
    ) as openai_ws:
        await send_session_update(openai_ws)
        
        stream_sid = None
        call_sid = None # Store Call SID for transfer
        
        async def receive_from_twilio():
            nonlocal stream_sid, call_sid
            try:
                while True:
                    message = await websocket.receive_text()
                    data = json.loads(message)
                    
                    if data['event'] == 'media':
                        # Send audio to OpenAI
                        audio_append = {
                            "type": "input_audio_buffer.append",
                            "audio": data['media']['payload']
                        }
                        await openai_ws.send(json.dumps(audio_append))
                    
                    elif data['event'] == 'start':
                        stream_sid = data['start']['streamSid']
                        call_sid = data['start']['callSid']
                        print(f"Incoming stream started: {stream_sid} for call {call_sid}")
            except Exception as e:
                print(f"Connection to Twilio lost: {e}")

        async def send_to_twilio():
            nonlocal stream_sid, call_sid
            try:
                async for message in openai_ws:
                    data = json.loads(message)
                    if LOG_EVENTS:
                        print(f"OpenAI Event: {data['type']}")

                    if data['type'] == 'response.audio.delta':
                        if stream_sid:
                            audio_payload = base64.b64encode(base64.b64decode(data['delta'])).decode('utf-8')
                            audio_delta = {
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {
                                    "payload": audio_payload
                                }
                            }
                            await websocket.send_text(json.dumps(audio_delta))
                    
                    elif data['type'] == 'response.function_call_arguments.done':
                        print(f"Tool Call Triggered: {data['name']}")
                        await handle_tool_call(data, openai_ws, call_sid)
                        
            except Exception as e:
                print(f"Connection to OpenAI lost: {e}")

        await asyncio.gather(receive_from_twilio(), send_to_twilio())

async def send_session_update(openai_ws):
    """Configure the OpenAI Realtime Session"""
    session_update = {
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "voice": VOICE,
            "instructions": SYSTEM_PROMPT,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
            "tools": TOOLS,
            "tool_choice": "auto",
        }
    }
    print("Sending Session Update to OpenAI...")
    await openai_ws.send(json.dumps(session_update))

async def handle_tool_call(data, openai_ws, call_sid):
    """Executes the tool and sends the result back to OpenAI"""
    call_id = data['call_id']
    name = data['name']
    arguments = json.loads(data['arguments'])
    
    result = None
    
    print(f"Executing Tool: {name} with args {arguments}")

    if name == 'check_state_validity':
        is_valid = is_valid_state(arguments.get('state_code'))
        result = {"valid": is_valid, "message": "State is approved" if is_valid else "State is NOT approved"}
        
    elif name == 'check_debt_qualification':
        is_valid = validate_debt_amount(arguments.get('amount', 0))
        result = {"valid": is_valid, "message": "Debt amount qualifies" if is_valid else "Debt amount is too low"}
        
    elif name == 'transfer_call':
        if call_sid:
            print(f"Initiating transfer for call {call_sid}")
            try:
                warm_transfer_call(call_sid)
                result = {"status": "success", "message": "Transfer initiated"}
            except Exception as e:
                result = {"status": "error", "message": str(e)}
        else:
            result = {"status": "error", "message": "No Call SID available"}

    # Send result back to OpenAI
    tool_output = {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps(result)
        }
    }
    await openai_ws.send(json.dumps(tool_output))
    
    # Trigger response generation
    await openai_ws.send(json.dumps({"type": "response.create"}))
