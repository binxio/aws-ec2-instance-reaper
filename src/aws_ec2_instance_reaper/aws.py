import pytz
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
import durations
from durations import Duration
from durations.exceptions import ScaleFormatError, InvalidTokenError
import logging


class Tag(object):
    """
    a key value pair.

    >>> Tag("Name")
    Name
    >>> Tag("Name", "Value")
    Name=Value
    """

    def __init__(self, key: str, value: Optional[str] = None):
        super(Tag, self).__init__()
        self.key = key
        self.value = value

    @staticmethod
    def from_string(s: str) -> "Tag":
        """
        Creates a tag from a string representation.

        >>> Tag.from_string("Name=Value")
        Name=Value
        >>> Tag.from_string("Name")
        Name
        >>> Tag.from_string("Name=ab=c").value
        'ab=c'
        """
        splits = s.split("=", 1)
        return Tag(key=splits[0], value=None if len(splits) == 1 else splits[1])

    def __repr__(self) -> str:
        return f"{self.key}={self.value}" if self.value else self.key


class TagFilter(object):
    """
    A boto3 tag filter

    >>> TagFilter([Tag("Name")])
    [{'Name': 'tag:Name', 'Values': []}]

    >>> TagFilter([Tag("Name", "Value")])
    [{'Name': 'tag:Name', 'Values': ['Value']}]

    >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value2")])
    [{'Name': 'tag:Name', 'Values': ['Value', 'Value2']}]

    >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value")])
    [{'Name': 'tag:Name', 'Values': ['Value']}]

    >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value2"), Tag("Region", "eu-west-1a"), Tag("Region", "eu-west-1b")])
    [{'Name': 'tag:Name', 'Values': ['Value', 'Value2']}, {'Name': 'tag:Region', 'Values': ['eu-west-1a', 'eu-west-1b']}]
    """

    def __init__(self, tags: List[Tag]):
        self.filter = {}
        for tag in tags:
            key = f"tag:{tag.key}"
            if not self.filter.get(key):
                self.filter[key] = []
            if tag.value:
                if tag.value not in self.filter[key]:
                    self.filter[key].append(tag.value)

    def to_api(self):
        """
        returns an array of dictionaries with `Name` and `Values` set as expected by the boto3 api.

        >>> TagFilter([Tag("Name", "Value"), Tag("Name", "Value2")]).to_api()
        [{'Name': 'tag:Name', 'Values': ['Value', 'Value2']}]

        """
        return [{"Name": f"{k}", "Values": self.filter[k]} for k in self.filter.keys()]

    def __repr__(self):
        return str(self.to_api())


class ReaperTagFilter(TagFilter):
    """
    A reaper tag filter, which has a predefined filter for tag:ExpiresAfter and tag:ExpirationAction=stop,terminate.

    >>> ReaperTagFilter()
    [{'Name': 'tag:ExpiresAfter', 'Values': ['*']}, {'Name': 'tag:ExpirationAction', 'Values': ['stop', 'terminate']}]
    """

    def __init__(self, tags: list[Tag] = None):
        if tags is None:
            tags = []
        super(ReaperTagFilter, self).__init__(tags)
        self.filter["tag:ExpiresAfter"] = ["*"]
        self.filter["tag:ExpirationAction"] = ["stop", "terminate"]


class EC2Instance(dict):
    """
    EC2 instances are returned by the boto api.
    """

    def __init__(self, i):
        super(EC2Instance, self).__init__()
        self.update(i)

    @property
    def instance_id(self):
        return self["InstanceId"]

    @property
    def tags(self):
        return {t["Key"]: t["Value"] for t in self.get("Tags")}

    @property
    def name(self):
        return self.tags.get("Name", self.instance_id)

    @property
    def launch_time(self):
        return self.get("LaunchTime")

    @property
    def expires_after(self) -> Optional[timedelta]:
        expires_at = self.tags.get("ExpiresAfter", None)
        if not expires_at:
            return None

        try:
            return timedelta(seconds=Duration(expires_at).to_seconds())
        except (InvalidTokenError, ScaleFormatError) as e:
            logging.warning(
                'could not parse "ExpiresAfter=%s" of instance %s, (%s)',
                expires_at,
                self,
                e,
            )
        return None

    @property
    def expiration_action(self) -> Optional[str]:
        action: str = self.tags.get("ExpirationAction", "")
        if not action or action.lower() not in ["stop", "terminate"]:
            if action:
                logging.warning(
                    "invalid expiration action %s specified for instance %s",
                    action,
                    self,
                )
            return None

        return action.lower()

    @property
    def time_since_launch(self) -> timedelta:
        return pytz.utc.localize(dt=datetime.utcnow()) - self.launch_time

    @property
    def expires_at(self) -> datetime:
        return self.launch_time + self.expires_after

    @property
    def time_left(self) -> timedelta:
        return self.time_since_launch - self.expires_after

    @property
    def state(self):
        return self.get("State", {}).get("Name")

    def __str__(self):
        return f"{self.instance_id} ({self.name})"
