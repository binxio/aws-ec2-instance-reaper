import durations
from durations.exceptions import ScaleFormatError, InvalidTokenError
from jsonschema import Draft7Validator, FormatChecker, validators
from jsonschema.exceptions import ValidationError

from aws_ec2_instance_reaper.logger import log

schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "properties": {
        "dry_run": {
            "type": "boolean",
            "description": "if you only want output",
            "default": False,
        },
        "tags": {
            "type": "array",
            "description": "to select EC2 instances with",
            "minItems": 1,
            "items": {"type": "string", "minLength": 1},
        },
    },
}


@FormatChecker.cls_checks("duration")
def duration_checker(value) -> bool:
    """
    checks whether the `value` is a valid duration.

    >>> duration_checker({})
    False

    >>> duration_checker(1.0)
    False

    >>> duration_checker("2h")
    True

    >>> duration_checker("hundred days")
    False
    """
    try:
        if isinstance(value, str):
            durations.Duration(value)
            return True
    except (InvalidTokenError, ScaleFormatError) as e:
        pass
    return False


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for prop, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(prop, subschema["default"])

        for error in validate_properties(
            validator,
            properties,
            instance,
            schema,
        ):
            yield error

    return validators.extend(
        validator_class,
        {"properties": set_defaults},
    )


validator = extend_with_default(Draft7Validator)(schema, format_checker=FormatChecker())


def validate(request: dict) -> bool:
    """
    return True and completes the missing values if the dictionary matches the schema, otherwise False.
    >>> validate({"dry_run": "stoep"})
    False
    >>> validate({"dry_run": True})
    True
    >>> validate({"tags": []})
    False
    >>> validate({"tags": ["Name=Packer"], "dry_run": False})
    True
    >>> x = {}
    >>> validate(x)
    True
    >>> print(x)
    {'dry_run': False}
    """
    try:
        validator.validate(request)
        return True
    except ValidationError as e:
        log.error("invalid request received: %s" % str(e.message))
        return False
