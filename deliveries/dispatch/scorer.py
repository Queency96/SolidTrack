class RiderScorer:
    @staticmethod
    def score(
        rider,
        delivery,
    ):
        score = 0
        score += rider.rating * 10
        score -= rider.active_jobs * 5

        return score