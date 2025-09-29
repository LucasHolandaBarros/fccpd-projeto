import json
import threading
import asyncio
import websockets
from websockets.exceptions import ConnectionClosed

def show_help():
    print("\n=== Comandos disponíveis =========================================")
    print("/username NOME       -> Define seu nome de usuário")
    print("/rooms               -> Lista todas as salas existentes")
    print("/create NOME_DA_SALA -> Cria uma nova sala")
    print("/join NOME_DA_SALA   -> Entra em uma sala")
    print("/leave               -> Sai da sala atual")
    print("/quit                -> Sai do cliente")
    print("/help                -> Mostra esta ajuda")
    print("/listusers           -> Mostra os usuários online")
    print("Qualquer outro texto será enviado como mensagem para a sala atual.")
    print("==================================================================")

class ChatClient:
    def __init__(self, uri):
        self.uri = uri
        self.running = True
        self.ws = None
        self.loop = asyncio.new_event_loop()

    def start(self):
        
        threading.Thread(target=self.loop.run_until_complete, args=(self.connect(),), daemon=True).start()
       
        threading.Thread(target=self.sender_thread, daemon=True).start()

    async def connect(self):
        async with websockets.connect(self.uri) as ws:
            self.ws = ws
            print("Conectado ao servidor.")
            show_help()
            
            threading.Thread(target=self.receiver_thread, daemon=True).start()
            
            while self.running:
                await asyncio.sleep(0.1)

    def receiver_thread(self):
        while self.running:
            try:
                
                future = asyncio.run_coroutine_threadsafe(self.ws.recv(), self.loop)
                message = future.result()  
                try:
                    data = json.loads(message)
                except Exception:
                    continue

                t = data.get('type')
                if t == 'message':
                    print(f"[{data.get('room')}] {data.get('from')}: {data.get('text')}")
                elif t == 'rooms_list':
                    salas = data.get('rooms', [])
                    print("Salas existentes:", ", ".join(salas) if salas else "Nenhuma")
                elif t == 'users_list':
                    users = data.get('users', [])
                    if not users:
                        print("Nenhum usuário online.")
                    else:
                        print("Usuários online:")
                        for u in users:
                            room = u['room'] if u['room'] else "Nenhuma sala"
                            print(f"- {u['username']} (Sala: {room})")
            except ConnectionClosed:
                print("Conexão fechada pelo servidor.")
                self.running = False
                break
            except Exception as e:
                print("Erro no receiver:", e)
                self.running = False
                break

    def sender_thread(self):
        while self.running:
            try:
                cmd = input("> ").strip()
                if not cmd:
                    continue

                if cmd.startswith('/username '):
                    uname = cmd.split(' ', 1)[1].strip()
                    asyncio.run_coroutine_threadsafe(
                        self.ws.send(json.dumps({'type':'set_username','username':uname})),
                        self.loop
                    )
                elif cmd == '/rooms':
                    asyncio.run_coroutine_threadsafe(
                        self.ws.send(json.dumps({'type':'list_rooms'})),
                        self.loop
                    )
                elif cmd == '/listusers':
                    asyncio.run_coroutine_threadsafe(
                        self.ws.send(json.dumps({'type':'list_users'})),
                        self.loop
                    )
                elif cmd.startswith('/create '):
                    room = cmd.split(' ', 1)[1].strip()
                    asyncio.run_coroutine_threadsafe(
                        self.ws.send(json.dumps({'type':'create_room','room':room})),
                        self.loop
                    )
                elif cmd.startswith('/join '):
                    room = cmd.split(' ', 1)[1].strip()
                    asyncio.run_coroutine_threadsafe(
                        self.ws.send(json.dumps({'type':'join_room','room':room})),
                        self.loop
                    )
                elif cmd == '/leave':
                    asyncio.run_coroutine_threadsafe(
                        self.ws.send(json.dumps({'type':'leave_room'})),
                        self.loop
                    )
                elif cmd == '/help':
                    show_help()
                elif cmd == '/quit':
                    print("Saindo...")
                    self.running = False
                    asyncio.run_coroutine_threadsafe(self.ws.close(), self.loop)
                    break
                else:
                    
                    asyncio.run_coroutine_threadsafe(
                        self.ws.send(json.dumps({'type':'message','text':cmd})),
                        self.loop
                    )
            except Exception as e:
                print("Erro no sender:", e)
                self.running = False
                break

if __name__ == '__main__':
    client = ChatClient('ws://localhost:8765')
    client.start()


    try:
        while client.running:
            pass
    except KeyboardInterrupt:
        client.running = False
        print("\nEncerrando cliente...")
