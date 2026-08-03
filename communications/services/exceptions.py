class CommunicationException(Exception):
    """Base communication exception."""


class EmailException(CommunicationException):
    pass


class SMSException(CommunicationException):
    pass


class PushNotificationException(
    CommunicationException,
):
    pass