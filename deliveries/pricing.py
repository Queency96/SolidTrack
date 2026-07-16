from decimal import Decimal


BASE_PRICE = Decimal("1000.00")

PRICE_PER_KM = Decimal("250.00")

WEIGHT_PRICE = {
    "SMALL": Decimal("0"),
    "MEDIUM": Decimal("300"),
    "LARGE": Decimal("700"),
}

VEHICLE_MULTIPLIER = {
    "BIKE": Decimal("1.00"),
    "CAR": Decimal("1.35"),
    "VAN": Decimal("1.80"),
    "TRUCK": Decimal("2.50"),
}

SERVICE_FEE = Decimal("300.00")

INSURANCE_RATE = Decimal("0.01")      # 1%

SURGE_MULTIPLIER = Decimal("1.50")