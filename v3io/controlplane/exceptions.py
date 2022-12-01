class ResourceDeleteException(Exception):
    def __str__(self):
        return "This resource is not delete-able"


class ResourceUpdateException(Exception):
    def __str__(self):
        return "This resource is not update-able"


class ResourceListException(Exception):
    def __str__(self):
        return "This resource is not list-able"
