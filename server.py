import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from datetime import datetime

rooms = {}   
clients = {} 

def get_timestamp():
    return datetime.now().strftime("%H:%M")

async def notify_room(room, message):
    if room not in rooms:
        return
    webs = list(rooms[room])
    if not webs:
        return
    data = json.dumps(message)
    await asyncio.gather(*[w.send(data) for w in webs], return_exceptions=True)

async def handle_message(ws, raw):
    try:
        msg = json.loads(raw)
    except Exception:
        await ws.send(json.dumps({"type": "error", "message": "json inválido"}))
        return

    t = msg.get("type")
    username = clients[ws].get("username") or "anon"

    if t == "set_username":
        uname = msg.get("username")
        old_name = username
        clients[ws]["username"] = uname
        print(f"[{get_timestamp()}] {old_name} mudou username para '{uname}'")
        await ws.send(json.dumps({"type": "username_set", "username": uname}))

    elif t == "list_rooms":
        print(f"[{get_timestamp()}] {username} solicitou lista de salas (total: {len(rooms)})")
        await ws.send(json.dumps({"type": "rooms_list", "rooms": list(rooms.keys())}))

    elif t == "create_room":
        room = msg.get("room")
        if not room:
            await ws.send(json.dumps({"type": "error", "message": "nome de sala vazio"}))
            return
        if room in rooms:
            await ws.send(json.dumps({"type": "error", "message": "sala já existe"}))
            return
        rooms[room] = set()
        print(f"[{get_timestamp()}] {username} criou a sala '{room}' (salas totais: {len(rooms)})")
        await ws.send(json.dumps({"type": "room_created", "room": room}))

    elif t == "join_room":
        room = msg.get("room")
        if room not in rooms:
            await ws.send(json.dumps({"type": "error", "message": "sala não existe"}))
            return
        prev = clients[ws]["room"]
        if prev:
            rooms[prev].discard(ws)
            await notify_room(prev, {"type": "user_left", "room": prev, "username": username})
            print(f"[{get_timestamp()}] {username} saiu da sala '{prev}' (usuários na sala: {len(rooms[prev])})")
        
        rooms[room].add(ws)
        clients[ws]["room"] = room
        await ws.send(json.dumps({"type": "joined", "room": room}))
        await notify_room(room, {"type": "user_joined", "room": room, "username": username})
        print(f"[{get_timestamp()}] {username} entrou na sala '{room}' (usuários na sala: {len(rooms[room])})")

    elif t == "leave_room":
        room = clients[ws]["room"]
        if room:
            rooms[room].discard(ws)
            clients[ws]["room"] = None
            await ws.send(json.dumps({"type": "left", "room": room}))
            await notify_room(room, {"type": "user_left", "room": room, "username": username})
            print(f"[{get_timestamp()}] {username} saiu da sala '{room}' (usuários restantes: {len(rooms[room])})")
        else:
            await ws.send(json.dumps({"type": "error", "message": "não está em nenhuma sala"}))
    
    elif t == "list_users":
        
        users_list = [
            {"username": info.get("username") or "anon", "room": info.get("room")}
            for info in clients.values()
        ]
        await ws.send(json.dumps({"type": "users_list", "users": users_list}))
        print(f"[{get_timestamp()}] {username} solicitou lista de usuários online")

    elif t == "message":
        room = clients[ws]["room"]
        if not room:
            await ws.send(json.dumps({"type": "error", "message": "entre em uma sala para enviar mensagens"}))
            return
        text = msg.get("text", "")
        outgoing = {"type": "message", "room": room, "from": username, "text": text}
        await notify_room(room, outgoing)
        print(f"[{get_timestamp()}] [{room}] {username}: {text}")

    else:
        await ws.send(json.dumps({"type": "error", "message": "tipo de mensagem desconhecido"}))

async def register(ws):
    clients[ws] = {"username": None, "room": None}
    print(f"[{get_timestamp()}] Novo cliente conectado. Total de clientes: {len(clients)}")

async def unregister(ws):
    info = clients.get(ws)
    if not info:
        return
    room = info.get("room")
    username = info.get("username") or "anon"
    if room and room in rooms:
        rooms[room].discard(ws)
        await notify_room(room, {"type": "user_left", "room": room, "username": username})
        print(f"[{get_timestamp()}] {username} removido da sala '{room}' (usuários restantes: {len(rooms[room])})")
    
    del clients[ws]
    print(f"[{get_timestamp()}] Cliente desconectado: {username}. Total de clientes: {len(clients)}")

async def ws_handler(ws):
    await register(ws)
    try:
        async for message in ws:
            await handle_message(ws, message)
    except (ConnectionClosedOK, ConnectionClosedError) as e:
        print(f"[{get_timestamp()}] Conexão fechada normalmente: {e}")
    except Exception as e:
        print(f"[{get_timestamp()}] Erro inesperado: {e}")
    finally:
        await unregister(ws)

async def main():
    async with websockets.serve(
        ws_handler, 
        '0.0.0.0', 
        8765,
        ping_interval=20,
        ping_timeout=10,
        close_timeout=10
    ):
        print(f"[{get_timestamp()}] Servidor WebSocket rodando em ws://localhost:8765")
        await asyncio.Future()  

if __name__ == '__main__':
    asyncio.run(main())