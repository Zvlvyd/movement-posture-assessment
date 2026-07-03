import asyncio, json, urllib.request, urllib.error

# Login
login_data = json.dumps({"username": "test", "password": "test123"}).encode()
req = urllib.request.Request("http://localhost:8002/api/auth/login", data=login_data, headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
token = data["access_token"]
print("Token obtained")

async def test():
    import websockets
    # Test via Vite proxy (port 5173)
    uri = f"ws://localhost:5173/api/assessment/ws?token={token}"
    print("WS via proxy:", uri)
    try:
        async with websockets.connect(uri, close_timeout=5) as ws:
            print("WS via proxy Connected!")
            await ws.send(json.dumps({"type": "start"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print("Received:", msg[:200])
    except Exception as e:
        print("WS via proxy Error:", type(e).__name__, str(e)[:200])

asyncio.run(test())
