# mcp_server.py
import os, sys
from datetime import datetime
from fastmcp import FastMCP

DEBUG = os.environ.get("DEBUG", "0") == "1"

def dlog(msg: str) -> None:
    if DEBUG:
        # ✔️ 반드시 stderr로만 로그 출력 (stdout은 프로토콜 전용)
        print(f"[mcp_server][{datetime.now().isoformat()}] {msg}", file=sys.stderr, flush=True)

mcp = FastMCP("demo-mcp-server")

@mcp.tool
def get_time() -> str:
    """현재 로컬 시간을 ISO 포맷 문자열로 반환합니다."""
    dlog("tool=get_time called")
    return datetime.now().isoformat()

@mcp.tool
def read_text(path: str) -> str:
    """파일 경로를 입력받아 텍스트 내용을 반환합니다."""
    dlog(f"tool=read_text called args={{'path': '{path}'}}")
    if not os.path.exists(path):
        msg = f"파일이 존재하지 않습니다: {path}"
        dlog(f"tool=read_text error: {msg}")
        raise FileNotFoundError(msg)
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    dlog(f"tool=read_text ok, bytes={len(data.encode('utf-8'))}")
    return data

if __name__ == "__main__":
    dlog("MCP server starting (stdio)…")
    mcp.run()
