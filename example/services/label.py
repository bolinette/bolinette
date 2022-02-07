from bolinette.data import service, Service

from example.entities import Label


@service("label")
class LabelService(Service[Label]):
    ...
