# pyenv
- Manage Python versions
- ref:
  - https://github.com/pyenv/pyenv
  - https://www.maxlist.xyz/2022/05/06/python-pyenv/
  - https://blog.kyomind.tw/ubuntu-pyenv/
- pyenv + poetry
  - https://blog.kyomind.tw/poetry-pyenv-practical-tips/
- 用 poetry 的前提下，不要再加上 pyenv 的 virtualenv
- Cheet sheet
```script
# 查看 pyenv 可安裝 Python 版本
pyenv install -l

# 安裝想選擇的 python 版本
pyenv install -v 3.7.7

# 查看已經安裝過的 pyenv python 版本
pyenv versions

# 切換 Python 版本，可以選擇用 global、local 或 shell 來執行：
## global & local & shell 三者使用方法差異在於：
### global 對應於全局
### local 對應於當前資料夾
### shell 對應於當前 shell
### 優先順序是 shell > local > global
pyenv global 3.7.7
pyenv local 3.7.7
pyenv shell 3.7.7

# Pyenv 切換 python 版本成功後，如何查看？
python3 --version

# Pyenv 如何切換成原始系統的版本
pyenv global system
```

# poetry
- Manage python packages' dependency
- Installation
  - ref: https://python-poetry.org/docs/#installing-with-the-official-installer
  - Linux: `curl -sSL https://install.python-poetry.org | POETRY_VERSION=1.6.1 python3 -`
- Poetry in docker: https://blog.kyomind.tw/poetry-multi-stage-build/
- Cheet Sheet
```script
# 檢查是否安裝成功
poetry --version

# 使用下面這段指令來看 Poetry 中的設定
poetry config --list

# 設定虛擬環境在專案中
poetry config virtualenvs.in-project true

# 用 Poetry 來建一個新專案
poetry new myprj
cd myprj

# 確認 pyenv 的 python 版本與位置
pyenv version
which <python_version_eg. python3.12>

# pyproject.toml 虛擬環境設定檔
## 修改 pyproject.toml 並安裝 Python 3.12 版的虛擬環境
poetry env use <python_version_or_path eg. python3.12>
poetry env remove --all

## 如果不需要轉換 python 路徑，直接透過以下指令產生 venv
poetry install

# 安裝套件
## 觀察 pyproject. Toml 的變化
poetry add pendulum
poetry remove pendulum

# Read requirements.txt and add them into poetry environment
cat requirements.txt | xargs poetry add

# 啟動 Poetry 建立的虛擬環境
poetry shell

# 離開虛擬環境
exit

# export requirement.txt
poetry export -f requirements.txt --output requirements.txt --without-hashes

```