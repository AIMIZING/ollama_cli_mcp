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

if __name__ == "__main__":
    dlog("MCP server starting (stdio)…")
    mcp.run()
