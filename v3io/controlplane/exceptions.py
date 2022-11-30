class RetryUntilSuccessfulInProgressErrorMessage(Exception):
    def __init__(self, message, *, variables=None):
        super().__init__(message)
        self.variables = variables if variables else {}
        self.message = message


class ResourceDeleteException(Exception):
    def __str__(self):
        return "This resource is not delete-able"


class ResourceUpdateException(Exception):
    def __str__(self):
        return "This resource is not update-able"


class ResourceListException(Exception):
    def __str__(self):
        return "This resource is not list-able"
