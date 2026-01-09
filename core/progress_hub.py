# core/progress_hub.py
import json
from websocket_server import WebsocketServer

_clients = set()          # 只放 client['id'] 整数

def _new_client(client, server):
    _clients.add(client['id'])          # 只记录 id
    pass

def _client_left(client, server):
    _clients.discard(client['id'])      # 只删 id
    pass

def _msg_received(client, server, msg):
    pass   # 目前纯广播，不处理上行

def start_hub():
    hub = WebsocketServer(port=8001, host='0.0.0.0')
    hub.set_fn_new_client(_new_client)
    hub.set_fn_client_left(_client_left)
    hub.set_fn_message_received(_msg_received)
    hub.run_forever(threaded=True)
    return hub

def broadcast(data: dict):
    msg = json.dumps(data, ensure_ascii=False)
    # hub 存到 server 里，用内部方法发
    hub = WebsocketServer.websocket_servers.get(('', 8001))
    if not hub: return
    for cid in list(_clients):
        client = hub.clients.get(cid)
        if client:
            try:
                hub.send_message(client, msg)
            except Exception as e:
                print('[ProgressHub] 广播失败', e)
                _clients.discard(cid)