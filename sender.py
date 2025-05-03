import asyncio
import json
import cv2
import aiohttp
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import fractions


class VideoTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(1)
        self.frame_count = 0

    async def recv(self):
        self.frame_count += 1
        ret, frame = self.cap.read()
        if not ret:
            print('Failed to read frame from camera.')
            return None
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = self.frame_count
        video_frame.time_base = fractions.Fraction(1, 30)
        return video_frame


async def send_offer(ws, offer, receiver_id):
    offer_msg = {
        "type": "offer",
        "receiver_id": receiver_id,
        "offer": {
            "sdp": offer.sdp,
            "type": offer.type
        }
    }
    await ws.send_json(offer_msg)


async def websocket_handler(url: str):
    # create websocket session
    video_track = VideoTrack()
    session = aiohttp.ClientSession()
    pcs = {}
    try:
        async with session.ws_connect(f'{url}sender') as ws:
            async for message in ws:
                data = json.loads(message.data)
                data_type = data.get('type')
                if data_type == 'registered':
                    sender_id = data['sender_id']
                    print(f'registered sender as {sender_id}')
                elif data_type == 'request_offer':
                    if not sender_id:
                        print('ERROR: no sender')
                        continue
                    receiver_id = data.get('receiver_id')
                    if not receiver_id:
                        print('ERROR: no receiver_id')
                        continue
                    pc = RTCPeerConnection()
                    pc.addTrack(video_track)
                    pcs[receiver_id] = pc
                    # create WebRTC-offer
                    # TODO save pc-connction somewhere to control it.
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    print(f'send offer to {receiver_id}')
                    await send_offer(ws, pc.localDescription, receiver_id)
                elif data_type == 'answer':
                    receiver_id = data.get('receiver_id')
                    if not receiver_id:
                        print('ERROR: no receiver_id')
                        continue
                    answer = data['answer']
                    rsd = RTCSessionDescription(
                        answer.get('sdp'), answer.get('type'))
                    
                    await pcs[receiver_id].setRemoteDescription(rsd)
                    print(f'answer handled for {receiver_id}')
                else:
                    print(f'received unknown data type "{data_type}"')

    except KeyboardInterrupt:
        print('Keyboard Interrupt, exiting...')
    finally:
        await pc.close()

if __name__ == '__main__':
    url = 'http://127.0.0.1:8080/'
    asyncio.run(websocket_handler(url=url))
