class DispatchException(Exception):
    """
    Base exception for all dispatch-related errors.
    """
    default_message = "Dispatch operation failed."

    def __init__(self, message=None):
        super().__init__(message or self.default_message)


class NoAvailableRider(DispatchException):
    default_message = (
        "No available riders were found for this delivery."
    )


class RiderRejectedDelivery(DispatchException):
    default_message = (
        "The rider rejected the delivery request."
    )


class RiderTimedOut(DispatchException):
    default_message = (
        "The rider did not respond before the timeout."
    )


class RiderAlreadyAssigned(DispatchException):
    default_message = (
        "The rider is already assigned to another delivery."
    )


class DeliveryAlreadyAssigned(DispatchException):
    default_message = (
        "This delivery has already been assigned."
    )


class DeliveryAlreadyCompleted(DispatchException):
    default_message = (
        "This delivery has already been completed."
    )


class DeliveryAlreadyCancelled(DispatchException):
    default_message = (
        "This delivery has been cancelled."
    )


class RiderNotEligible(DispatchException):
    default_message = (
        "The selected rider is not eligible for this delivery."
    )


class InvalidAssignmentState(DispatchException):
    default_message = (
        "The assignment cannot be performed in the current state."
    )


class DispatchRadiusExceeded(DispatchException):
    default_message = (
        "No rider found within the configured search radius."
    )


class DispatchConfigurationError(DispatchException):
    default_message = (
        "Dispatch configuration is invalid."
    )