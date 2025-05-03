import uuid
import json
from aiohttp import web
import aiohttp

# data for clients
# active receivers (dict of receiver_id: ws)
receivers = {}
# active senders (dict of sender_id: ws)
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
        'ws': ws
    }
    # TODO: advertise new sender to receivers

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                data_type = data.get('type')
                if data_type == 'offer':
                    offer = data['offer']
                    receiver_id = data['receiver_id']
                    receiver = receivers[receiver_id]
                    print(
                        f'send offer from {sender_id} '
                        f'to {receiver_id}')
                    await receiver['ws'].send_json({
                        "sender_id": sender_id,
                        "type": "offer",
                        "receiver_id": receiver_id,
                        "offer": offer
                    })
                else:
                    print(
                        'received unknown data type from sender'
                        f' "{data_type}"')
            if msg.type == aiohttp.WSMsgType.ERROR:
                print(
                    'WS connection closed with exception '
                    f'{ws.exception()}')
    finally:
        # cleanup and inform all clients that the sender disconnected
        del senders[sender_id]
        # for ws in connected_receivers:
        #     await ws.send_json({
        #         "type": "sender_exit",
        #         "id": sender_id
        #     })


@routes.get('/receiver')
async def websocket_receiver(request):
    """Informs all connected clients about the existing sender."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    receiver_id = str(uuid.uuid4())
    await ws.send_json({
        'type': 'registered',
        'receiver_id': receiver_id,
    })
    receivers[receiver_id] = {
        'ws': ws
    }

    for sender_id, data in senders.items():
        print(f'send data of sender to receiver for {sender_id}')
        await ws.send_json({
            "type": "sender",
            "sender_id": sender_id
        })

    try:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                data_type = data.get('type')
                if data_type in ['answer', 'request_offer']:
                    # forward answer to sender
                    sender_id = data.get('sender_id')
                    sender = senders.get(sender_id)
                    sender_ws = sender['ws']
                    await sender_ws.send_json(data)
                else:
                    print(
                        'received unknown data type from receiver'
                        f' "{data_type}"')
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print(
                    'WS connection closed with exception '
                    f'{ws.exception()}')
    finally:
        del receivers[receiver_id]

    print('websocket connection closed')

    return ws


if __name__ == '__main__':
    app = web.Application()
    app.add_routes(routes)
    web.run_app(app, port=8080)
