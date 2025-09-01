# ollama_cli_mcp
A lightweight Python bridge that connects Ollama CLI-based local LLMs with a simple MCP (Model Context Protocol) server. Supports real-time tool invocation, interactive conversations until user exit, and automatic VRAM cleanup on shutdown.

This project is intended to be used with a local LLM model running via Ollama CLI in combination with an MCP (Model Context Protocol) server.  
It is an experimental project designed to verify whether an AI model running on Ollama can communicate effectively with an MCP server.

<br>

## Features
- Enables MCP to run any local model installed via Ollama CLI
- Sends MCP client requests to the local Ollama HTTP API
- Supports interactive chat until manually stopped
- Includes optional `keep_alive=0` request to unload the model and free GPU VRAM when the bridge stops
- Fully local — no internet connection required after model download
- Minimal setup with Python and Ollama
- Integrated MCP tools: Get current time, list files in a folder, read files (including PDFs), and perform web searches

<br>

## Requirements

- Windows 11 / macOS / Linux (tested on Windows 11)
- Python 3.10+
- Ollama CLI installed
- MCP-compatible client

<br>

## How to Use

### 1. Install Ollama & Download Model
- Install [Ollama](https://ollama.com/download) for your OS
- Download the desired model (example: `gpt-oss:20b`):
```sh
ollama pull gpt-oss:20b
```

<br>

### 2. Clone `ollama_cli_mcp`

**Option 1: Download as ZIP**
- Click **"Code"** → **"Download ZIP"**
- Extract the downloaded ZIP

<br>

**Option 2: Clone with Git**
```sh
git clone https://github.com/AIMIZING/ollama_cli_mcp.git
cd ollama_cli_mcp
```

<br>

### 3. Set Up Python Environment

**Create and activate a virtual environment:**

```sh
python -m venv .venv
# Windows (PowerShell)
.venv\Scripts\activate.ps1
# Windows (Command Prompt)
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

<br>

**Install the necessary Python packages for MCP support:**  

Use the provided `requirements.txt` file for all dependencies:
```sh
pip install -r requirements.txt
```

If you prefer manual installation:
```sh
pip install mcp fastmcp requests pypdf2 duckduckgo-search
```

<br>

### 4. Configure Environment Variables (Optional)
Set the following environment variables to customize behavior:
- `OLLAMA_HOST`: Ollama server URL (default: `http://127.0.0.1:11434`)
- `OLLAMA_MODEL`: Model name (default: `gpt-oss:20b`)
- `DEBUG`: Enable debug logging (set to `1` for verbose output, default: `0`)

Example (Windows PowerShell):
```sh
$env:OLLAMA_HOST="http://127.0.0.1:11434"
$env:OLLAMA_MODEL="gpt-oss:20b"
$env:DEBUG="1"
```

<br>

### 5. Run Bridge (MCP + Ollama HTTP API)
`bridge_http.py` will start the MCP server and connect it to the local Ollama HTTP API.
Run it directly:
```sh
python bridge_http.py
```

When you close the bridge, it will send a `keep_alive=0` request to Ollama to unload the model and free VRAM.

<br>

## Example Interaction
Once running, you can ask questions that leverage MCP tools:
> "What is the current time?"

The request will be sent to the MCP server, which communicates with the Ollama-powered local AI model.  
The model will process the request and respond with the current time.

Other examples:
- "List files in the 'asset' folder."
- "Read the content of 'asset/apple_research.pdf'."
- "Search the web for 'Python tutorials'."

---

## Notes
- Ensure Ollama is running before starting the bridge (`ollama serve`).
- Models must be pulled via `ollama pull <model_name>` before use.
- VRAM is automatically freed on exit, but you can also run `ollama stop <model_name>` to manually unload.
- If you encounter module errors (e.g., `ModuleNotFoundError`), ensure all packages from `requirements.txt` are installed in the virtual environment.
- For troubleshooting, enable `DEBUG=1` to see detailed logs.
- If you want the model to respond in English, modify the SYSTEM_PROMPT in `bridge_http.py` to request English responses.
