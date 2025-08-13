# bridge_http.py
import os, json, shlex, asyncio, requests, sys
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

# ── 설정 ─────────────────────────────────────────────────────
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:20b")
DEBUG = os.environ.get("DEBUG", "0") == "1"

def dlog(msg: str) -> None:
    if DEBUG:
        print(f"[bridge][{datetime.now().isoformat()}] {msg}", flush=True)

# ── MCP(stdio) ───────────────────────────────────────────────
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
SERVER_PY = HERE / "mcp_server.py"

# ✔️ UTF-8 강제 + 무버퍼
DEFAULT_SERVER_CMD = f'"{sys.executable}" -X utf8 -u "{SERVER_PY}"'
MCP_SERVER_CMD = os.environ.get("MCP_SERVER_CMD", DEFAULT_SERVER_CMD)

SYSTEM_PROMPT = (
    "당신은 도구 사용이 가능한 보조 모델입니다. "
    "정확한 정보(현재 시각, 파일 내용 등)가 필요하면 함수 호출을 사용하고, "
    "필요 없으면 바로 답변을 생성합니다. "
    "도구 결과를 반영해 자연스러운 한국어로 답변합니다."
)

# ── Ollama HTTP chat ─────────────────────────────────────────
def ollama_chat(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    payload = {"model": MODEL, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    dlog(f"Ollama /api/chat request: msgs={len(messages)}, tools={len(tools) if tools else 0}")
    r = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload, timeout=120)
    r.raise_for_status()
    resp = r.json()
    content_preview = (resp.get("message", {}).get("content") or "")[:120].replace("\n", " ")
    dlog(f"Ollama response: content_preview='{content_preview}'")
    return resp

def extract_tool_calls(resp: Dict[str, Any]) -> List[Dict[str, Any]]:
    calls: List[Dict[str, Any]] = []
    msg = resp.get("message", {})
    # OpenAI 호환 tool_calls
    for tc in msg.get("tool_calls") or []:
        fn = (tc or {}).get("function", {})
        name = fn.get("name")
        args_raw = fn.get("arguments")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
        except json.JSONDecodeError:
            args = {}
        if name:
            calls.append({"name": name, "arguments": args})
    # 백업: content에 JSON이 온 경우
    if not calls:
        content = msg.get("content") or ""
        try:
            maybe = json.loads(content)
            if isinstance(maybe, dict) and "tool" in maybe:
                calls.append({"name": maybe["tool"], "arguments": maybe.get("args", {})})
        except Exception:
            pass
    dlog(f"extracted tool_calls: {calls}")
    return calls

def build_tools_schema(mcp_tools: List[Any]) -> List[Dict[str, Any]]:
    schema = []
    for t in mcp_tools:
        schema.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema or {"type": "object", "properties": {}},
            },
        })
    dlog(f"built tools schema count={len(schema)}")
    return schema

def content_to_text(items: Optional[List[Any]]) -> str:
    if not items:
        return ""
    parts: List[str] = []
    for c in items:
        try:
            if hasattr(c, "text"):
                parts.append(getattr(c, "text") or "")
            elif isinstance(c, dict) and "text" in c:
                parts.append(str(c.get("text") or ""))
            else:
                parts.append(str(c))
        except Exception:
            parts.append(str(c))
    return "\n".join(parts).strip()

# ── 한 턴 처리: 툴콜 루프 포함 ───────────────────────────────
def run_turn(messages: List[Dict[str, Any]], tools_schema: List[Dict[str, Any]], session: ClientSession) -> None:
    """messages 끝에 마지막 user가 들어와 있다고 가정. 이 턴의 assistant 최종 답변까지 messages에 누적."""
    max_hops = 5
    for hop in range(1, max_hops + 1):
        dlog(f"hop={hop} -> ask model")
        resp = ollama_chat(messages, tools=tools_schema)
        msg = resp.get("message", {})
        if msg.get("content"):
            preview = msg["content"][:120].replace("\n", " ")
            dlog(f"assistant draft: '{preview}'")
            messages.append({"role": "assistant", "content": msg["content"]})

        calls = extract_tool_calls(resp)
        if not calls:
            dlog("no tool calls -> finish turn")
            break

        # 여러 툴콜 순차 처리
        for call in calls:
            name = call["name"]
            args = call.get("arguments", {})
            dlog(f"call MCP tool: name={name}, args={args}")
            # MCP 호출 (동기식: 현재 스레드에서 await 불가하므로 run_until_complete를 사용할 수 없어,
            # 이 함수는 main 이벤트 루프 내부에서 호출되어야 합니다. → main에서 wrapper로 호출)
            raise RuntimeError("run_turn should be called via run_turn_async inside the event loop")

async def run_turn_async(messages: List[Dict[str, Any]], tools_schema: List[Dict[str, Any]], session: ClientSession) -> None:
    max_hops = 5
    for hop in range(1, max_hops + 1):
        dlog(f"hop={hop} -> ask model")
        resp = ollama_chat(messages, tools=tools_schema)
        msg = resp.get("message", {})
        if msg.get("content"):
            preview = msg["content"][:120].replace("\n", " ")
            dlog(f"assistant draft: '{preview}'")
            messages.append({"role": "assistant", "content": msg["content"]})

        calls = extract_tool_calls(resp)
        if not calls:
            dlog("no tool calls -> finish turn")
            break

        for call in calls:
            name = call["name"]
            args = call.get("arguments", {})
            dlog(f"call MCP tool: name={name}, args={args}")
            result = await session.call_tool(name, args)
            tool_text = content_to_text(getattr(result, "content", None))
            dlog(f"MCP result len={len(tool_text)} preview='{tool_text[:120].replace(chr(10), ' ')}'")
            messages.append({"role": "tool", "name": name, "content": tool_text if tool_text else "(empty)"} )

# ── 메인: 세션 1회 열고, exit 전까지 루프 ─────────────────────
async def chat_loop():
    print(f"[bridge] Ollama: {OLLAMA_HOST} / model: {MODEL}")
    print(f"[bridge] MCP server cmd: {MCP_SERVER_CMD}")
    if DEBUG:
        print("[bridge] DEBUG=1 모드로 상세 로그를 출력합니다.", flush=True)

    # UTF-8 환경변수 강제
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    params = StdioServerParameters(
        command=shlex.split(MCP_SERVER_CMD)[0],
        args=shlex.split(MCP_SERVER_CMD)[1:],
        env=env,
        cwd=str(HERE),
    )

    # MCP 서버/세션을 프로그램 생명주기 내내 유지
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            dlog("MCP session initialized")

            tools_resp = await session.list_tools()
            tools_schema = build_tools_schema(tools_resp.tools)

            # 대화 컨텍스트 유지
            messages: List[Dict[str, Any]] = [
                {"role": "system", "content": SYSTEM_PROMPT},
            ]

            print('대화를 시작합니다. "exit" 또는 "quit" 또는 "bye" 입력 시 종료됩니다.\n', flush=True)

            # 입력 루프
            while True:
                try:
                    user_text = input("> ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n[bridge] 종료합니다.")
                    break

                if not user_text:
                    continue
                if user_text.lower() in {"exit", "quit", "bye"}:
                    print("[bridge] 종료합니다.")
                    break

                # 사용자 발화 누적
                messages.append({"role": "user", "content": user_text})

                # 한 턴 처리(함수호출 루프 포함)
                await run_turn_async(messages, tools_schema, session)

                # 마지막 assistant의 자연어 답변 출력
                last = next((m for m in reversed(messages) if m["role"] == "assistant"), None)
                print(last["content"] if last else "")

async def main():
    try:
        await chat_loop()  # 사용자가 exit/quit/bye 입력해서 루프 종료
    finally:
        try:
            requests.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": MODEL,
                    "keep_alive": 0,     # ← 즉시 언로드
                    "messages": [{"role": "user", "content": "(cleanup)"}],
                    "stream": False,
                },
                timeout=10,
            )
        except Exception:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[bridge] 예외 발생: {e}", file=sys.stderr)
        raise
