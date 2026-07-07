# 算法测试平台全面改进方案

日期: 2026-07-07
状态: 已批准
推进方式: 渐进式（Phase 1-4，每阶段独立上线）

## 背景

对现有平台进行安全加固、稳定性提升、代码结构重构和前端体验优化。

## Phase 1: 安全加固

### 1.1 命令注入修复

**文件**: `backend/services/simulator_service.py`, `backend/services/svn_service.py`

**现状**: 使用 `subprocess.run(cmd, shell=True, ...)`，`sim_cmd_template` 和 `script_path` 来自数据库，管理员可注入任意 shell 命令。

**方案**:
- 改为 `shell=False`，用 `shlex.split()` 拆分命令
- 添加输入校验函数 `validate_command_arg(s)`，只允许 `[a-zA-Z0-9/_.\-]`，拒绝 `| & ; $ \` ` 等 shell 元字符
- `simulator_service.py`: `shlex.split(core.sim_cmd_template.format(script=algorithm.script_path))`
- `svn_service.py`: `["svn", "info", repo_url, ...]` 列表形式传参

### 1.2 移除硬编码凭据

**文件**: `backend/config.py`, `backend/api/users.py`

- `config.py`: `SECRET_KEY` 无环境变量时 `raise RuntimeError("SECRET_KEY must be set")`
- `config.py`: `MYSQL_PASSWORD` 无环境变量时 `raise RuntimeError("MYSQL_PASSWORD must be set")`
- `config.py`: 默认管理员密码改为从 `ADMIN_PASSWORD` 环境变量读取，无默认值时报错
- `api/users.py:96`: 重置密码端点移除默认值 `'admin123'`，`new_password` 为必填字段

### 1.3 CSRF 防护

**依赖**: `flask-wtf`

前后端分离架构下，API 使用 session cookie 认证，需防护 CSRF。

**方案**:
- `app.py`: 初始化 `CSRFProtect(app)`
- 后端在登录成功后通过 `set_cookie` 写入 `csrf_token`（非 HttpOnly，前端可读）
- 前端 `api/index.js`: 请求拦截器从 cookie 读取 `csrf_token`，附加到 `X-CSRFToken` 请求头
- 所有 POST/PUT/DELETE 端点自动校验 header 中的 CSRF token

### 1.4 登录限流

**依赖**: `flask-limiter`

- 对 `/api/auth/login` 限流: 同一 IP 每分钟最多 5 次
- 超限返回 429 Too Many Requests
- 前端显示 "登录尝试过于频繁，请稍后再试"

## Phase 2: 后端稳定性

### 2.1 Celery 任务竞态锁

**文件**: `backend/tasks/celery_tasks.py`

**现状**: `_finalize_run` 检查 `completed >= total_tasks` 无锁，两个并发 worker 可能同时触发。

**方案**:
```python
def _finalize_run(run_id):
    with db.session.begin():
        run = db.session.query(TestRun).with_for_update().get(run_id)
        if run.status != 'running':
            return
        completed = TestResult.query.filter_by(
            test_run_id=run_id, status='completed'
        ).count()
        if completed >= run.total_tasks:
            run.status = 'completed'
            run.finished_at = datetime.utcnow()
    # 锁释放后再触发一致性报告
    _generate_consistency_report(run_id)
```

### 2.2 事务回滚

**全局修改**: 所有 `db.session.commit()` 包裹 try/except

```python
try:
    db.session.commit()
except Exception:
    db.session.rollback()
    raise
```

影响文件:
- `backend/app.py` (登录逻辑)
- `backend/api/tasks.py` (触发/重试)
- `backend/services/scheduler_service.py`
- `backend/tasks/celery_tasks.py`
- `backend/services/test_run_service.py` (Phase 3 新增)

### 2.3 N+1 查询修复

**dashboard trend** (`api/dashboard.py`):
```python
# Before: N 次 query per run
# After: 单条聚合
stats = dict(db.session.query(
    TestResult.test_run_id,
    func.count().filter(TestResult.status == 'passed')
).filter(TestResult.test_run_id.in_(run_ids))
 .group_by(TestResult.test_run_id).all())
```

**dashboard matrix** (`api/dashboard.py`):
- 使用 `joinedload(TestResult.algorithm)` 和 `joinedload(TestResult.core)`

**TestRun.to_dict()** (`models.py`):
- 查询时使用 `joinedload(TestRun.svn_revision)`

### 2.4 外键索引

**文件**: `backend/models.py`

为以下列添加 `index=True`:
- `TestResult.test_run_id`
- `TestResult.algorithm_id`
- `TestResult.core_id`
- `ConsistencyReport.test_run_id`
- `ConsistencyReport.algorithm_id`
- `TestRun.svn_revision_id`

新增迁移脚本 `backend/scripts/add_indexes.py`，对已有表执行 `CREATE INDEX IF NOT EXISTS`。

## Phase 3: 代码结构重构

### 3.1 抽取 TestRunService

**新文件**: `backend/services/test_run_service.py`

```python
class TestRunService:
    @staticmethod
    def create_run(triggered_by, svn_revision_id=None):
        """创建 TestRun + 所有 TestResult 记录"""
        algorithms = Algorithm.query.filter_by(is_active=True).all()
        cores = Core.query.filter_by(is_active=True).all()
        run = TestRun(
            triggered_by=triggered_by,
            svn_revision_id=svn_revision_id,
            total_tasks=len(algorithms) * len(cores),
            status=RunStatus.RUNNING
        )
        db.session.add(run)
        results = [
            TestResult(test_run_id=run.id, algorithm_id=a.id, core_id=c.id,
                       status=ResultStatus.PENDING)
            for a in algorithms for c in cores
        ]
        db.session.bulk_save_objects(results)
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return run
```

**重构**:
- `api/tasks.py`: `trigger_run` 调用 `TestRunService.create_run('manual')`
- `scheduler_service.py`: `check_svn_periodically` 调用 `TestRunService.create_run('auto', revision.id)`

### 3.2 Auth 路由迁移到 Blueprint

**新文件**: `backend/api/auth.py`

将 `app.py:35-93` 的 4 个路由迁移为 `auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')`:
- `POST /login`
- `POST /logout`
- `GET /me`
- `PUT /password`

`app.py` 改为 `app.register_blueprint(auth_bp)`，`create_app()` 只负责初始化。

### 3.3 统一错误处理

**文件**: `backend/app.py`

```python
@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(500)
def handle_error(e):
    code = e.code if hasattr(e, 'code') else 500
    return jsonify(error=str(e)), code
```

各端点 bare `except` 改为具体异常类型或交给全局处理器。

### 3.4 状态枚举规范化

**文件**: `backend/models.py`

```python
class RunStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'

class ResultStatus:
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    ERROR = 'error'
```

全局替换所有魔法字符串为枚举引用。

## Phase 4: 前端体验

### 4.1 ECharts 内存泄漏修复

**文件**: `frontend/src/views/Dashboard.vue`

```javascript
const chartInstance = ref(null)

onUnmounted(() => {
  if (chartInstance.value) {
    window.removeEventListener('resize', chartInstance.value.resize)
    chartInstance.value.dispose()
    chartInstance.value = null
  }
})
```

loadTrend 中 `chartInstance.value = echarts.init(...)` 并绑定 resize。

### 4.2 统一 Loading/空状态

**新文件**: `frontend/src/components/PageState.vue`

```vue
<template>
  <div v-if="loading" v-loading="true" style="min-height: 200px"></div>
  <el-empty v-else-if="empty" :description="description" />
  <slot v-else />
</template>
```

各页面统一使用，替换散落的 `v-loading` 和 `v-if` 判断。

### 4.3 通知系统

**后端**:
- 新模型 `Notification(id, user_id, type, message, is_read, created_at)`
- SSE 端点 `GET /api/notifications/stream`
- `_finalize_run` 中发送 "Run #X 完成" 通知写入数据库 + Redis pubsub

**前端**:
- `App.vue` 挂载时连接 SSE
- 侧边栏顶部添加通知铃铛 + badge 计数
- 新组件 `NotificationBell.vue`

### 4.4 审计日志

**后端**:
- 新模型 `AuditLog(id, user_id, action, target_type, target_id, detail, created_at)`
- 装饰器 `@audit_log(action, target_type)` 记录管理员操作
- 应用到: 用户管理 CRUD、配置管理 CRUD、手动触发测试

**前端**:
- 管理员页面新增 "审计日志" tab 或独立页面

## 依赖变更

**新增 Python 依赖** (`backend/requirements.txt`):
- `flask-wtf` (CSRF)
- `flask-limiter` (登录限流)

**无前端依赖变更** (SSE 使用原生 `EventSource`)

## 实施顺序

1. Phase 1 安全加固 — 最高优先级，独立可上线
2. Phase 2 后端稳定性 — 依赖 Phase 1 的事务回滚模式
3. Phase 3 代码结构 — 依赖 Phase 2 的稳定基础
4. Phase 4 前端体验 — 可与 Phase 3 并行
