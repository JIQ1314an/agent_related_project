import subprocess
import tempfile
import os
import sys
import time
from typing import Dict, Any
from logger import logger
from config import settings


class CodeSandbox:
    """
    安全代码执行沙箱
    """

    def __init__(self, timeout: int = settings.SANDBOX_TIMEOUT_SECONDS):
        self.timeout = timeout

    def execute_test(self, code: str, test_code: str) -> Dict[str, Any]:
        full_script = f"{code}\n\n# --- AUTOMATED TESTS ---\n{test_code}"

        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = os.path.join(temp_dir, "test_runner.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(full_script)

            logger.info(f"[SANDBOX] 准备在沙箱中运行脚本: {script_path}")
            start_time = time.time()

            try:
                # 显式指定 utf-8 编码，防止 Windows 控制台编码错乱
                process = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    encoding="utf-8",
                    errors="replace",
                )
                execution_time = time.time() - start_time
                success = process.returncode == 0

                logger.info(
                    f"[SANDBOX EXECUTION COMPLETE] ExitCode={process.returncode} | "
                    f"Success={success} | Time={execution_time:.2f}s"
                )

                if not success:
                    logger.warning(f"[SANDBOX ERROR LOG]:\n{process.stderr.strip()}")

                return {
                    "success": success,
                    "exit_code": process.returncode,
                    "stdout": process.stdout,
                    "stderr": process.stderr,
                    "execution_time": execution_time,
                    "error_message": process.stderr if not success else "",
                }

            except subprocess.TimeoutExpired:
                execution_time = time.time() - start_time
                logger.error(f"[SANDBOX TIMEOUT] 执行超过设定的上限 {self.timeout}s")
                return {
                    "success": False,
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": f"Error: Code execution timed out after {self.timeout} seconds.",
                    "execution_time": execution_time,
                    "error_message": "Execution Timeout",
                }
            except Exception as e:
                execution_time = time.time() - start_time
                logger.critical(f"[SANDBOX SYSTEM ERROR] 未捕获异常: {str(e)}")
                return {
                    "success": False,
                    "exit_code": -2,
                    "stdout": "",
                    "stderr": str(e),
                    "execution_time": execution_time,
                    "error_message": str(e),
                }
