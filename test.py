import asyncio
import websockets

async def test():
    uri = "ws://127.0.0.1:8000/posts/<slug>/comments/"   # өз URL-іңізді қойыңыз
    async with websockets.connect(uri) as websocket:
        print("✅ Connected")
        await websocket.send('{"type": "test_message"}')
        response = await websocket.recv()
        print(f"📩 Received: {response}")

asyncio.run(test())