import math
from models import ConsistencyReport, Core, ResultStatus, TestResult, db
from services.db_session import safe_commit


class ConsistencyService:
    def __init__(self, threshold=None):
        from flask import current_app
        self.threshold = threshold or current_app.config.get('CONSISTENCY_THRESHOLD', 1e-6)

    def compare_across_cores(self, test_run_id, algorithm_id):
        """
        对比同一算法在不同核上的结果一致性。
        以 x86 核为参考基准（如果存在），否则取第一个核。
        """
        results = TestResult.query.filter_by(
            test_run_id=test_run_id,
            algorithm_id=algorithm_id,
        ).filter(TestResult.status.in_([ResultStatus.PASSED, ResultStatus.FAILED])).all()

        if len(results) < 2:
            # 不足两个核的结果，无法比较
            report = ConsistencyReport(
                test_run_id=test_run_id,
                algorithm_id=algorithm_id,
                is_consistent=None,
                details={'error': '不足两个核的结果，无法比较'},
                max_diff=None,
            )
            db.session.add(report)
            safe_commit()
            return report

        # 选择参考核：优先 x86
        ref_result = None
        for r in results:
            if r.core and r.core.name.lower() in ('x86', 'x86_64', 'x64'):
                ref_result = r
                break
        if ref_result is None:
            ref_result = results[0]

        # 逐项比较
        details = {
            'reference_core': ref_result.core.display_name or ref_result.core.name,
            'comparisons': [],
        }

        max_diff = 0.0
        all_consistent = True

        for r in results:
            if r.id == ref_result.id:
                continue

            diff = self._compute_diff(ref_result.result_data, r.result_data)
            core_name = r.core.display_name or r.core.name

            is_consistent = diff['max_abs_diff'] < self.threshold
            if not is_consistent:
                all_consistent = False
            max_diff = max(max_diff, diff['max_abs_diff'])

            details['comparisons'].append({
                'core': core_name,
                'max_abs_diff': diff['max_abs_diff'],
                'mean_abs_diff': diff['mean_abs_diff'],
                'is_consistent': is_consistent,
                'ref_pass_count': ref_result.pass_count,
                'ref_fail_count': ref_result.fail_count,
                'cur_pass_count': r.pass_count,
                'cur_fail_count': r.fail_count,
            })

        report = ConsistencyReport(
            test_run_id=test_run_id,
            algorithm_id=algorithm_id,
            is_consistent=all_consistent,
            reference_core_id=ref_result.core_id,
            details=details,
            max_diff=max_diff,
        )
        db.session.add(report)
        safe_commit()
        return report

    def _compute_diff(self, ref_data, cur_data):
        """
        计算两个结果数据之间的差异。
        支持多种数据格式：
        - dict of numeric values
        - list of numeric values
        - scalar numbers
        """
        if ref_data is None or cur_data is None:
            return {'max_abs_diff': float('inf'), 'mean_abs_diff': float('inf')}

        diffs = []

        try:
            if isinstance(ref_data, dict) and isinstance(cur_data, dict):
                # 字典：按 key 比较
                for key in ref_data:
                    if key in cur_data:
                        d = self._abs_diff(ref_data[key], cur_data[key])
                        if d is not None:
                            diffs.append(d)
            elif isinstance(ref_data, list) and isinstance(cur_data, list):
                # 列表：按索引比较
                for i in range(min(len(ref_data), len(cur_data))):
                    d = self._abs_diff(ref_data[i], cur_data[i])
                    if d is not None:
                        diffs.append(d)
            else:
                # 标量
                d = self._abs_diff(ref_data, cur_data)
                if d is not None:
                    diffs.append(d)
        except Exception:
            return {'max_abs_diff': float('inf'), 'mean_abs_diff': float('inf')}

        if not diffs:
            return {'max_abs_diff': 0.0, 'mean_abs_diff': 0.0}

        return {
            'max_abs_diff': max(diffs),
            'mean_abs_diff': sum(diffs) / len(diffs),
        }

    def _abs_diff(self, a, b):
        """计算两个值的绝对差，非数值返回 None"""
        try:
            return abs(float(a) - float(b))
        except (TypeError, ValueError):
            return None
