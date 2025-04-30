import uuid
import json
from aiohttp import web
import aiohttp

# data for clients
# active receivers (set of websockets)
connected_receivers = set()
# active senders (dict of sender_id: (hash, offer))
senders = {}

routes = web.RouteTableDef()


@routes.get('/sender')
async def websocket_sender(request):
    """A new sender connects, we store its offer."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    sender_id = str(uuid.uuid4())
    await ws.send_json({
        'type': 'registered',
        'sender_id': sender_id,
    })
    senders[sender_id] = {
        'ws': ws,
        'offer': None
    }

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                data_type = data.get('type')
                if data_type == 'offer':
                    offer = data['offer']
                    senders[sender_id]['offer'] = offer
                    for rec_ws in connected_receivers:
                        await rec_ws.send_json({
                            "type": "sender",
                            "sender_id": sender_id,
                            "offer": offer
                        })
            if msg.type == aiohttp.WSMsgType.ERROR:
                print(
                    'WS connection closed with exception '
                    f'{ws.exception()}')
    finally:
        # cleanup and inform all clients that the sender disconnected
        del senders[sender_id]
        for ws in connected_receivers:
            await ws.send_json({
                "type": "sender_exit",
                "id": sender_id
            })


@routes.get('/receiver')
async def websocket_receiver(request):
    """Informs all connected clients about the existing sender."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    for sender_id, data in senders.items():
        if not data.get('offer'):
            continue
        offer = data.get('offer')
        await ws.send_json({
            "type": "sender",
            "sender_id": sender_id,
            "offer": offer
        })

    connected_receivers.add(ws)

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get('type') == 'answer':
                    # forward answer to sender
                    sender_id = data.get('sender_id')
                    sender = senders.get(sender_id)
                    sender_ws = sender['ws']
                    await sender_ws.send_json(data)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(
                    'WS connection closed with exception '
                    f'{ws.exception()}')
    finally:
        connected_receivers.remove(ws)

    print('websocket connection closed')

    return ws


if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8080)
