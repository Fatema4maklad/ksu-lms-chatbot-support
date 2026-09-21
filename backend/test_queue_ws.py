import asyncio
import websockets
import json

async def listen():
    uri = "ws://localhost:8000/ws/agent/queue"
    async with websockets.connect(uri) as ws:
        print("Connected to queue WebSocket. Waiting for a new escalation...")
        print("(Now go trigger an escalation in the browser chat, in a NEW conversation)")
        message = await ws.recv()
        print("RECEIVED:", json.dumps(json.loads(message), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(listen())