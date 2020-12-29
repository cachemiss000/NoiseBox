import re
from dataclasses import dataclass
from typing import Any, Optional, List, Set, Collection

from pydantic import BaseModel, ValidationError


def class_name(cls: Any) -> str:
    """Returns the resolved, human-friendly class name of a class.

    Not extensively tested - for informational/debug purposes only.
    """
    try:
        if hasattr(cls, "__name__"):
            return cls.__name__
        return cls.__class__.__name__
    except AttributeError:
        return str(cls)


# Quick json model to parse in the errors attached to the ValidationError.
class _ErrorModel(BaseModel):
    loc: List[str]
    msg: str
    type: str
    ctx: Any


# Quick model to extract the location & type of error for hashing into a set.
# We use dataclass instead of BaseModel because BaseModel isn't hashable.
@dataclass(eq=True, frozen=True)
class _PatternError:
    type: str
    loc: str
    regex: str

    def __post_init__(self):
        if not self.type or not re.fullmatch(r'value_error\.str\.regex', self.type):
            raise ValueError("Expected 'type' field to match 'value_error.str.regex', got '%s'" % (self.type,))


@dataclass(eq=True, frozen=True)
class _OtherError:
    loc: str
    msg: str
    type: str


def _try_pattern_error_from(em: _ErrorModel) -> Optional[_PatternError]:
    try:
        return _PatternError(type=em.type,
                             loc=".".join(em.loc),
                             regex=em.ctx.get("pattern", None) if em.ctx else None)
    except ValueError:
        return None


def _other_error_from(em: _ErrorModel) -> _OtherError:
    return _OtherError(loc=".".join(em.loc), msg=em.msg, type=em.type)


def simplify_validation_error(e: ValidationError):
    """Validation errors are long and messy. Return a simplified version

    Because we do so much overloading, ValidationErrors thrown by parse_raw can cover between 2 and 5+
    fields/schemas, explaining how the model wouldn't fit each one individually. The client probably
    doesn't want to sit through parsing that kind of error, so we work to return a simplified version.

    TODO: This is a quick and dirty function. Come up with something a bit more comprehensive and 'better'.
    """

    pattern_err_set: Set[_PatternError] = set()
    other_err_set: Set[_OtherError] = set()
    for err in e.errors():
        em = _ErrorModel(**err)
        pm = _try_pattern_error_from(em)
        if pm:
            pattern_err_set.add(pm)
            continue
        other_err_set.add(_other_error_from(em))

    pattern_err_strings = list(
        "\t'%s': '%s'" % (p_em.loc, p_em.regex) for p_em in pattern_err_set
    )
    other_err_strings = list(
        "\t%s(%s): '%s'" % (o_em.type, o_em.loc, o_em.msg) for o_em in other_err_set
    )

    msg = "Message failed validation."
    if pattern_err_strings:
        msg += "\n  'Regex' type failures: {\n%s\n}" % (",\n".join(pattern_err_strings),)
    if other_err_strings:
        msg += "\n  'Other' type failures: {\n%s\n}" % (",\n".join(other_err_strings),)
    return msg


def group_by(obj_list: Collection[Any], group_size: int) -> Collection[Collection[Any]]:
    return list(zip(*(iter(obj_list),) * group_size))