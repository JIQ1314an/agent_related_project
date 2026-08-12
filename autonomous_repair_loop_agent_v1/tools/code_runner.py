import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float


class PythonSandbox:
    @staticmethod
    def run_code(code_content: str, timeout: int = 10) -> ExecutionResult:
        start_time = time.time()
        temp_file_path = None

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(
                suffix=".py", mode="w", delete=False, encoding="utf-8"
            ) as temp_file:
                temp_file.write(code_content)
                temp_file_path = temp_file.name

            # 执行子进程
            process = subprocess.run(
                [sys.executable, temp_file_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=(process.returncode == 0),
                stdout=process.stdout,
                stderr=process.stderr,
                exit_code=process.returncode,
                duration_ms=round(duration, 2),
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start_time) * 1000
            return ExecutionResult(
                success=False,
                stdout="",
                stderr=f"Execution timed out after {timeout} seconds.",
                exit_code=-1,
                duration_ms=round(duration, 2),
            )
        finally:
            # 安全清理磁盘临时文件
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
