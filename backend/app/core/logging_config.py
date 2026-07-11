"""统一日志配置。

全局级别由配置文件 LOG_LEVEL 控制（默认 INFO）。
模块级覆盖通过环境变量 LOG_LEVEL_<NAME>=DEBUG 设置，
例如 LOG_LEVEL_INGEST=DEBUG。
"""

import logging
import os
import sys

# 模块级覆盖：以 getLogger("ingest") 为例，设 LOG_LEVEL_INGEST=DEBUG
_MODULE_OVERRIDES: dict[str, int] = {}
for key, value in os.environ.items():
    if key.startswith("LOG_LEVEL_"):
        name = key[len("LOG_LEVEL_"):].lower()
        level = getattr(logging, value.upper(), None)
        if isinstance(level, int):
            _MODULE_OVERRIDES[name] = level


class _ColoredFormatter(logging.Formatter):
    """终端友好：级别字段带颜色。"""

    COLORS = {
        logging.DEBUG:    "\033[36m",  # cyan
        logging.INFO:     "\033[32m",  # green
        logging.WARNING:  "\033[33m",  # yellow
        logging.ERROR:    "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        levelname = f"{color}{record.levelname:<7}{self.RESET}"
        record.levelname_fmt = levelname  # type: ignore[attr-defined]
        return super().format(record)


_FORMAT = (
    "%(asctime)s [%(levelname_fmt)s] %(name)-12s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(log_level: str = "INFO") -> None:
    """初始化全局日志配置，在 FastAPI startup 中调用一次。

    参数 log_level 来自配置文件 settings.LOG_LEVEL。
    """
    root = logging.getLogger()
    root.handlers.clear()

    # 全局级别（来自配置文件）
    level = getattr(logging, log_level.upper(), logging.INFO)
    root.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_ColoredFormatter(_FORMAT, _DATE_FORMAT))
    root.addHandler(handler)

    # 模块级覆盖（来自环境变量 LOG_LEVEL_<NAME>）
    for name, lvl in _MODULE_OVERRIDES.items():
        logging.getLogger(name).setLevel(lvl)
