# 請先安裝 python-multipart，否則 FastAPI 的表單上傳功能會失效
# 安裝指令：pip install python-multipart

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import tempfile
import subprocess
import time
import os
import psutil
import uuid

app = FastAPI()

LANG_CONFIG = {
    "c":    {"compile": ["gcc", "{src}", "-o", "{exe}"], "run": ["{exe}"]},
    "cpp":  {"compile": ["g++", "{src}", "-o", "{exe}"], "run": ["{exe}"]},
    "java": {"compile": ["javac", "{src}"], "run": ["java", "{main_class}"]},
    "python": {"compile": None, "run": ["python", "{src}"]},
}

def run_with_limits(cmd, input_data, timeout=2, lang="python", src_path=None, exe_path=None):
    # 使用 Docker 執行程式並限制資源
    container_name = f"judge_{uuid.uuid4().hex[:8]}"
    # 建立對應語言的 docker image 與執行指令
    image_map = {
        "c":      ("gcc:latest", f"/tmp/prog"),
        "cpp":    ("gcc:latest", f"/tmp/prog"),
        "java":   ("openjdk:latest", f"java {os.path.splitext(os.path.basename(src_path))[0]}"),
        "python": ("python:3.10-slim", f"python /tmp/{os.path.basename(src_path)}"),
    }
    image, run_cmd = image_map[lang]
    # 將程式碼與執行檔複製到 /tmp
    with tempfile.TemporaryDirectory() as tmpdir:
        if src_path:
            src_dst = os.path.join(tmpdir, os.path.basename(src_path))
            with open(src_dst, "wb") as f:
                with open(src_path, "rb") as srcf:
                    f.write(srcf.read())
        if exe_path and os.path.exists(exe_path):
            exe_dst = os.path.join(tmpdir, "prog")
            with open(exe_dst, "wb") as f:
                with open(exe_path, "rb") as exef:
                    f.write(exef.read())
        # 建立 docker 指令
        docker_cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--cpus=1", "--memory=128m", "--network=none",
            "-v", f"{tmpdir}:/tmp",
            image,
            "timeout", str(timeout), "sh", "-c", run_cmd
        ]
        try:
            start_time = time.time()
            proc = subprocess.Popen(
                docker_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            outs, errs = proc.communicate(input=input_data.encode(), timeout=timeout+1)
            elapsed = time.time() - start_time
            # 記憶體用量可用 docker stats 或略過
            mem = 0
            output = outs.decode()
            return output, mem, elapsed, proc.returncode, errs.decode()
        except subprocess.TimeoutExpired:
            proc.kill()
            return "", 0, timeout, -1, "Time Limit Exceeded"
        except Exception as e:
            proc.kill()
            return "", 0, 0, -1, str(e)

@app.post("/judge")
async def judge(
    code: UploadFile = File(...),
    language: str = Form(...),
    testcases: UploadFile = File(...)
):
    if language not in LANG_CONFIG:
        return JSONResponse({"error": "Unsupported language"}, status_code=400)
    with tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, code.filename)
        with open(src_path, "wb") as f:
            f.write(await code.read())
        exe_path = os.path.join(tmpdir, "prog")
        # 編譯
        if LANG_CONFIG[language]["compile"]:
            compile_cmd = [x.format(src=src_path, exe=exe_path) for x in LANG_CONFIG[language]["compile"]]
            res = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode != 0:
                return JSONResponse({"error": "Compile Error", "message": res.stderr.decode()}, status_code=200)
        # 讀取測資
        testcases_data = (await testcases.read()).decode().split("\n====\n")
        results = []
        for idx, testcase in enumerate(testcases_data):
            # 執行（改用 docker）
            if language == "java":
                run_cmd = None  # 由 run_with_limits 處理
            else:
                run_cmd = None
            output, mem, elapsed, ret, err = run_with_limits(
                cmd=None, input_data=testcase, timeout=2,
                lang=language, src_path=src_path, exe_path=exe_path
            )
            if ret != 0:
                return JSONResponse({"error": "Runtime Error", "testcase": idx+1, "message": err}, status_code=200)
            results.append({"memory": mem, "time": elapsed, "output": output})
        return {"status": "Accepted", "results": results}
