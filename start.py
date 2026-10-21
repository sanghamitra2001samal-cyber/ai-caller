import os
import uvicorn
import threading
from pyngrok import ngrok, conf
from dotenv import load_dotenv

load_dotenv()

def start_tunnel():
    """
    Starts an ngrok tunnel to localhost:8000 and prints the public URL.
    """
    # Check if NGROK_AUTH_TOKEN is set in .env, otherwise it might fail or use restricted session
    auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if auth_token:
        conf.get_default().auth_token = auth_token
    
    # Open a HTTP tunnel on the default port 8000
    # The 'bind_tls=True' forces HTTPS, which Twilio requires for Media Streams
    public_url = ngrok.connect(8000, bind_tls=True).public_url
    print("\n" + "="*60)
    print(f"🚀 PUBLIC URL GENERATED: {public_url}")
    print(f"👉 Copy this URL to your Twilio Phone Number 'Voice Webhook' field:")
    print(f"   {public_url}/voice/incoming")
    print("="*60 + "\n")
    return public_url

if __name__ == "__main__":
    print("Starting BeepBoost AI Caller System...")
    
    try:
        # Start ngrok tunnel
        url = start_tunnel()
        
        # Start Uvicorn Server
        # We run it directly here. It blocks the main thread, which is fine.
        # Ngrok runs in a separate thread/process managed by pyngrok.
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
        
    except KeyboardInterrupt:
        print("Shutting down...")
        ngrok.kill()
