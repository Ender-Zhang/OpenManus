"""
Author: Ender-Zhang 102596313+Ender-Zhang@users.noreply.github.com
Date: 2025-04-01 23:04:28
LastEditors: Ender-Zhang 102596313+Ender-Zhang@users.noreply.github.com
LastEditTime: 2025-04-01 23:06:59
FilePath: /OpenManus/test_http_client.py
Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
"""

import asyncio
import json
import time
from datetime import datetime

import aiohttp
import requests


async def test_process_and_logs():
    # 生成唯一的会话ID
    session_id = f"test_{int(time.time())}"
    base_url = "http://localhost:8001"

    print(f"\n=== 开始测试 会话ID: {session_id} ===\n")

    # 1. 发送处理请求
    print("1. 发送处理请求...")
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/process/{session_id}",
            json={"prompt": "帮我总结一下最近的新闻"},
        ) as response:
            result = await response.json()
            print(f"处理请求响应: {json.dumps(result, ensure_ascii=False, indent=2)}")

    # 2. 等待一段时间让处理完成
    print("\n等待处理完成 (10秒)...")
    await asyncio.sleep(10)

    # 3. 获取日志
    print("\n2. 获取特定会话的日志...")
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{base_url}/logs", params={"session_id": session_id}
        ) as response:
            logs = await response.json()
            print(f"\n会话 {session_id} 的日志:")
            print(json.dumps(logs, ensure_ascii=False, indent=2))

    # 4. 获取所有日志
    print("\n3. 获取所有日志...")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/logs") as response:
            all_logs = await response.json()
            print("\n所有会话的日志数量:", len(all_logs))
            print("所有会话ID:", list(all_logs.keys()))


def main():
    print("开始HTTP端点测试...")
    asyncio.run(test_process_and_logs())
    print("\n测试完成!")


if __name__ == "__main__":
    main()
