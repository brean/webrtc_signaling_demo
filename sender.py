import asyncio
import json
import cv2
import aiohttp
import asyncio
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import fractions


class VideoTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        self.cap = cv2.VideoCapture(0)
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


async def send_offer(ws, offer):
    offer_msg = {
        "type": "offer",
        "offer": {
            "sdp": offer.sdp,
            "type": offer.type
        }
    }
    await ws.send_json(offer_msg)


async def websocket_handler(url: str):
    # create websocket session
    session = aiohttp.ClientSession()
    try:
        async with session.ws_connect(f'{url}sender') as ws:
            async for message in ws:
                data = json.loads(message.data)
                data_type = data.get('type')
                if data_type == 'registered':
                    sender_id = data['sender_id']
                    print(f'new sender registered {sender_id}')
                elif data_type == 'request_offer':
                    if not sender_id:
                        return
                    pc = RTCPeerConnection()
                    video_track = VideoTrack()
                    pc.addTrack(video_track)
                    # create WebRTC-offer
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    await send_offer(ws, offer)
                elif data_type == 'answer':
                    rsd = RTCSessionDescription(
                        data.get('sdp'), data.get('type'))
                    await pc.setRemoteDescription(rsd)
                    # TODO: loop and send next stream!

    except KeyboardInterrupt:
        print('Keyboard Interrupt, exiting...')
    finally:
        await pc.close()

if __name__ == '__main__':
    url = 'http://127.0.0.1:8080/'
    asyncio.run(websocket_handler(url=url))
