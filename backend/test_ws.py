import asyncio
import websockets
import json
import sys

async def test_ws(conversation_id: str):
    uri = f"ws://localhost:8000/ws/chat/{conversation_id}"
    async with websockets.connect(uri) as ws:
        # First message should be the history push
        history = await ws.recv()
        print("HISTORY:", json.dumps(json.loads(history), indent=2, ensure_ascii=False))

        # Send a test agent message
        await ws.send(json.dumps({
            "role": "agent",
            "content": "Hello, this is a test agent message.",
            "agent_id": 1
        }))

        # Should receive the broadcast of that same message back
        response = await ws.recv()
        print("BROADCAST:", json.dumps(json.loads(response), indent=2, ensure_ascii=False))

if __name__ == "__main__":
    conv_id = sys.argv[1]
    asyncio.run(test_ws(conv_id))