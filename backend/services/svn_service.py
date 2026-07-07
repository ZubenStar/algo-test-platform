import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from models import db, SvnRevision


class SvnService:
    def __init__(self, repo_url=None):
        from flask import current_app
        self.repo_url = repo_url or current_app.config.get('SVN_REPO_URL', '')

    def check_update(self):
        """
        检查 SVN 是否有新提交。
        返回 (has_update, SvnRevision object or None)
        """
        try:
            cmd = f'svn info --xml {self.repo_url}'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                print(f"SVN info failed: {result.stderr}")
                return False, None

            root = ET.fromstring(result.stdout)
            entry = root.find('.//entry')
            revision = entry.get('revision')
            author = entry.find('.//commit/author').text
            message = entry.find('.//commit/date').text
            date_str = entry.find('.//commit/date').text

            commit_time = None
            if date_str:
                try:
                    commit_time = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                except Exception:
                    pass

            # 获取提交消息
            msg_elem = entry.find('.//commit')
            log_msg = ''
            # svn info 不一定有 message，用 svn log 获取
            log_result = subprocess.run(
                f'svn log -r {revision} --xml {self.repo_url}',
                shell=True, capture_output=True, text=True, timeout=30
            )
            if log_result.returncode == 0:
                log_root = ET.fromstring(log_result.stdout)
                msg_elem = log_root.find('.//msg')
                if msg_elem is not None and msg_elem.text:
                    log_msg = msg_elem.text.strip()

            # 检查是否已存在
            existing = SvnRevision.query.filter_by(revision=revision).first()
            if existing:
                return False, existing

            # 新 revision，写入数据库
            svn_rev = SvnRevision(
                revision=revision,
                author=author,
                message=log_msg,
                commit_time=commit_time,
                triggered_run=False,
            )
            db.session.add(svn_rev)
            db.session.commit()

            return True, svn_rev

        except subprocess.TimeoutExpired:
            print("SVN command timed out")
            return False, None
        except Exception as e:
            print(f"SVN check error: {e}")
            return False, None

    def get_log_since(self, revision, limit=50):
        """获取指定 revision 以来的提交日志"""
        try:
            cmd = f'svn log -r {revision}:HEAD --xml -l {limit} {self.repo_url}'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                return []

            root = ET.fromstring(result.stdout)
            logs = []
            for entry in root.findall('.//logentry'):
                rev = entry.get('revision')
                author = entry.find('author')
                msg = entry.find('msg')
                date = entry.find('date')
                logs.append({
                    'revision': rev,
                    'author': author.text if author is not None else '',
                    'message': msg.text.strip() if msg is not None and msg.text else '',
                    'date': date.text if date is not None else '',
                })
            return logs
        except Exception as e:
            print(f"SVN log error: {e}")
            return []
