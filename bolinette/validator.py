from bolinette.exceptions import ParamMissingError, ParamConflictError


class Validator:
    def model(self, model, params, **kwargs):
        excluding = kwargs.get('excluding', [])
        errors = []
        valid = {}
        for column in model.__table__.columns:
            key = column.key
            if column.primary_key or key in excluding:
                continue
            value = params.get(key, None)
            if column.unique and value is not None:
                criteria = getattr(model, key) == value
                if model.query.filter(criteria).first() is not None:
                    errors.append((key, value))
            valid[key] = value
        if len(errors) > 0:
            raise ParamConflictError(params=errors)
        return valid

    def payload(self, definition, params):
        errors = []
        valid = {}
        for field in definition.fields:
            value = params.get(field.name, None)
            if field.required and (value is None or len(value) <= 0):
                errors.append(field.name)
            valid[field.name] = value
        if len(errors) > 0:
            raise ParamMissingError(params=errors)
        return valid


validate = Validator()
