import logging
import os

logging.basicConfig(
    format="%(levelname)s: %(message)s", level=os.getenv("LOG_LEVEL", "INFO")
)
log = logging.getLogger("aws_ec2_instance_reaper")
