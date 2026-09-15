import asyncio
import websockets
import json
import sys

async def test_presence(agent_id: str):
    uri = f"ws://localhost:8000/ws/agent/{agent_id}"
    async with websockets.connect(uri) as ws:
        print("Connected - agent should now be 'online'. Check the DB now.")
        input("Press Enter to send a 'busy' status update...")

        await ws.send(json.dumps({"status": "busy"}))
        print("Sent busy status. Check the DB now.")
        input("Press Enter to disconnect (agent should go 'offline')...")

if __name__ == "__main__":
    agent_id = sys.argv[1]
    asyncio.run(test_presence(agent_id))