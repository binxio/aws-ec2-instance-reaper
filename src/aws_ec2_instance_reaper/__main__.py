import logging
import os
from typing import List

import boto3
import click
import humanize

from aws_ec2_instance_reaper.aws import Tag
from aws_ec2_instance_reaper.click_argument_types import TagType
from aws_ec2_instance_reaper.logger import log
from aws_ec2_instance_reaper.reaper import (
    reap_expired_instances,
    list_ephemeral_instances,
)
from datetime import timedelta


@click.group(help="manage ephemeral ec2 instances")
@click.option("--dry-run", is_flag=True, default=False, help="do not change anything")
@click.option("--verbose", is_flag=True, default=False, help="output")
@click.pass_context
def main(ctx, dry_run, verbose):
    if dry_run:
        logging.basicConfig(
            format="dry-run: %(levelname)s: %(message)s",
            level=os.getenv("LOG_LEVEL", "INFO"),
        )

    log.setLevel(os.getenv("LOG_LEVEL", "DEBUG" if verbose else "INFO"))
    ctx.obj = ctx.params


@main.command(help="reap expired ephemeral ec2 instances")
@click.option(
    "--tag",
    "tags",
    type=TagType(),
    required=False,
    multiple=True,
    help="Tags to filter instances by in the format Name=Value. Can be specified multiple times.",
)
@click.pass_context
def reap(ctx, tags):
    reap_expired_instances(
        boto3.client("ec2"),
        dry_run=ctx.obj["dry_run"],
        tags=tags,
    )


@main.command(name="list", help="ephemeral ec2 instances")
@click.option(
    "--tag",
    "tags",
    type=TagType(),
    required=False,
    multiple=True,
    default=[],
    help="Tags to filter instances by in the format Name=Value. Can be specified multiple times.",
)
@click.option(
    "--state",
    "state",
    type=str,
    required=False,
    multiple=True,
    default=["running"],
    help="of instances to list",
)
def list_instances(tags: List[Tag], state: List[str]):
    instances = list_ephemeral_instances(boto3.client("ec2"), tags=tags)
    for i in filter(lambda i: i.state in state, instances):
        expires_in = "expires in" if i.time_left < timedelta(0) else "expired"
        print(f"{i} {expires_in} {humanize.naturaltime(i.time_left)} - {i.state}")
    log.info(f"{len(instances)} ephemeral ec2 instances found")


if __name__ == "__main__":
    main()
