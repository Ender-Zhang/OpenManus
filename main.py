import asyncio
import json
import sys
from contextlib import asynccontextmanager
from typing import List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger as loguru_logger
from pydantic import BaseModel

from app.agent.manus import Manus
from app.logger import logger


# 创建一个自定义的日志接收器
class WebSocketLogHandler:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def write(self, message):
        try:
            await self.websocket.send_json({"type": "log", "message": message.strip()})
        except Exception:
            pass


app = FastAPI(title="OpenManus API")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            # 接收 prompt
            data = await websocket.receive_json()
            prompt = data.get("prompt", "").strip()

            if not prompt:
                await websocket.send_json(
                    {"type": "error", "message": "Empty prompt provided"}
                )
                continue

            # 创建一个自定义的日志处理器
            ws_handler = WebSocketLogHandler(websocket)

            # 添加WebSocket日志处理器
            log_format = "{message}"
            loguru_logger.add(ws_handler.write, format=log_format, level="INFO")

            agent = Manus()
            try:
                await websocket.send_json(
                    {"type": "status", "message": "Processing started"}
                )

                # 运行 agent
                result = await agent.run(prompt)

                await websocket.send_json(
                    {
                        "type": "result",
                        "message": "Processing completed",
                        "data": result,
                    }
                )

            except Exception as e:
                await websocket.send_json(
                    {"type": "error", "message": f"Error processing request: {str(e)}"}
                )
            finally:
                # 清理日志处理器
                loguru_logger.remove(ws_handler.write)
                await agent.cleanup()

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
