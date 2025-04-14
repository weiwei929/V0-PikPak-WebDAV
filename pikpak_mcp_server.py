import asyncio
import logging
import os
import argparse
import sys
import uvicorn
from fastapi import FastAPI

# 检查 MCP 包的结构
print("Python 版本:", sys.version)
print("Python 路径:", sys.executable)
print("模块搜索路径:", sys.path)

try:
    import mcp
    print("MCP 版本:", mcp.__version__ if hasattr(mcp, "__version__") else "未知")
    print("MCP 路径:", mcp.__file__)
    print("MCP 内容:", dir(mcp))
except ImportError as e:
    print("导入 mcp 失败:", e)

# 使用 FastAPI 创建一个简单的 MCP 兼容服务器
app = FastAPI(
    title="PikPak-MCP",
    description="一个简单的 MCP 服务器示例",
    version="0.1.0",
)

# 添加文本补全路由
@app.post("/v1/completions")
async def text_completion(request: dict):
    """处理文本补全请求"""
    prompt = request.get("prompt", "")
    logging.info(f"收到文本补全请求: {prompt}")
    
    # 这里只是一个简单的演示响应
    response_text = f"你好！我是 PikPak-MCP 服务器。你发送的请求是: {prompt}"
    
    return {
        "id": "cmpl-" + os.urandom(4).hex(),
        "object": "text_completion",
        "created": int(asyncio.get_event_loop().time()),
        "model": "pikpak-mcp-demo-model",
        "choices": [
            {
                "text": response_text,
                "index": 0,
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(prompt),
            "completion_tokens": len(response_text),
            "total_tokens": len(prompt) + len(response_text)
        }
    }

# 添加模型信息
@app.get("/v1/models")
async def models():
    """返回可用模型的列表"""
    return {
        "object": "list",
        "data": [
            {
                "id": "pikpak-mcp-demo-model",
                "object": "model",
                "created": 1712345678,
                "owned_by": "pikpak"
            }
        ]
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="启动 PikPak MCP 服务器")
    parser.add_argument("--host", type=str, default="localhost", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8080, help="服务器端口")
    args = parser.parse_args()
    
    print(f"启动 MCP 服务器在 http://{args.host}:{args.port}")
    
    # 使用 uvicorn 启动服务器
    uvicorn.run(app, host=args.host, port=args.port)