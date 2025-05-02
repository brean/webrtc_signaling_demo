import aiohttp
import json
import asyncio

from av import VideoFrame
import numpy as np
import cv2

from aiortc import \
    MediaStreamTrack, VideoStreamTrack, \
    RTCPeerConnection, RTCSessionDescription


class VideoTrack(VideoStreamTrack):
    """Custom VideoTrack handling."""
    async def recv(self):
        frame = await self.recv()
        return frame


async def handle_track(track, sender_id):
    frame_count = 0
    while True:
        try:
            print('wait for track')
            frame = await asyncio.wait_for(track.recv(), timeout=5.0)
            frame_count += 1
            print(f'received frame {frame_count}')
            # self.get_logger().info(f"Received frame {frame_count}")
            if isinstance(frame, VideoFrame):
                frame = frame.to_ndarray(format="rgb24")
            elif isinstance(frame, np.ndarray):
                print("Frame type: numpy array")
            else:
                print(
                    f"Unexpected frame type: {type(frame)}")
                continue
            cv2.imwrite(f"{sender_id}_{frame_count}.png", frame)
        except asyncio.TimeoutError:
            print("Timeout waiting for frame, continuing...")
        except Exception as e:
            print(f"Error in handle_track: {str(e)}")
            if "Connection" in str(e) or str(e) == '':
                break


async def receive_video(sender_id, offer, websocket):
    pc = RTCPeerConnection()
    pc.addTrack(VideoTrack())

    @pc.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack):
            print(f"Receiving {track.kind} track")
            asyncio.ensure_future(handle_track(track, sender_id))

    @pc.on("datachannel")
    def on_datachannel(channel):
        print(f"Data channel established: {channel.label}")

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await websocket.send_json({
        'type': 'answer',
        'sender_id': sender_id,
        'sdp': answer.sdp
    })

    while pc.connectionState != "connected":
        await asyncio.sleep(0.5)


async def websocket_handler():
    """Get streaming information from WebRTC, connect to first Sender."""
    session = aiohttp.ClientSession()
    # TODO: We need some UI to select any one of the
    # server that provide RTC streams, so we can send request_offer
    # then the sender should create an offer that we can answer to
    async with session.ws_connect('ws://localhost:8080/receiver') as ws:
        async for message in ws:
            data = json.loads(message.data)
            if data['type'] == 'sender':
                sender_id = data['sender_id']
                rtc_offer = RTCSessionDescription(**data['offer'])
                asyncio.create_task(
                    receive_video(sender_id, rtc_offer, ws))
                print(f'connect to {sender_id}')


if __name__ == '__main__':
    asyncio.run(websocket_handler())
