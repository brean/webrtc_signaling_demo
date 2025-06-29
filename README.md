# WebRTC Signaling Demo
Simple WebRTC WebSocket Signaling server with simple server, sender and receiver script.

Prototype-implementation for the [webrtc-bridge](https://github.com/brean/webrtc_bridge)

## Websocket server signaling communication
```mermaid
sequenceDiagram
    Sender-->>+Server: connects
    Note left of Server: Server generates unique_ids
    Server->>+Sender: {type: "registered", sender_id}
    Receiver-->>+Server: connects
    Server->>+Receiver: {type: "registered", receive_id}
    loop for all Sender
        Server->>+Receiver: {"type": "sender", sender_id}
    end
    Note left of Receiver: Receiver selects a sender_id
    Receiver->>+Server: {"type": "request_offer", sender_id}
    Server->>+Sender: {"type": "request_offer", receiver_id}
    Sender->>+Server: {"type": "offer", "offer": {...}, receiver_id}
    Server->>+Receiver: {"type": "offer", "offer": {...}}
    Receiver->>+Server: {"type": "answer": answer: {...}, sender_id}
    Server->>+Sender: {"type": "answer": answer: {...}}
    Sender-->>+Receiver: send video stream via aiortc (not WebSocket)
````
