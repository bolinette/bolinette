from bolinette.exceptions import ParamConflictError


class Mapper:
    def update(self, model, entity, params, patch=False):
        errors = []
        for column in model.__table__.columns:
            key = column.key
            if column.primary_key or (key not in params and patch):
                continue
            original = getattr(entity, key)
            new = params.get(key, None)
            if original == new:
                continue
            if column.unique and new is not None:
                if model.query.filter(getattr(model, key) == new).first() is not None:
                    errors.append((key, new))
            setattr(entity, key, new)
        if len(errors) > 0:
            raise ParamConflictError(params=errors)


mapper = Mapper()
