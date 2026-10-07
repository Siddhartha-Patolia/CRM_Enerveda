import csv
import datetime
import logging
import os

import config

logger = logging.getLogger(__name__)

_LOG_PATH = "token_logs.csv"
_HEADER = ["timestamp", "user", "input_tokens", "output_tokens", "total_tokens"]


def log_usage(user: str, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
    try:
        file_exists = os.path.exists(_LOG_PATH)
        with open(_LOG_PATH, "a", newline="") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(_HEADER)
            writer.writerow(
                [
                    datetime.datetime.now(config.LOCAL_TZ).strftime("%Y-%m-%d %H:%M:%S"),
                    user or "",
                    input_tokens,
                    output_tokens,
                    total_tokens,
                ]
            )
    except Exception:
        logger.exception("Failed to write to token_logs.csv")
