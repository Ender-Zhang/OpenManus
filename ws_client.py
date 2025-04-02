"""
Author: Ender-Zhang 102596313+Ender-Zhang@users.noreply.github.com
Date: 2025-04-01 22:26:35
LastEditors: Ender-Zhang 102596313+Ender-Zhang@users.noreply.github.com
LastEditTime: 2025-04-01 22:26:41
FilePath: /OpenManus/ws_client.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List, Optional

import uvicorn
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

app = FastAPI(title="Manus Proxy API")


# 存储所有的日志
class LogStorage:
    def __init__(self):
        self.logs: Dict[str, List[Dict]] = {}

    def add_log(
        self, session_id: str, log_type: str, message: str, data: Optional[dict] = None
    ):
        if session_id not in self.logs:
            self.logs[session_id] = []

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": log_type,
            "message": message,
        }
        if data:
            log_entry["data"] = data

        self.logs[session_id].append(log_entry)

    def get_logs(self, session_id: Optional[str] = None):
        if session_id:
            return self.logs.get(session_id, [])
        return self.logs


log_storage = LogStorage()


class PromptRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


async def connect_to_manus(
    prompt: str, session_id: str, websocket: Optional[WebSocket] = None
):
    """连接到 Manus 服务器并处理消息"""
    try:
        async with websockets.connect("ws://localhost:8000/ws") as ws:
            # 发送 prompt 到 Manus
            await ws.send(json.dumps({"prompt": prompt}))

            # 接收并处理消息
            while True:
                response = await ws.recv()
                data = json.loads(response)

                # 保存日志
                log_storage.add_log(
                    session_id=session_id,
                    log_type=data["type"],
                    message=data.get("message", ""),
                    data=data.get("data"),
                )

                # 如果有 WebSocket 连接，转发消息
                if websocket:
                    await websocket.send_json(data)

                # 如果收到结果或错误，结束处理
                if data["type"] in ["result", "error"]:
                    break

    except Exception as e:
        error_message = f"Error connecting to Manus: {str(e)}"
        log_storage.add_log(session_id, "error", error_message)
        if websocket:
            await websocket.send_json({"type": "error", "message": error_message})


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 端点，实时转发 Manus 的消息"""
    await websocket.accept()

    try:
        # 等待接收 prompt
        data = await websocket.receive_json()
        prompt = data.get("prompt", "").strip()

        if not prompt:
            await websocket.send_json(
                {"type": "error", "message": "Empty prompt provided"}
            )
            return

        # 连接到 Manus 并处理消息
        await connect_to_manus(prompt, session_id, websocket)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "message": str(e)})


@app.post("/process/{session_id}")
async def process_prompt(session_id: str, request: PromptRequest):
    """HTTP 端点，异步处理请求"""
    if not request.prompt.strip():
        return {"error": "Empty prompt provided"}

    # 在后台任务中处理请求
    asyncio.create_task(connect_to_manus(request.prompt, session_id))

    return {"message": "Request accepted", "session_id": session_id}


@app.get("/logs")
async def get_logs(session_id: Optional[str] = None):
    """获取日志端点"""
    return log_storage.get_logs(session_id)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
