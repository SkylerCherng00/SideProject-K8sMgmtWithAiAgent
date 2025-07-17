# 包成 Steamable Fast API (實務採用)
from typing import Dict
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI
import uvicorn, subprocess, yaml
import datetime
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config_mcpserver.yml"

class Settings(BaseModel):
    prometheus_url: str
    jump_server_host: str
    jump_server_ssh_arguments: str

def _load_settings(path: Path) -> Settings:
    """從指定的路徑載入 YAML 設定檔並驗證"""
    if not path.is_file():
        # 如果設定檔不存在，拋出一個明確的錯誤，並提示使用者如何建立
        raise FileNotFoundError(
            f"設定檔不存在於: {path}\n"
            f"請在專案根目錄建立一個 'config_server.yml' 檔案，並填入必要的設定。"
        )
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        return Settings(**config_data)
    except yaml.YAMLError as e:
        # 如果 YAML 格式錯誤，提供錯誤訊息
        raise ValueError(f"設定檔 '{path}' 格式錯誤: {e}")
    except Exception as e:
        # 捕捉其他可能的錯誤，例如 Pydantic 驗證失敗
        raise ValueError(f"載入設定檔 '{path}' 時發生錯誤: {e}")

# 在應用程式啟動時載入設定
settings = _load_settings(CONFIG_PATH)

mcp = FastMCP("mcp")

@mcp.tool(name="ssh_exec", description="execute command")
def remote_cmd(cmd: str) -> Dict:
    try:
        base_cmd = f"{settings.jump_server_ssh_arguments} {settings.jump_server_host} {cmd}"
        result = subprocess.run(base_cmd, shell=True, capture_output=True, text=True, timeout=3)
        rslt = {"return_state": "Error", "detail": result.stderr.replace(' ','')} if result.stderr else {"return_state": "OK", "detail": result.stdout.replace(' ','')}
        return rslt
    except Exception as e:
        return {"return_state": "Error", "detail": f"Command: {cmd}, Exception: {str(e)}"}

@mcp.tool(name="get_current_time", description="get current time in UTC+8")
def get_current_time() -> str:
    """取得當前時間，格式為 'YYYY-MM-DD HH:MM:SS'"""
    time = (datetime.datetime.now() + datetime.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
    return time

app = FastAPI(title="MCP API Gateway", lifespan=lambda app: mcp.session_manager.run())

app.mount("/run_cmd", mcp.streamable_http_app())
app.mount("/current_time", mcp.streamable_http_app())

@app.get("/")
def index():
    return {"message": "welcome, here is MCP Server!"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")