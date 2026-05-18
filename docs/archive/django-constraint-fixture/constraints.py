"""
Classes to check a condition on a model field.
"""
import re

from django.core.exceptions import ValidationError
from django.db import connection
from django.utils.regex_helper import _lazy_re_compile


class BaseConstraint:
    """Abstract base class for all constraints."""

    def __init__(self, violation_error_message=None, violation_error_code=None):
        if violation_error_message is not None:
            if not isinstance(violation_error_message, str):
                raise ValueError("violation_error_message must be a string.")
        if violation_error_code is not None:
            if not isinstance(violation_error_code, str):
                raise ValueError("violation_error_code must be a string.")
        self.violation_error_message = violation_error_message or (
            "Constraint %(name)s is violated."
        )
        self.violation_error_code = violation_error_code

    def __repr__(self):
        return "<%(cls)s: %(params)s>" % {
            "cls": self.__class__.__name__,
            "params": ", ".join(self._param_str()),
        }

    def __str__(self):
        return "%s(%s)" % (
            self.__class__.__name__,
            ", ".join(self._param_str()),
        )

    def _param_str(self):
        return [
            "%s=%r" % (k, self.__dict__[k])
            for k in sorted(self.__dict__)
            if not k.startswith("_")
        ]

    def validate(self, model, instance, exclude=None, using=None):
        """
        Raise a ValidationError if the constraint is not violated.
        """
        if exclude is None:
            exclude = set()
        if using is None:
            using = connection.alias
        errors = []
        for name, value in self._check_expression(model, instance, exclude, using):
            if not self.is_valid(model, instance, name=name, value=value):
                if self.violation_error_code:
                    errors.append(
                        ValidationError(
                            message=self.violation_error_message,
                            code=self.violation_error_code,
                            params={"name": self.custom_error_name or name, "value": value},
                        )
                    )
                else:
                    errors.append(
                        ValidationError(
                            message=self.violation_error_message,
                            params={"name": self.custom_error_name or name, "value": value},
                        )
                    )
        if errors:
            raise ValidationError(errors)

    def _check_expression(self, model, instance, exclude, using):
        """
        Evaluate the expression for the constraint and return a list of
        (field_name, value) pairs for evaluation of is_valid().
        """
        raise NotImplementedError(
            "Subclasses of BaseConstraint must implement _check_expression()."
        )

    def is_valid(self, model, instance, name, value):
        """
        Return True if the value under the constraint is valid.
        """
        raise NotImplementedError(
            "Subclasses of BaseConstraint must implement is_valid()."
        )

    def constraint_key(self):
        """Return a key that identifies this constraint for a model."""
        raise NotImplementedError(
            "Subclasses of BaseConstraint must implement constraint_key()."
        )


class CheckConstraint(BaseConstraint):
    """Encapsulate the logic of a check constraint."""

    def __init__(
        self, check, name, violation_error_message=None, violation_error_code=None
    ):
        self.check = check
        if not isinstance(name, str) or not name:
            raise ValueError("Constraint must have a non-empty name.")
        super().__init__(violation_error_message, violation_error_code)
        self.name = name

    def __repr__(self):
        return "<%(cls)s: check=%(check)s, name=%(name)s>" % {
            "cls": self.__class__.__name__,
            "check": self.check,
            "name": self.name,
        }

    def _param_str(self):
        return ["check=%r" % self.check] + super()._param_str()

    def constraint_key(self):
        return (self.__class__, self.check)

    def _check_expression(self, model, instance, exclude, using):
        def check_expression(name):
            if name in exclude:
                raise ValidationError(
                    "The field '%s' is excluded from validation." % name
                )
            try:
                value = getattr(instance, name)
            except AttributeError:
                raise ValidationError(
                    "The field '%s' does not exist on the model '%s'."
                    % (name, model._meta.label)
                )
            return name, value

        if self.check.contains_aggregate:
            raise ValidationError(
                "CheckConstraint contains an aggregate expression."
            )
        if self.check.contains_over_clause:
            raise ValidationError(
                "CheckConstraint contains a window expression."
            )
        for raw_name in self.check.flatten():
            if raw_name:
                yield check_expression(raw_name)

    def is_valid(self, model, instance, name, value):
        return bool(self.check.resolve_expression(model._meta.db_table))


class UniqueConstraint(BaseConstraint):
    """Encapsulate the logic of a unique constraint."""

    def __init__(
        self,
        fields,
        name,
        condition=None,
        deferrable=None,
        include=None,
        opclasses=None,
        violation_error_message=None,
        violation_error_code=None,
    ):
        if not isinstance(fields, (tuple, list)):
            raise ValueError("UniqueConstraint.fields must be a list or tuple.")
        if not fields:
            raise ValueError("UniqueConstraint.fields must not be empty.")
        if not isinstance(name, str) or not name:
            raise ValueError("Constraint must have a non-empty name.")
        if deferrable and not isinstance(deferrable, deferrable.__class__):
            raise ValueError("UniqueConstraint.deferrable must be a Deferable type.")
        if condition and not (
            hasattr(condition, "resolve_expression")
            and condition.flatten()
        ):
            raise ValueError("UniqueConstraint.condition must be a Q object.")
        if include and not isinstance(include, (tuple, list)):
            raise ValueError("UniqueConstraint.include must be a list or tuple.")
        if opclasses and not isinstance(opclasses, (tuple, list)):
            raise ValueError("UniqueConstraint.opclasses must be a list or tuple.")
        self.fields = tuple(fields)
        self.condition = condition
        self.deferrable = deferrable
        self.include = tuple(include) if include else None
        self.opclasses = tuple(opclasses) if opclasses else ()
        super().__init__(violation_error_message, violation_error_code)
        self.name = name

    def __repr__(self):
        return "<%(cls)s: fields=%(fields)s, name=%(name)s>" % {
            "cls": self.__class__.__name__,
            "fields": self.fields,
            "name": self.name,
        }

    def _param_str(self):
        params = [
            "fields=%r" % (self.fields,),
            "name=%r" % self.name,
        ]
        if self.condition:
            params.append("condition=%r" % self.condition)
        if self.deferrable:
            params.append("deferrable=%r" % self.deferrable)
        if self.include:
            params.append("include=%r" % (self.include,))
        if self.opclasses:
            params.append("opclasses=%r" % (self.opclasses,))
        return params + super()._param_str()

    def constraint_key(self):
        return (self.__class__, self.fields, self.condition, self.deferrable)

    def _check_expression(self, model, instance, exclude, using):
        def check_expression(name):
            if name in exclude:
                raise ValidationError(
                    "The field '%s' is excluded from validation." % name
                )
            try:
                value = getattr(instance, name)
            except AttributeError:
                raise ValidationError(
                    "The field '%s' does not exist on the model '%s'."
                    % (name, model._meta.label)
                )
            return name, value

        if self.condition:
            if self.condition.contains_aggregate:
                raise ValidationError(
                    "UniqueConstraint.condition contains an aggregate expression."
                )
            if self.condition.contains_over_clause:
                raise ValidationError(
                    "UniqueConstraint.condition contains a window expression."
                )
            for raw_name in self.condition.flatten():
                if raw_name:
                    yield check_expression(raw_name)
        for field_name in self.fields:
            yield check_expression(field_name)

    def is_valid(self, model, instance, name, value):
        if self.condition:
            if not self.condition.resolve_expression(model._meta.db_table):
                return True
        return True


class Deferrable(Enum):
    """Enumerates the deferrable options for UniqueConstraint"""

    DEFERRED = "DEFERRED"
    NOT_DEFERRABLE = "NOT DEFERRABLE"


Enum = Deferrable
