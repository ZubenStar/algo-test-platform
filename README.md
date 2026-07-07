# 算法单元测试一致性平台

多核多算法的单元测试自动化管理平台。支持 SVN 更新检测、自动触发仿真、跨核一致性对比。

## 功能特性

- **仪表盘**: 算法×核心矩阵热力图、通过率趋势图
- **测试结果**: 按轮次查看详细测试结果，支持筛选
- **一致性报告**: 跨核结果一致性对比，差异详情展示
- **SVN 监控**: 自动检测 SVN 更新，触发仿真任务
- **任务管理**: 手动触发测试、查看进度、重试失败任务
- **用户管理**: 管理员/普通用户两级权限，前端用户管理
- **配置管理**: 算法和核心的增删改查

## 技术栈

| 层 | 技术 |
|---|------|
| 后端 | Python Flask + Celery + APScheduler |
| 前端 | Vue3 + Element Plus + ECharts |
| 数据库 | MySQL 8 |
| 任务队列 | Celery + Redis |
| 认证 | Flask-Login (Session) |

## 环境要求

| 依赖 | 最低版本 | 说明 |
|------|----------|------|
| Docker | 20.10+ | 用于运行 MySQL 和 Redis 容器 |
| Docker Compose | v2+ | 已内置于 Docker Desktop |
| Python | 3.10+ | 后端运行环境 |
| Node.js | 18+ | 前端构建环境 |
| libxml2-dev / libxslt-dev | - | lxml 编译依赖（见下方说明） |

### 系统依赖安装

lxml 需要 C 库编译支持，在部署后端前安装：

```bash
# Ubuntu / Debian
sudo apt install -y python3-venv libxml2-dev libxslt-dev

# CentOS / RHEL
sudo yum install -y python3-devel libxml2-devel libxslt-devel
```

> **WSL2 用户**：需先安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)，并在 Settings > Resources > WSL Integration 中启用当前发行版的集成。

## 快速开始

### 1. 启动基础设施

```bash
docker compose up -d
```

启动 Redis (端口 6379) 和 MySQL (端口 3306)。等待 MySQL 就绪：

```bash
# 验证 MySQL 可用
docker exec algo-test-mysql mysqladmin ping -h 127.0.0.1 -u root -proot123

# 验证 Redis 可用
docker exec algo-test-redis redis-cli ping
```

### 2. 后端设置

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 初始化数据库（创建表 + 默认管理员 + 示例数据）
python scripts/init_db.py
```

### 3. 启动后端

```bash
# 终端1: 启动 Celery Worker
celery -A tasks.celery_app worker --loglevel=info

# 终端2: 启动 Flask
python app.py
```

### 4. 前端设置

```bash
cd frontend

npm install
npm run dev
```

前端默认运行在 `http://localhost:3000`，API 请求代理到 `http://localhost:5000`。

### 5. 登录

- 默认管理员: `admin` / `admin123`
- 首次登录需修改密码

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FLASK_ENV` | development | 运行环境 |
| `MYSQL_HOST` | 127.0.0.1 | MySQL 地址 |
| `MYSQL_PORT` | 3306 | MySQL 端口 |
| `MYSQL_USER` | root | MySQL 用户 |
| `MYSQL_PASSWORD` | root123 | MySQL 密码 |
| `MYSQL_DB` | algo_test | 数据库名 |
| `REDIS_URL` | redis://127.0.0.1:6379/0 | Redis 地址 |
| `SVN_REPO_URL` | - | SVN 仓库地址 |
| `SVN_CHECK_INTERVAL` | 30 | SVN 检查间隔(分钟) |
| `SIM_SCRIPTS_DIR` | - | 仿真脚本目录 |
| `SIM_OUTPUT_DIR` | /tmp/sim_output | 仿真输出目录 |
| `SIM_TIMEOUT` | 600 | 仿真超时(秒) |
| `CONSISTENCY_THRESHOLD` | 1e-6 | 一致性阈值 |

## 仿真脚本规范

仿真脚本需要输出特定格式的结果，平台会自动解析：

```
# 方式1: 逐条结果
PASS: test_case_1
PASS: test_case_2
FAIL: test_case_3

# 方式2: 汇总格式
Tests: 10 passed, 1 failed, 11 total

# 方式3: JSON 结果数据（用于一致性对比）
RESULT_JSON: {"snr": 25.3, "thd": 0.001, "output_level": -3.2}
```

## 生产部署

### 后端

```bash
export FLASK_ENV=production
export SECRET_KEY=your-very-secret-key        # 必须修改
export MYSQL_PASSWORD=strong-password          # 必须修改
export MYSQL_HOST=your-mysql-host
export REDIS_URL=redis://your-redis-host:6379/0
```

### 前端构建

```bash
cd frontend
npm run build
# 输出到 frontend/dist/，可配置 nginx 代理或由 Flask 托管静态文件
```

### 停止服务

```bash
docker compose down          # 停止并删除容器
docker compose down -v       # 同时删除数据卷（会清除数据库数据）
```

## 常见问题

### MySQL 容器启动失败：`unknown variable 'default-authentication-plugin'`

MySQL 8.4 已移除 `--default-authentication-plugin` 参数。确保 `docker-compose.yml` 中的 command 不包含该选项：

```yaml
command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci
```

如已使用旧配置启动过，需清除数据卷后重建：

```bash
docker compose down -v
docker compose up -d
```

### Python venv 创建失败：`ensurepip is not available`

Debian/Ubuntu 系统需要安装 `python3-venv` 包：

```bash
sudo apt install -y python3-venv
```

### lxml 编译失败：`Please make sure the libxml2 and libxslt development packages are installed`

```bash
sudo apt install -y libxml2-dev libxslt-dev   # Ubuntu / Debian
sudo yum install -y libxml2-devel libxslt-devel  # CentOS / RHEL
```

### `docker-compose` 命令未找到

本项目使用 Docker Compose v2，命令为 `docker compose`（无连字符）。如需兼容旧版：

```bash
# 安装 docker-compose-plugin（Linux）
sudo apt install docker-compose-plugin

# 或使用 pip 安装旧版
pip install docker-compose
```

## 项目结构

```
algo-test-platform/
├── backend/
│   ├── app.py              # Flask 入口
│   ├── config.py           # 配置
│   ├── models.py           # 数据模型
│   ├── decorators.py       # 权限装饰器
│   ├── services/           # 业务服务
│   ├── api/                # REST API
│   ├── tasks/              # Celery 任务
│   └── scripts/            # 工具脚本
├── frontend/
│   └── src/
│       ├── views/          # 页面组件
│       ├── components/     # 公共组件
│       ├── stores/         # Pinia 状态
│       ├── api/            # API 封装
│       └── router/         # 路由配置
├── docker-compose.yml
└── README.md
```
