from dataclasses import dataclass
from deliveries.models.delivery_offer import DeliveryOffer
from deliveries.models.delivery_assignment import DeliveryAssignment
from deliveries.models.delivery import Delivery


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