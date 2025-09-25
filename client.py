# client.py
import asyncio
import json
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

async def cli(uri):
    try:
        async with websockets.connect(
            uri,
            ping_interval=10,
            ping_timeout=5,
            close_timeout=5
        ) as ws:
            print("Conectado ao servidor.")
            show_help()

            running = True

            async def receiver():
                nonlocal running
                try:
                    while running:
                        try:
                            message = await ws.recv()
                            try:
                                data = json.loads(message)
                            except Exception:
                                continue

                            t = data.get('type')
                            if t == 'message':
                                # Mensagens de outros clientes
                                print(f"[{data.get('room')}] {data.get('from')}: {data.get('text')}")
                            elif t == 'rooms_list':
                                salas = data.get('rooms', [])
                                print("Salas existentes:", ", ".join(salas) if salas else "Nenhuma")
                            # ignora todos os outros tipos
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
                            running = False
                            break
                        except Exception:
                            running = False
                            break
                except Exception:
                    running = False

            async def sender():
                nonlocal running
                loop = asyncio.get_event_loop()
                try:
                    while running:
                        try:
                            # Input **não-bloqueante confiável**
                            cmd = await loop.run_in_executor(None, input, '> ')
                            cmd = cmd.strip()
                            if not cmd:
                                continue

                            if cmd.startswith('/username '):
                                parts = cmd.split(' ', 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    print("Uso: /username NOME")
                                    continue
                                uname = parts[1].strip()
                                await ws.send(json.dumps({'type':'set_username','username':uname}))

                            elif cmd == '/rooms':
                                await ws.send(json.dumps({'type':'list_rooms'}))
                            
                            elif cmd == '/listusers':
                                await ws.send(json.dumps({'type':'list_users'}))

                            elif cmd.startswith('/create '):
                                parts = cmd.split(' ', 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    print("Uso: /create NOME_DA_SALA")
                                    continue
                                room = parts[1].strip()
                                await ws.send(json.dumps({'type':'create_room','room':room}))

                            elif cmd.startswith('/join '):
                                parts = cmd.split(' ', 1)
                                if len(parts) < 2 or not parts[1].strip():
                                    print("Uso: /join NOME_DA_SALA")
                                    continue
                                room = parts[1].strip()
                                await ws.send(json.dumps({'type':'join_room','room':room}))

                            elif cmd == '/leave':
                                await ws.send(json.dumps({'type':'leave_room'}))

                            elif cmd == '/quit':
                                print('Saindo...')
                                running = False
                                await ws.close()
                                break

                            elif cmd == '/help':
                                show_help()

                            else:
                                await ws.send(json.dumps({'type':'message','text':cmd}))

                        except ConnectionClosed:
                            print("\nNão é possível enviar mensagens - conexão fechada")
                            running = False
                            break
                        except Exception as e:
                            print('Erro no sender:', e)
                            running = False
                            break
                except Exception as e:
                    print('Erro fatal no sender:', e)
                    running = False

            # Executa receiver e sender em paralelo
            await asyncio.gather(
                receiver(),
                sender(),
                return_exceptions=True
            )

    except Exception as e:
        print("Erro ao conectar ou manter a conexão:", e)

if __name__ == '__main__':
    asyncio.run(cli('ws://localhost:8765'))
