import os
from datetime import timedelta
from typing import List

import boto3
import humanize
import durations
from botocore.client import BaseClient

from typing import Tuple
from aws_ec2_instance_reaper.aws import EC2Instance, Tag, ReaperTagFilter
from aws_ec2_instance_reaper.logger import log
from aws_ec2_instance_reaper.schema import validate


def list_ephemeral_instances(ec2: BaseClient, tags: List[Tag]) -> List[EC2Instance]:
    paginator = ec2.get_paginator("describe_instances")
    instances = []

    for response in paginator.paginate(Filters=ReaperTagFilter(tags).to_api()):
        for reservation in response["Reservations"]:
            for instance in map(lambda i: EC2Instance(i), reservation["Instances"]):
                if instance.expiration_action and instance.expires_after:
                    log.debug(
                        "found instance %s launched %s, now in state %s",
                        instance,
                        humanize.naturaltime(instance.time_since_launch),
                        instance.state,
                    )
                    instances.append(instance)
    return instances


def expired_instances(
    instances: List[EC2Instance],
    states: List[str],
) -> List[EC2Instance]:
    return list(
        filter(
            lambda i: i.state in states and i.time_since_launch > i.expires_after,
            instances,
        )
    )


def reap_expired_instances(ec2: BaseClient, dry_run: bool, tags: List[Tag]):
    count = 0
    instances = expired_instances(
        list_ephemeral_instances(ec2, tags),
        ["running", "stopped"],
    )

    for instance in instances:
        name = "stopping" if instance.expiration_action == "stop" else "terminating"
        log.info(
            "%s %s created %s",
            name,
            instance,
            humanize.naturaltime(instance.time_since_launch),
        )
        count = count + 1
        if not dry_run:
            if instance.expiration_action == "terminate":
                ec2.terminate_instances(InstanceIds=[instance.instance_id])
            else:
                if instance.state == "running":
                    ec2.stop_instances(InstanceIds=[instance.instance_id])
    log.info(f"total of {len(instances)} running instances reaped")


def handler(request, _):
    log.setLevel(os.getenv("LOG_LEVEL", "INFO"))

    if validate(request):
        dry_run = request.get("dry_run", False)
        tags = request.get("tags", [])
        tags = [Tag.from_string(s) for s in tags]

        reap_expired_instances(
            ec2=boto3.client("ec2"),
            dry_run=dry_run,
            tags=tags,
        )


if __name__ == "__main__":
    handler({"dry_run": True, "tags": []}, {})
