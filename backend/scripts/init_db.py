#!/usr/bin/env python3
"""初始化数据库：创建表 + 插入默认管理员 + 示例数据"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, User, Algorithm, Core


def init_database():
    app = create_app()

    with app.app_context():
        # 创建所有表
        db.create_all()
        print("[OK] 数据库表已创建")

        # 创建默认管理员
        admin = User.query.filter_by(username=app.config['DEFAULT_ADMIN_USERNAME']).first()
        if not admin:
            admin = User(
                username=app.config['DEFAULT_ADMIN_USERNAME'],
                role='admin',
                force_change_password=True,
            )
            admin.set_password(app.config['DEFAULT_ADMIN_PASSWORD'])
            db.session.add(admin)
            db.session.commit()
            print(f"[OK] 默认管理员已创建: {admin.username} / {app.config['DEFAULT_ADMIN_PASSWORD']}")
            print("     首次登录后请修改密码！")
        else:
            print(f"[OK] 管理员已存在: {admin.username}")

        # 插入示例数据（如果需要）
        if Algorithm.query.count() == 0:
            sample_algos = [
                Algorithm(name='Algorithm_A', display_name='算法A - 降噪',
                         script_path='/path/to/algo_a_sim.py', description='降噪算法仿真'),
                Algorithm(name='Algorithm_B', display_name='算法B - 回声消除',
                         script_path='/path/to/algo_b_sim.py', description='回声消除算法仿真'),
                Algorithm(name='Algorithm_C', display_name='算法C - 波束成形',
                         script_path='/path/to/algo_c_sim.py', description='波束成形算法仿真'),
            ]
            db.session.add_all(sample_algos)
            print(f"[OK] 已插入 {len(sample_algos)} 个示例算法")

        if Core.query.count() == 0:
            sample_cores = [
                Core(name='ARM_M55', display_name='ARM Cortex-M55', arch='arm',
                     sim_cmd_template='python {script} --core m55'),
                Core(name='HiFi1S', display_name='Cadence HiFi1S', arch='xtensa',
                     sim_cmd_template='python {script} --core hifi1s'),
                Core(name='HiFi4', display_name='Cadence HiFi4', arch='xtensa',
                     sim_cmd_template='python {script} --core hifi4'),
                Core(name='x86', display_name='x86 (参考基准)', arch='x86',
                     sim_cmd_template='python {script} --core x86'),
            ]
            db.session.add_all(sample_cores)
            print(f"[OK] 已插入 {len(sample_cores)} 个示例核")

        db.session.commit()
        print("\n[OK] 数据库初始化完成！")


if __name__ == '__main__':
    init_database()
