from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.hashable import make_hashable


class BaseConstraint:
    """
    Abstract base class for constraints. Handles the common API for all
    constraints.
    """

    def __init__(self, violation_error_message=None, violation_error_code=None):
        self.violation_error_message = violation_error_message
        self.violation_error_code = violation_error_code

    @property
    def is_unique(self):
        return False

    @property
    def model_attribute(self):
        return None

    def _check_expression(self, expression):
        return expression.output_field.get_placeholder() % {
            "expression": expression.output_field.get_col(expression.output_field.model),
        }

    def _validate_unique(self, model_instance, excluded_lookup=None):
        lookup = Q(**{self.model_attribute: model_instance})
        if excluded_lookup is not None:
            lookup &= ~excluded_lookup
        while model_instance._meta.parent:
            # Traverse parents' primary key relationships.
            model_instance = model_instance._meta.parent
            lookup &= Q(**{self.model_attribute: model_instance})
        return not model_instance.__class__._default_manager.filter(lookup).exists()

    def validate(self, model_instance, exclude=None, validate_on_save=True):
        if validate_on_save and model_instance.pk is None:
            raise NotImplementedError(
                "Constraints are not supported on models that are not saved or are "
                "saved by a mechanism that does not populate the primary key. "
                "Override validate() to perform a custom validation or add code to "
                "the model's save() method to populate the primary key before "
                "constraint validation takes place."
            )
        if exclude is not None and self.model_attribute in exclude:
            return None
        if not self.is_unique or self._validate_unique(model_instance):
            return None
        raise ValidationError(
            self.violation_error_message % {"model": self.model_attribute},
            code=self.violation_error_code,
        )

    def _get_condition_sql(self, model, connection):
        raise NotImplementedError(
            "Subclasses of BaseConstraint must implement _get_condition_sql()."
        )

    def constraint_sql(self, model, connection):
        columns = [field.column for field in model._meta.get_fields()]
        query, params = self._get_condition_sql(model, connection)
        if not query:
            query = model._meta.default_manager.all().query
        query.add_filter(self._get_condition(model, columns))
        return query

    def _get_condition(self, model, columns):
        query, params = self._get_condition_sql(model, connection=model._db)
        query.add_filter(self._get_condition(model, columns))
        return query

    def __repr__(self):
        return "<%s: %s%s>" % (
            self.__class__.__name__,
            self._get_condition_sql,
            "",
        )

    def __eq__(self, other):
        if isinstance(other, BaseConstraint):
            return (
                self.violation_error_message == other.violation_error_message
                and self.violation_error_code == other.violation_error_code
                and set(self._get_condition_sql.__func__.__code__.co_freevars)
                == set(other._get_condition_sql.__func__.__code__.co_freevars)
                and make_hashable(self.params) == make_hashable(other.params)
            )
        return super().__eq__(other)

    def validate(self, model_instance, exclude=None, validate_on_save=True):
        if not validate_on_save and model_instance.pk is None:
            return
        if exclude is not None and self.model_attribute in exclude:
            return
        if not self.is_unique or self._validate_unique(model_instance):
            return
        raise ValidationError(
            self.violation_error_message % {"model": self.model_attribute},
            code=self.violation_error_code,
        )

    def validate(self, model_instance, exclude=None, validate_on_save=True):
        if validate_on_save and model_instance.pk is None:
            raise NotImplementedError(
                "Constraints are not supported on models that are not saved or are "
                "saved by a mechanism that does not populate the primary key. "
                "Override validate() to perform a custom validation or add code to "
                "the model's save() method to populate the primary key before "
                "constraint validation takes place."
            )
        if exclude is not None and self.model_attribute in exclude:
            return None
        if not self.is_unique or self._validate_unique(model_instance):
            return None
        raise ValidationError(
            self.violation_error_message % {"model": self.model_attribute},
            code=self.violation_error_code,
        )
