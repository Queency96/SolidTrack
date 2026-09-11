Binary file [35mcart/models/__pycache__/cart_item.cpython-312.pyc[m matches
[35mcart/models/cart_item.py[m[36m:[m[32m270[m[36m:[m            # Variant [1;31mavailability[m
[35mcart/models/cart_item.py[m[36m:[m[32m273[m[36m:[m            if not self.variant.is_[1;31mavailable[m:
[35mcart/models/cart_item.py[m[36m:[m[32m279[m[36m:[m                            "is not [1;31mavailable[m."
[35mcart/models/cart_item.py[m[36m:[m[32m307[m[36m:[m            # Product [1;31mavailability[m
[35mcart/models/cart_item.py[m[36m:[m[32m310[m[36m:[m            if not self.product.is_[1;31mavailable[m:
[35mcart/models/cart_item.py[m[36m:[m[32m316[m[36m:[m                            "[1;31mavailable[m."
[35mcart/models/cart_item.py[m[36m:[m[32m451[m[36m:[m        Return the most specific SKU [1;31mavailable[m.
[35mcart/models/cart_item.py[m[36m:[m[32m481[m[36m:[m    # [1;31mAvailable[m Stock
[35mcart/models/cart_item.py[m[36m:[m[32m485[m[36m:[m    def [1;31mavailable[m_stock(self):
[35mcart/models/cart_item.py[m[36m:[m[32m487[m[36m:[m        Return the currently [1;31mavailable[m stock.
[35mcart/models/cart_item.py[m[36m:[m[32m520[m[36m:[m            <= self.[1;31mavailable[m_stock
[35mcart/models/cart_item.py[m[36m:[m[32m524[m[36m:[m    # [1;31mAvailability[m
[35mcart/models/cart_item.py[m[36m:[m[32m528[m[36m:[m    def is_[1;31mavailable[m(self):
[35mcart/models/cart_item.py[m[36m:[m[32m537[m[36m:[m                self.variant.is_[1;31mavailable[m
[35mcart/models/cart_item.py[m[36m:[m[32m542[m[36m:[m            self.product.is_[1;31mavailable[m
[35mcart/serializers/cart_item.py[m[36m:[m[32m51[m[36m:[m    # [1;31mAvailability[m
[35mcart/serializers/cart_item.py[m[36m:[m[32m54[m[36m:[m    is_[1;31mavailable[m = serializers.ReadOnlyField()
[35mcart/serializers/cart_item.py[m[36m:[m[32m62[m[36m:[m    [1;31mavailable[m_stock = serializers.ReadOnlyField()
[35mcart/serializers/cart_item.py[m[36m:[m[32m111[m[36m:[m            # [1;31mAvailability[m
[35mcart/serializers/cart_item.py[m[36m:[m[32m112[m[36m:[m            "is_[1;31mavailable[m",
[35mcart/serializers/cart_item.py[m[36m:[m[32m116[m[36m:[m            "[1;31mavailable[m_stock",
[35mcart/serializers/cart_item.py[m[36m:[m[32m142[m[36m:[m            "is_[1;31mavailable[m",
[35mcart/serializers/cart_item.py[m[36m:[m[32m145[m[36m:[m            "[1;31mavailable[m_stock",
[35mcart/services/cart_service.py[m[36m:[m[32m27[m[36m:[m    • Validate cart [1;31mavailability[m
[35mcart/services/cart_service.py[m[36m:[m[32m118[m[36m:[m        if not product.is_[1;31mavailable[m:
[35mcart/services/cart_service.py[m[36m:[m[32m121[m[36m:[m                "Product is not [1;31mavailable[m."
[35mcart/services/cart_service.py[m[36m:[m[32m246[m[36m:[m        cls._validate_item_[1;31mavailability[m(
[35mcart/services/cart_service.py[m[36m:[m[32m316[m[36m:[m        cls._validate_item_[1;31mavailability[m(
[35mcart/services/cart_service.py[m[36m:[m[32m404[m[36m:[m        cls._validate_item_[1;31mavailability[m(
[35mcart/services/cart_service.py[m[36m:[m[32m570[m[36m:[m                cls._validate_item_[1;31mavailability[m(
[35mcart/services/cart_service.py[m[36m:[m[32m771[m[36m:[m        if not variant.is_[1;31mavailable[m:
[35mcart/services/cart_service.py[m[36m:[m[32m775[m[36m:[m                "is not [1;31mavailable[m."
[35mcart/services/cart_service.py[m[36m:[m[32m789[m[36m:[m        Validate [1;31mavailable[m inventory.
[35mcart/services/cart_service.py[m[36m:[m[32m824[m[36m:[m    # [1;31mAvailability[m Validation
[35mcart/services/cart_service.py[m[36m:[m[32m828[m[36m:[m    def _validate_item_[1;31mavailability[m(
[35mcart/services/cart_service.py[m[36m:[m[32m838[m[36m:[m            if not item.variant.is_[1;31mavailable[m:
[35mcart/services/cart_service.py[m[36m:[m[32m842[m[36m:[m                    "is no longer [1;31mavailable[m."
[35mcart/services/cart_service.py[m[36m:[m[32m847[m[36m:[m        if not item.product.is_[1;31mavailable[m:
[35mcart/services/cart_service.py[m[36m:[m[32m850[m[36m:[m                "Product is no longer [1;31mavailable[m."
[35mcheckout/services/checkout_service.py[m[36m:[m[32m791[m[36m:[m                if not product.is_[1;31mavailable[m:
[35mcheckout/services/checkout_service.py[m[36m:[m[32m795[m[36m:[m                        "no longer [1;31mavailable[m."
[35mcheckout/services/checkout_service.py[m[36m:[m[32m798[m[36m:[m                if not variant.is_[1;31mavailable[m:
[35mcheckout/services/checkout_service.py[m[36m:[m[32m803[m[36m:[m                        "[1;31mavailable[m."
[35mcheckout/services/checkout_service.py[m[36m:[m[32m856[m[36m:[m                if not product.is_[1;31mavailable[m:
[35mcheckout/services/checkout_service.py[m[36m:[m[32m860[m[36m:[m                        "no longer [1;31mavailable[m."
