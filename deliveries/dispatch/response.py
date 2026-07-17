class DispatchResponseService:

    @staticmethod
    def wait_for_response(
        delivery,
        rider,
        timeout,
    ):
        """
        Wait for the rider to accept or reject.

        This will later be implemented using:
        - Django Channels
        - Redis
        - Celery
        """

        return False