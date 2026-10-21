import pytest
import json
import base64
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.stream import handle_media_stream
from main import app

# Mock data
MOCK_STREAM_SID = "MZ12345"
MOCK_CALL_SID = "CA12345"

# Mock OpenAI Response Events
OPENAI_HELLO_EVENT = {
    "type": "response.audio.delta",
    "delta": base64.b64encode(b"Hello from AI").decode('utf-8')
}

OPENAI_TOOL_CALL_EVENT = {
    "type": "response.function_call_arguments.done",
    "call_id": "call_abc123",
    "name": "check_state_validity",
    "arguments": json.dumps({"state_code": "CA"})
}

# Helper to mock async iterator
async def mock_openai_stream():
    yield json.dumps(OPENAI_HELLO_EVENT)
    yield json.dumps(OPENAI_TOOL_CALL_EVENT)
    # Keep the stream open a bit longer so the app doesn't close immediately
    await asyncio.sleep(0.1)

@pytest.mark.asyncio
async def test_voice_stream_flow():
    """
    Simulates a full voice call flow:
    1. Twilio connects (WebSocket).
    2. App connects to OpenAI (Mocked).
    3. Twilio sends 'start' and 'media'.
    4. OpenAI responds with audio (Mocked).
    5. OpenAI triggers a tool call (Mocked).
    6. App executes tool and sends result back.
    """
    
    # Mock the OpenAI WebSocket connection
    mock_openai_ws = AsyncMock()
    
    # Correctly mock the async iterator
    mock_openai_ws.__aiter__.side_effect = mock_openai_stream
    
    # Mock the send method to capture what we send to OpenAI
    mock_openai_ws.send = AsyncMock()

    # We need to patch the `websockets.connect` context manager in app.stream
    with patch("app.stream.websockets.connect") as mock_connect:
        mock_connect.return_value.__aenter__.return_value = mock_openai_ws
        
        # Use FastAPI TestClient to connect to our local WebSocket endpoint
        client = TestClient(app)
        
        print("\n--- Starting Simulation ---")
        
        with client.websocket_connect("/media-stream") as websocket:
            print("[Test] Connected to /media-stream")
            
            # 1. Simulate Twilio 'start' event
            start_event = {
                "event": "start",
                "start": {
                    "streamSid": MOCK_STREAM_SID,
                    "callSid": MOCK_CALL_SID
                }
            }
            websocket.send_json(start_event)
            print("[Test] Sent Twilio 'start' event")
            
            # 2. Simulate Twilio 'media' event (User speaking)
            media_event = {
                "event": "media",
                "media": {
                    "payload": base64.b64encode(b"I live in California").decode('utf-8')
                }
            }
            websocket.send_json(media_event)
            print("[Test] Sent Twilio 'media' event (Audio)")
            
            # 3. Receive Audio from AI (Mocked response)
            # The app should forward the OPENAI_HELLO_EVENT to Twilio as a 'media' event
            try:
                response_1 = websocket.receive_json()
                print(f"[Test] Received response: {response_1}")
                assert response_1['event'] == 'media'
                assert response_1['streamSid'] == MOCK_STREAM_SID
                decoded_audio = base64.b64decode(response_1['media']['payload'])
                print(f"[Test] Decoded AI Audio: {decoded_audio}")
                assert b"Hello from AI" in decoded_audio
            except Exception as e:
                print(f"[Error] Receiving audio: {e}")
                raise

            # 4. Verify Tool Execution
            # The app processes the OPENAI_TOOL_CALL_EVENT internally.
            
            # Let's wait a brief moment for the async task to process the tool call
            await asyncio.sleep(0.2) 
            
            print("\n--- Verifying OpenAI Interactions ---")
            calls = mock_openai_ws.send.call_args_list
            
            # Print all calls for debugging
            for i, c in enumerate(calls):
                print(f"Call {i}: {c[0][0][:100]}...")

            # Verify Session Update
            assert any("session.update" in c[0][0] for c in calls)
            print("[Pass] Session Configured")
            
            # Verify Audio Sent to OpenAI
            assert any("input_audio_buffer.append" in c[0][0] for c in calls)
            print("[Pass] User Audio sent to OpenAI")
            
            # Verify Tool Output
            tool_output_call = next((c for c in calls if "function_call_output" in c[0][0]), None)
            assert tool_output_call is not None
            tool_data = json.loads(tool_output_call[0][0])
            tool_result = json.loads(tool_data['item']['output'])
            
            print(f"[Pass] Tool 'check_state_validity' Executed. Result: {tool_result}")
            assert tool_result['valid'] is True
            assert tool_result['message'] == "State is approved"

            print("\n--- Simulation Complete: Success ---")
