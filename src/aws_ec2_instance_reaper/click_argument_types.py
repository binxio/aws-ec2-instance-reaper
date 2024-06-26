from typing import Optional

import click
import durations

from aws_ec2_instance_reaper.aws import Tag


class DurationType(click.ParamType):
    """
    A duration in human-readable form as parsed by https://github.com/oleiade/durations
    """

    name = "duration"

    def convert(self, value, param, ctx) -> Optional[durations.Duration]:
        if value is None:
            return value

        if isinstance(value, durations.Duration):
            return value

        try:
            return durations.Duration(value)
        except ValueError as e:
            self.fail(f'Could not parse "{value}" into duration ({e})', param, ctx)


class TagType(click.ParamType):
    """
    an AWS tag in the form <key>=<value> or <key>.
    """

    name = "tag"

    def convert(self, value, param, ctx):
        splits = value.split("=", 1)
        return Tag(key=splits[0], value=None if len(splits) == 1 else splits[1])
