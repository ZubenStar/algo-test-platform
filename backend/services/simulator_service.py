import subprocess
import os
import re
import json
import shlex
from datetime import datetime
from models import Algorithm, Core, ResultStatus, TestResult, db
from services.db_session import safe_commit


COMMAND_ARG_PATTERN = re.compile(r'^[a-zA-Z0-9/_.\-]+$')


def validate_command_arg(value):
    if not value or not COMMAND_ARG_PATTERN.fullmatch(value):
        raise ValueError(f'非法命令参数: {value}')
    return value


class SimulatorService:
    def __init__(self):
        from flask import current_app
        self.output_dir = current_app.config.get('SIM_OUTPUT_DIR', '/tmp/sim_output')
        self.timeout = current_app.config.get('SIM_TIMEOUT_SECONDS', 600)
        os.makedirs(self.output_dir, exist_ok=True)

    def run_algorithm_on_core(self, test_run_id, algorithm_id, core_id):
        """
        执行单个算法在单个核上的仿真。
        更新 test_results 表中的对应记录。
        """
        result = TestResult.query.filter_by(
            test_run_id=test_run_id,
            algorithm_id=algorithm_id,
            core_id=core_id,
        ).first()

        if not result:
            return None

        algorithm = Algorithm.query.get(algorithm_id)
        core = Core.query.get(core_id)

        if not algorithm or not core:
            result.status = ResultStatus.ERROR
            result.error_message = '算法或核配置不存在'
            safe_commit()
            return result

        # 更新状态为 running
        result.status = ResultStatus.RUNNING
        result.started_at = datetime.utcnow()
        safe_commit()

        try:
            # 构建仿真命令
            cmd = self._build_command(algorithm, core)

            # 设置日志文件
            log_file = os.path.join(
                self.output_dir,
                f'run{test_run_id}_algo{algorithm_id}_core{core_id}.log'
            )
            result.log_file = log_file

            # 执行仿真
            proc = subprocess.run(
                cmd, shell=False, capture_output=True, text=True,
                timeout=self.timeout
            )

            # 保存日志
            with open(log_file, 'w') as f:
                f.write(f"=== STDOUT ===\n{proc.stdout}\n")
                f.write(f"=== STDERR ===\n{proc.stderr}\n")
                f.write(f"=== Return Code: {proc.returncode} ===\n")

            # 解析输出
            if proc.returncode == 0:
                parsed = self.parse_output(proc.stdout)
                result.status = ResultStatus.PASSED if parsed['fail_count'] == 0 else ResultStatus.FAILED
                result.result_data = parsed.get('data')
                result.pass_count = parsed['pass_count']
                result.fail_count = parsed['fail_count']
                result.total_count = parsed['total_count']
            else:
                result.status = ResultStatus.FAILED
                result.error_message = proc.stderr[-2000:] if proc.stderr else f'Exit code: {proc.returncode}'

        except subprocess.TimeoutExpired:
            result.status = ResultStatus.ERROR
            result.error_message = f'仿真超时（{self.timeout}秒）'
        except Exception as e:
            result.status = ResultStatus.ERROR
            result.error_message = str(e)[:2000]

        result.finished_at = datetime.utcnow()
        if result.started_at:
            result.execution_time = (result.finished_at - result.started_at).total_seconds()

        safe_commit()
        return result

    def _build_command(self, algorithm, core):
        """根据算法脚本路径和核的命令模板构建仿真命令"""
        if core.sim_cmd_template:
            cmd = shlex.split(core.sim_cmd_template.format(script=algorithm.script_path))
        else:
            # 默认直接执行脚本
            cmd = ['python', algorithm.script_path]
        return [validate_command_arg(arg) for arg in cmd]

    def parse_output(self, output):
        """
        解析仿真脚本的标准输出。

        默认解析格式（可在实际使用中定制）：
        - 期望输出包含类似 "PASS: test_name" 和 "FAIL: test_name" 的行
        - 数值结果用 JSON 格式输出，以 "RESULT_JSON:" 开头

        返回 dict:
        {
            'pass_count': int,
            'fail_count': int,
            'total_count': int,
            'data': dict or None
        }
        """
        pass_count = 0
        fail_count = 0
        data = None

        for line in output.split('\n'):
            line = line.strip()

            # 匹配 PASS/FAIL 行
            if line.startswith('PASS:') or line.startswith('[PASS]'):
                pass_count += 1
            elif line.startswith('FAIL:') or line.startswith('[FAIL]'):
                fail_count += 1

            # 匹配 JSON 结果数据
            if line.startswith('RESULT_JSON:'):
                try:
                    json_str = line[len('RESULT_JSON:'):].strip()
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    pass

            # 也支持 summary 格式: "Tests: X passed, Y failed, Z total"
            match = re.search(r'Tests?:\s*(\d+)\s*passed,\s*(\d+)\s*failed', line)
            if match:
                pass_count = int(match.group(1))
                fail_count = int(match.group(2))

        total_count = pass_count + fail_count
        if total_count == 0:
            # 如果没解析到任何结果，把整个输出当作一条结果
            total_count = 1
            if 'ERROR' in output or 'FAIL' in output:
                fail_count = 1
            else:
                pass_count = 1

        return {
            'pass_count': pass_count,
            'fail_count': fail_count,
            'total_count': total_count,
            'data': data,
        }
