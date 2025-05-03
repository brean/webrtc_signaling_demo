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


async def handle_track(track, receiver_id):
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
            cv2.imwrite(f"{receiver_id}_{frame_count}.png", frame)
        except asyncio.TimeoutError:
            print("Timeout waiting for frame, continuing...")
        except Exception as e:
            print(f"Error in handle_track: {str(e)}")
            if "Connection" in str(e) or str(e) == '':
                break


async def receive_video(sender_id, receiver_id, offer, websocket):
    pc = RTCPeerConnection()
    pc.addTrack(VideoTrack())

    @pc.on("track")
    def on_track(track):
        if isinstance(track, MediaStreamTrack):
            print(f"Receiving {track.kind} track")
            asyncio.ensure_future(handle_track(track, receiver_id))

    @pc.on("datachannel")
    def on_datachannel(channel):
        print(f"Data channel established: {channel.label}")

    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    await websocket.send_json({
        'type': 'answer',
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'answer': {
            'type': answer.type,
            'sdp': answer.sdp}
    })

    while pc.connectionState != "connected":
        await asyncio.sleep(0.5)


async def websocket_handler():
    """Get streaming information from WebRTC, connect to first Sender."""
    session = aiohttp.ClientSession()
    receiver_id = None
    receiving = False
    # TODO: We need some UI to select any one of the
    # server that provide RTC streams, so we can send request_offer
    # then the sender should create an offer that we can answer to
    async with session.ws_connect('ws://localhost:8080/receiver') as ws:
        async for message in ws:
            data = json.loads(message.data)
            data_type = data['type']
            if data_type == 'registered':
                receiver_id = data['receiver_id']
                print(f'registered receiver as {receiver_id}')
            elif data_type == 'sender':
                sender_id = data['sender_id']
                # TODO: for now we assume there is only ONE sender
                # however we might want to add some ui to select a
                # specific sender, for now we just request the offer
                # from the first sender we receive
                if receiving:
                    continue
                print(f'request offer from {sender_id}')
                receiving = True
                await ws.send_json({
                    'type': 'request_offer',
                    'receiver_id': receiver_id,
                    'sender_id': sender_id
                })
            elif data_type == 'offer':
                if not receiver_id:
                    print('no receiver_id set')
                    continue
                if data.get('receiver_id') != receiver_id:
                    print(
                        'reciever ids does not match: '
                        f'{data.get("receiver_id")} - {receiver_id}')
                    continue
                rtc_offer = RTCSessionDescription(**data['offer'])
                print(f'receiving video from {sender_id}')
                asyncio.create_task(receive_video(
                    sender_id, receiver_id, rtc_offer, ws))
            else:
                print(f'received unknown data type "{data_type}"')


if __name__ == '__main__':
    asyncio.run(websocket_handler())
