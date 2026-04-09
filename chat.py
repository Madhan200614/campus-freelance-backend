from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict
from database import get_db
from models import Message
from jobs import get_current_user
from jose import jwt, JWTError
from auth import SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/chat", tags=["Chat"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_message(self, user_id: int, message: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_text(message)

manager = ConnectionManager()

def get_user_from_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return int(user_id)
    except JWTError:
        return None

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
    db: Session = Depends(get_db)
):
    user_id = get_user_from_token(token)
    if not user_id:
        await websocket.close()
        return

    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            receiver_id = data.get("receiver_id")
            content = data.get("content")

            if not receiver_id or not content:
                continue

            message = Message(
                sender_id=user_id,
                receiver_id=receiver_id,
                content=content
            )
            db.add(message)
            db.commit()

            await manager.send_message(
                receiver_id,
                f'{{"sender_id": {user_id}, "content": "{content}"}}'
            )

            await manager.send_message(
                user_id,
                f'{{"sender_id": {user_id}, "content": "{content}", "status": "sent"}}'
            )

    except WebSocketDisconnect:
        manager.disconnect(user_id)

@router.get("/history/{other_user_id}")
def get_chat_history(other_user_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    messages = db.query(Message).filter(
        ((Message.sender_id == user_id) & (Message.receiver_id == other_user_id)) |
        ((Message.sender_id == other_user_id) & (Message.receiver_id == user_id))
    ).order_by(Message.created_at).all()
    return messages