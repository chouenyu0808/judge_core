# Judge Core / 核心評測

This service exposes a FastAPI endpoint for running code against test cases.
這個服務提供一個 FastAPI 端點，用於執行程式碼並比對測資。

## Requirements / 前置需求

- Python 3.10+
- Install dependencies / 安裝相依套件:
  ```bash
  pip install -r requirements.txt
  ```

## Running the Server / 啟動伺服器

Start the FastAPI server with `uvicorn`:
使用 `uvicorn` 啟動伺服器：

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.
API 將於 `http://localhost:8000` 提供服務。

## `/judge` Endpoint / `/judge` 端點

Send a `POST` request with `multipart/form-data` containing:
以 `multipart/form-data` 形式發送 `POST` 請求，內容包含：

- `code`: the source file to compile/run
  `code`: 要編譯或執行的程式檔案
- `language`: one of `c`, `cpp`, `java`, or `python`
  `language`: 可選 `c`、`cpp`、`java` 或 `python`
- `testcases`: text file with test inputs separated by `====`
  `testcases`: 測資檔案，以 `====` 分隔各筆輸入

Example using `curl`:
使用 `curl` 的範例：

```bash
curl -X POST \
  -F "code=@solution.py" \
  -F "language=python" \
  -F "testcases=@tests.txt" \
  http://localhost:8000/judge
```
