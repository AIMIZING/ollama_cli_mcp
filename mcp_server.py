# mcp_server.py
import os, sys
from datetime import datetime
from pathlib import Path
from fastmcp import FastMCP
import PyPDF2
from duckduckgo_search import DDGS

DEBUG = os.environ.get("DEBUG", "0") == "1"
HERE = Path(__file__).resolve().parent

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
def list_files_in_folder(folder_path: str) -> list[str]:
    """폴더 경로를 입력받아 해당 폴더의 파일명 목록을 반환합니다. 상대 경로도 지원합니다."""
    dlog(f"tool=list_files_in_folder called args={{'folder_path': '{folder_path}'}}")
    if not os.path.isabs(folder_path):
        folder_path = str(HERE / folder_path)
    if not os.path.exists(folder_path):
        msg = f"폴더가 존재하지 않습니다: {folder_path}"
        dlog(f"tool=list_files_in_folder error: {msg}")
        raise FileNotFoundError(msg)
    if not os.path.isdir(folder_path):
        msg = f"지정된 경로는 폴더가 아닙니다: {folder_path}"
        dlog(f"tool=list_files_in_folder error: {msg}")
        raise NotADirectoryError(msg)
    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
    dlog(f"tool=list_files_in_folder ok, files={files}")
    return files

@mcp.tool
def read_file(path: str) -> str:
    """파일 경로를 입력받아 텍스트 내용을 반환합니다. PDF 파일의 경우 텍스트를 추출합니다. 상대 경로도 지원합니다."""
    dlog(f"tool=read_file called args={{'path': '{path}'}}")
    if not os.path.isabs(path):
        path = str(HERE / path)
    if not os.path.exists(path):
        msg = f"파일이 존재하지 않습니다: {path}"
        dlog(f"tool=read_file error: {msg}")
        raise FileNotFoundError(msg)
    ext = os.path.splitext(path)[1].lower()
    if ext == '.pdf':
        with open(path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text = ''
            for page in pdf_reader.pages:
                text += page.extract_text()
        dlog(f"tool=read_file ok, bytes={len(text.encode('utf-8'))}")
        return text
    else:
        with open(path, "r", encoding="utf-8") as f:
            data = f.read()
        dlog(f"tool=read_file ok, bytes={len(data.encode('utf-8'))}")
        return data

@mcp.tool
def web_search(query: str) -> str:
    """웹에서 쿼리를 검색하여 결과를 반환합니다."""
    dlog(f"tool=web_search called args={{'query': '{query}'}}")
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        text = ""
        for result in results:
            text += f"Title: {result['title']}\nURL: {result['href']}\nSnippet: {result['body']}\n\n"
        dlog(f"tool=web_search ok, results={len(results)}")
        return text
    except Exception as e:
        msg = f"웹 검색 실패: {str(e)}"
        dlog(f"tool=web_search error: {msg}")
        raise RuntimeError(msg)

if __name__ == "__main__":
    dlog("MCP server starting (stdio)…")
    mcp.run()
