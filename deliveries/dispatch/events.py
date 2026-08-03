from dataclasses import dataclass

from deliveries.models import (
    Delivery,
    DeliveryAssignment,
    DeliveryOffer,
)


@dataclass(frozen=True)
class DeliveryOfferCreatedEvent:
    offer: DeliveryOffer


@dataclass(frozen=True)
class DeliveryOfferAcceptedEvent:
    assignment: DeliveryAssignment


@dataclass(frozen=True)
class DeliveryOfferRejectedEvent:
    offer: DeliveryOffer


@dataclass(frozen=True)
class DeliveryOfferExpiredEvent:
    offer: DeliveryOffer


@dataclass(frozen=True)
class DeliveryAssignedEvent:
    assignment: DeliveryAssignment


@dataclass(frozen=True)
class DeliveryRedispatchedEvent:
    delivery: Delivery



@dataclass(frozen=True)
class DeliveryCreatedEvent:
    delivery: Delivery