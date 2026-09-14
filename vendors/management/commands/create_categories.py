"""
Management command that seeds the full e-commerce
product category hierarchy.

Categories are organised in up to three levels:

    Level 1 -- Root  (e.g. Electronics)
    Level 2 -- Child (e.g. Mobile Phones & Tablets)
    Level 3 -- Grandchild (e.g. Smartphones)

The command is idempotent -- every category is looked up
by its globally-unique slug, so re-running it will never
create duplicates.

Example::

    python manage.py create_categories
"""

from django.core.management.base import BaseCommand
from django.utils.text import slugify
from vendors.models import ProductCategory, CategoryOption
from vendors.management.commands.category_options_data import CATEGORY_OPTIONS


# ==========================================================
# CATEGORY TREE
# ==========================================================
# Each tuple:
#   (name, slug, description, meta_title,
#    meta_description, sort_order, parent_slug)
#
# parent_slug = None  =>  root category
# ==========================================================

CATEGORY_TREE = [
    # -------------------------------------------------------
    # 1. Electronics
    # -------------------------------------------------------
    ("Electronics", "electronics",
     "Browse the latest gadgets, devices, and electronic accessories.",
     "Electronics | SolidTrack Marketplace",
     "Shop smartphones, laptops, cameras, wearables and more.",
     10, None),
    ("Mobile Phones & Tablets", "electronics-mobile-phones-tablets",
     "Smartphones, feature phones, and tablets from top brands.",
     "Mobile Phones & Tablets", "Browse smartphones, feature phones and tablets.",
     10, "electronics"),
    ("Smartphones", "electronics-mobile-phones-tablets-smartphones",
     "Latest Android and iOS smartphones.",
     "Smartphones", "Shop the latest smartphones at great prices.",
     10, "electronics-mobile-phones-tablets"),
    ("Feature Phones", "electronics-mobile-phones-tablets-feature-phones",
     "Basic phones for calls and messaging.",
     "Feature Phones", "Affordable feature phones for everyday use.",
     20, "electronics-mobile-phones-tablets"),
    ("Tablets", "electronics-mobile-phones-tablets-tablets",
     "Tablets for work, entertainment and education.",
     "Tablets", "Shop tablets for every need and budget.",
     30, "electronics-mobile-phones-tablets"),
    ("Computers", "electronics-computers",
     "Desktops, laptops and computer accessories.",
     "Computers | SolidTrack", "Find laptops, desktops and computer accessories.",
     20, "electronics"),
    ("Laptops", "electronics-computers-laptops",
     "Laptops for work, gaming and everyday use.",
     "Laptops", "Browse laptops from leading manufacturers.",
     10, "electronics-computers"),
    ("Desktops", "electronics-computers-desktops",
     "Desktop computers and all-in-ones.",
     "Desktops", "Shop desktop computers for home and office.",
     20, "electronics-computers"),
    ("Computer Accessories", "electronics-computers-accessories",
     "Keyboards, mice, monitors and more.",
     "Computer Accessories", "Keyboards, mice, monitors, cables and more.",
     30, "electronics-computers"),
    ("Audio & Video", "electronics-audio-video",
     "Speakers, headphones, televisions and home theatre.",
     "Audio & Video | SolidTrack",
     "Shop speakers, headphones, TVs and home theatre systems.",
     30, "electronics"),
    ("Speakers", "electronics-audio-video-speakers",
     "Portable, Bluetooth and home speakers.",
     "Speakers", "Browse speakers for every occasion.",
     10, "electronics-audio-video"),
    ("Headphones & Earbuds", "electronics-audio-video-headphones-earbuds",
     "Wired and wireless headphones and earbuds.",
     "Headphones & Earbuds", "Shop headphones and earbuds from top brands.",
     20, "electronics-audio-video"),
    ("Televisions", "electronics-audio-video-televisions",
     "Smart TVs, LED TVs and OLED TVs.",
     "Televisions", "Find the perfect TV for your living room.",
     30, "electronics-audio-video"),
    ("Cameras & Drones", "electronics-cameras-drones",
     "Digital cameras, action cameras and drones.",
     "Cameras & Drones | SolidTrack",
     "Shop cameras, drones and photography accessories.",
     40, "electronics"),
    ("Digital Cameras", "electronics-cameras-drones-digital-cameras",
     "DSLR, mirrorless and compact cameras.",
     "Digital Cameras", "Browse digital cameras for every skill level.",
     10, "electronics-cameras-drones"),
    ("Drones", "electronics-cameras-drones-drones",
     "Consumer and professional drones.",
     "Drones", "Shop camera drones for photography and recreation.",
     20, "electronics-cameras-drones"),
    ("Camera Accessories", "electronics-cameras-drones-accessories",
     "Lenses, tripods, bags and memory cards.",
     "Camera Accessories", "Lenses, tripods, bags, memory cards and more.",
     30, "electronics-cameras-drones"),
    ("Wearable Technology", "electronics-wearable-technology",
     "Smartwatches, fitness trackers and wearable gadgets.",
     "Wearable Technology | SolidTrack",
     "Shop smartwatches, fitness trackers and more.",
     50, "electronics"),
    ("Smartwatches", "electronics-wearable-technology-smartwatches",
     "Feature-rich smartwatches.",
     "Smartwatches", "Browse smartwatches with health tracking.",
     10, "electronics-wearable-technology"),
    ("Fitness Trackers", "electronics-wearable-technology-fitness-trackers",
     "Track your activity and health metrics.",
     "Fitness Trackers", "Affordable fitness trackers for active lifestyles.",
     20, "electronics-wearable-technology"),
    ("Home Appliances", "electronics-home-appliances",
     "Kitchen and household appliances.",
     "Home Appliances | SolidTrack", "Shop kitchen and household appliances.",
     60, "electronics"),
    ("Kitchen Appliances", "electronics-home-appliances-kitchen",
     "Blenders, microwaves, rice cookers and more.",
     "Kitchen Appliances", "Blenders, microwaves, rice cookers and more.",
     10, "electronics-home-appliances"),
    ("Laundry & Cleaning", "electronics-home-appliances-laundry-cleaning",
     "Washing machines, vacuum cleaners and more.",
     "Laundry & Cleaning", "Washing machines, vacuum cleaners and more.",
     20, "electronics-home-appliances"),

    # -------------------------------------------------------
    # 2. Fashion & Clothing
    # -------------------------------------------------------
    ("Fashion & Clothing", "fashion-clothing",
     "Trendy clothing, shoes and accessories for everyone.",
     "Fashion & Clothing | SolidTrack",
     "Shop men's, women's and kids' fashion at great prices.",
     20, None),
    ("Men's Fashion", "fashion-clothing-mens",
     "Clothing, shoes and accessories for men.",
     "Men's Fashion | SolidTrack", "Explore men's clothing, shoes and accessories.",
     10, "fashion-clothing"),
    ("Men's Clothing", "fashion-clothing-mens-clothing",
     "Shirts, trousers, jackets and more for men.",
     "Men's Clothing", "Browse shirts, trousers, jackets and everyday wear.",
     10, "fashion-clothing-mens"),
    ("Men's Shoes", "fashion-clothing-mens-shoes",
     "Sneakers, loafers, sandals and boots for men.",
     "Men's Shoes", "Shop sneakers, loafers, sandals and boots for men.",
     20, "fashion-clothing-mens"),
    ("Men's Accessories", "fashion-clothing-mens-accessories",
     "Belts, wallets, watches and caps for men.",
     "Men's Accessories", "Belts, wallets, watches, caps and more.",
     30, "fashion-clothing-mens"),
    ("Women's Fashion", "fashion-clothing-womens",
     "Clothing, shoes and accessories for women.",
     "Women's Fashion | SolidTrack", "Explore women's clothing, shoes and accessories.",
     20, "fashion-clothing"),
    ("Women's Clothing", "fashion-clothing-womens-clothing",
     "Dresses, tops, skirts and more for women.",
     "Women's Clothing", "Browse dresses, tops, skirts and everyday wear.",
     10, "fashion-clothing-womens"),
    ("Women's Shoes", "fashion-clothing-womens-shoes",
     "Heels, flats, sneakers and sandals for women.",
     "Women's Shoes", "Shop heels, flats, sneakers and sandals.",
     20, "fashion-clothing-womens"),
    ("Women's Accessories", "fashion-clothing-womens-accessories",
     "Bags, jewellery, scarves and more for women.",
     "Women's Accessories", "Bags, jewellery, scarves, sunglasses and more.",
     30, "fashion-clothing-womens"),
    ("Kids & Baby Clothing", "fashion-clothing-kids-baby",
     "Clothing for boys, girls and babies.",
     "Kids & Baby Clothing | SolidTrack",
     "Shop clothing for boys, girls and babies.",
     30, "fashion-clothing"),
    ("Boys' Clothing", "fashion-clothing-kids-baby-boys",
     "T-shirts, shorts, trousers and sets for boys.",
     "Boys' Clothing", "Browse t-shirts, shorts, trousers and sets for boys.",
     10, "fashion-clothing-kids-baby"),
    ("Girls' Clothing", "fashion-clothing-kids-baby-girls",
     "Dresses, tops, skirts and sets for girls.",
     "Girls' Clothing", "Browse dresses, tops, skirts and sets for girls.",
     20, "fashion-clothing-kids-baby"),
    ("Baby Clothing", "fashion-clothing-kids-baby-baby",
     "Onesies, rompers and outfits for babies.",
     "Baby Clothing", "Soft onesies, rompers and outfits for babies.",
     30, "fashion-clothing-kids-baby"),

    # -------------------------------------------------------
    # 3. Home & Garden
    # -------------------------------------------------------
    ("Home & Garden", "home-garden",
     "Furniture, decor, kitchen essentials and garden supplies.",
     "Home & Garden | SolidTrack",
     "Shop furniture, decor, kitchen essentials and garden supplies.",
     30, None),
    ("Furniture", "home-garden-furniture",
     "Sofas, beds, tables and office furniture.",
     "Furniture | SolidTrack", "Shop sofas, beds, tables and office furniture.",
     10, "home-garden"),
    ("Living Room", "home-garden-furniture-living-room",
     "Sofas, TV stands and coffee tables.",
     "Living Room Furniture", "Sofas, TV stands, coffee tables and more.",
     10, "home-garden-furniture"),
    ("Bedroom", "home-garden-furniture-bedroom",
     "Beds, wardrobes and nightstands.",
     "Bedroom Furniture", "Beds, wardrobes, nightstands and bedroom storage.",
     20, "home-garden-furniture"),
    ("Office", "home-garden-furniture-office",
     "Desks, chairs and bookshelves.",
     "Office Furniture", "Desks, office chairs, bookshelves and storage.",
     30, "home-garden-furniture"),
    ("Home Decor", "home-garden-decor",
     "Wall art, lighting, rugs and decorative items.",
     "Home Decor | SolidTrack",
     "Shop wall art, lighting, rugs and decorative items.",
     20, "home-garden"),
    ("Wall Art", "home-garden-decor-wall-art",
     "Paintings, posters, frames and wall hangings.",
     "Wall Art", "Paintings, posters, frames and wall hangings.",
     10, "home-garden-decor"),
    ("Lighting", "home-garden-decor-lighting",
     "Ceiling lights, table lamps and floor lamps.",
     "Lighting", "Ceiling lights, table lamps, floor lamps and more.",
     20, "home-garden-decor"),
    ("Rugs & Carpets", "home-garden-decor-rugs-carpets",
     "Area rugs, runners and carpets.",
     "Rugs & Carpets", "Area rugs, runners and carpets for every room.",
     30, "home-garden-decor"),
    ("Kitchen & Dining", "home-garden-kitchen-dining",
     "Cookware, tableware and storage solutions.",
     "Kitchen & Dining | SolidTrack",
     "Shop cookware, tableware and kitchen storage solutions.",
     30, "home-garden"),
    ("Cookware", "home-garden-kitchen-dining-cookware",
     "Pots, pans, baking trays and utensils.",
     "Cookware", "Pots, pans, baking trays, utensils and more.",
     10, "home-garden-kitchen-dining"),
    ("Tableware", "home-garden-kitchen-dining-tableware",
     "Plates, bowls, glasses and cutlery.",
     "Tableware", "Plates, bowls, glasses, cutlery and serving ware.",
     20, "home-garden-kitchen-dining"),
    ("Storage & Organization", "home-garden-kitchen-dining-storage",
     "Containers, racks and pantry organizers.",
     "Kitchen Storage", "Containers, racks, pantry organizers and more.",
     30, "home-garden-kitchen-dining"),
    ("Garden & Outdoor", "home-garden-outdoor",
     "Garden tools, outdoor furniture and planters.",
     "Garden & Outdoor | SolidTrack",
     "Shop garden tools, outdoor furniture and planters.",
     40, "home-garden"),
    ("Garden Tools", "home-garden-outdoor-tools",
     "Shovels, rakes, pruners and watering cans.",
     "Garden Tools", "Shovels, rakes, pruners, watering cans and more.",
     10, "home-garden-outdoor"),
    ("Outdoor Furniture", "home-garden-outdoor-furniture",
     "Patios, benches and garden tables.",
     "Outdoor Furniture", "Patio sets, benches, garden tables and chairs.",
     20, "home-garden-outdoor"),
    ("Planters & Pots", "home-garden-outdoor-planters-pots",
     "Flower pots, planters and raised beds.",
     "Planters & Pots", "Flower pots, planters and raised beds.",
     30, "home-garden-outdoor"),

    # -------------------------------------------------------
    # 4. Health & Beauty
    # -------------------------------------------------------
    ("Health & Beauty", "health-beauty",
     "Skincare, haircare, fragrances and wellness products.",
     "Health & Beauty | SolidTrack",
     "Shop skincare, haircare, fragrances and wellness products.",
     40, None),
    ("Personal Care", "health-beauty-personal-care",
     "Skincare, haircare and oral care products.",
     "Personal Care | SolidTrack",
     "Browse skincare, haircare and oral care essentials.",
     10, "health-beauty"),
    ("Skincare", "health-beauty-personal-care-skincare",
     "Moisturizers, cleansers, serums and sunscreens.",
     "Skincare", "Moisturizers, cleansers, serums, sunscreens and more.",
     10, "health-beauty-personal-care"),
    ("Haircare", "health-beauty-personal-care-haircare",
     "Shampoos, conditioners, oils and styling products.",
     "Haircare", "Shampoos, conditioners, oils and styling products.",
     20, "health-beauty-personal-care"),
    ("Oral Care", "health-beauty-personal-care-oral-care",
     "Toothbrushes, toothpaste and mouthwash.",
     "Oral Care", "Toothbrushes, toothpaste, mouthwash and dental floss.",
     30, "health-beauty-personal-care"),
    ("Fragrances", "health-beauty-fragrances",
     "Perfumes, colognes and body mists.",
     "Fragrances | SolidTrack",
     "Shop perfumes, colognes and body mists.",
     20, "health-beauty"),
    ("Health & Wellness", "health-beauty-wellness",
     "Vitamins, supplements and fitness accessories.",
     "Health & Wellness | SolidTrack",
     "Browse vitamins, supplements and fitness accessories.",
     30, "health-beauty"),
    ("Vitamins & Supplements", "health-beauty-wellness-vitamins",
     "Multivitamins, protein powders and herbal supplements.",
     "Vitamins & Supplements",
     "Multivitamins, protein powders, herbal supplements.",
     10, "health-beauty-wellness"),
    ("Fitness Accessories", "health-beauty-wellness-fitness-accessories",
     "Resistance bands, water bottles and gym bags.",
     "Fitness Accessories",
     "Resistance bands, water bottles, gym bags and more.",
     20, "health-beauty-wellness"),

    # -------------------------------------------------------
    # 5. Sports & Outdoors
    # -------------------------------------------------------
    ("Sports & Outdoors", "sports-outdoors",
     "Exercise equipment, outdoor gear and team sports gear.",
     "Sports & Outdoors | SolidTrack",
     "Shop exercise equipment, outdoor gear and team sports gear.",
     50, None),
    ("Exercise & Fitness", "sports-outdoors-exercise-fitness",
     "Gym equipment, yoga gear and running essentials.",
     "Exercise & Fitness | SolidTrack",
     "Browse gym equipment, yoga gear and running essentials.",
     10, "sports-outdoors"),
    ("Gym Equipment", "sports-outdoors-exercise-fitness-gym",
     "Dumbbells, treadmills and benches.",
     "Gym Equipment", "Dumbbells, treadmills, benches and more.",
     10, "sports-outdoors-exercise-fitness"),
    ("Yoga & Pilates", "sports-outdoors-exercise-fitness-yoga",
     "Yoga mats, blocks, straps and pilates rings.",
     "Yoga & Pilates", "Yoga mats, blocks, straps and pilates rings.",
     20, "sports-outdoors-exercise-fitness"),
    ("Running", "sports-outdoors-exercise-fitness-running",
     "Running shoes, apparel and accessories.",
     "Running", "Running shoes, apparel, watches and accessories.",
     30, "sports-outdoors-exercise-fitness"),
    ("Outdoor Recreation", "sports-outdoors-outdoor-recreation",
     "Camping, hiking, cycling and water sports gear.",
     "Outdoor Recreation | SolidTrack",
     "Shop camping, hiking, cycling and water sports gear.",
     20, "sports-outdoors"),
    ("Camping & Hiking", "sports-outdoors-outdoor-recreation-camping",
     "Tents, sleeping bags, backpacks and hiking boots.",
     "Camping & Hiking",
     "Tents, sleeping bags, backpacks, hiking boots and more.",
     10, "sports-outdoors-outdoor-recreation"),
    ("Cycling", "sports-outdoors-outdoor-recreation-cycling",
     "Bicycles, helmets and cycling accessories.",
     "Cycling", "Bicycles, helmets, lights and cycling accessories.",
     20, "sports-outdoors-outdoor-recreation"),
    ("Water Sports", "sports-outdoors-outdoor-recreation-water",
     "Swimming gear, surfboards and kayaks.",
     "Water Sports", "Swimming gear, surfboards, kayaks and more.",
     30, "sports-outdoors-outdoor-recreation"),
    ("Team Sports", "sports-outdoors-team-sports",
     "Football, basketball, tennis and other team sports gear.",
     "Team Sports | SolidTrack",
     "Shop football, basketball, tennis and team sports gear.",
     30, "sports-outdoors"),
    ("Football", "sports-outdoors-team-sports-football",
     "Footballs, boots, kits and goals.",
     "Football", "Footballs, boots, kits, goals and accessories.",
     10, "sports-outdoors-team-sports"),
    ("Basketball", "sports-outdoors-team-sports-basketball",
     "Basketballs, hoops, shoes and jerseys.",
     "Basketball", "Basketballs, hoops, shoes and jerseys.",
     20, "sports-outdoors-team-sports"),
    ("Tennis", "sports-outdoors-team-sports-tennis",
     "Rackets, balls, shoes and nets.",
     "Tennis", "Rackets, balls, shoes, nets and tennis accessories.",
     30, "sports-outdoors-team-sports"),

    # -------------------------------------------------------
    # 6. Toys & Games
    # -------------------------------------------------------
    ("Toys & Games", "toys-games",
     "Action figures, board games, puzzles and educational toys.",
     "Toys & Games | SolidTrack",
     "Shop action figures, board games, puzzles and educational toys.",
     60, None),
    ("Action Figures & Collectibles", "toys-games-action-figures",
     "Action figures, model kits and collectible figurines.",
     "Action Figures & Collectibles",
     "Action figures, model kits and collectible figurines.",
     10, "toys-games"),
    ("Board Games & Puzzles", "toys-games-board-games-puzzles",
     "Family board games, card games and jigsaw puzzles.",
     "Board Games & Puzzles",
     "Family board games, card games and jigsaw puzzles.",
     20, "toys-games"),
    ("Educational Toys", "toys-games-educational",
     "STEM kits, building blocks and learning toys.",
     "Educational Toys",
     "STEM kits, building blocks, science sets and more.",
     30, "toys-games"),
    ("Outdoor Play", "toys-games-outdoor-play",
     "Bicycles, scooters, swings and trampolines.",
     "Outdoor Play Toys",
     "Bicycles, scooters, swings, trampolines and more.",
     40, "toys-games"),

    # -------------------------------------------------------
    # 7. Books, Movies & Music
    # -------------------------------------------------------
    ("Books, Movies & Music", "books-movies-music",
     "Books, movies, TV shows and music across all genres.",
     "Books, Movies & Music | SolidTrack",
     "Browse books, movies, TV shows and music.",
     70, None),
    ("Books", "books-movies-music-books",
     "Fiction, non-fiction and children's books.",
     "Books | SolidTrack",
     "Browse fiction, non-fiction and children's books.",
     10, "books-movies-music"),
    ("Fiction", "books-movies-music-books-fiction",
     "Novels, short stories and literary fiction.",
     "Fiction Books",
     "Novels, short stories, fantasy, romance and more.",
     10, "books-movies-music-books"),
    ("Non-Fiction", "books-movies-music-books-non-fiction",
     "Biographies, self-help, business and more.",
     "Non-Fiction Books",
     "Biographies, self-help, business, science and more.",
     20, "books-movies-music-books"),
    ("Children's Books", "books-movies-music-books-children",
     "Picture books, early readers and young adult fiction.",
     "Children's Books",
     "Picture books, early readers and young adult fiction.",
     30, "books-movies-music-books"),
    ("Movies & TV", "books-movies-music-movies-tv",
     "DVDs, Blu-rays and digital movie codes.",
     "Movies & TV | SolidTrack", "Shop DVDs, Blu-rays and digital codes.",
     20, "books-movies-music"),
    ("Music", "books-movies-music-music",
     "Vinyl records, CDs and music accessories.",
     "Music | SolidTrack", "Vinyl records, CDs and music accessories.",
     30, "books-movies-music"),

    # -------------------------------------------------------
    # 8. Food & Grocery
    # -------------------------------------------------------
    ("Food & Grocery", "food-grocery",
     "Beverages, snacks, fresh produce and pantry staples.",
     "Food & Grocery | SolidTrack",
     "Shop beverages, snacks, fresh produce and pantry staples.",
     80, None),
    ("Beverages", "food-grocery-beverages",
     "Water, juices, soft drinks and energy drinks.",
     "Beverages", "Water, juices, soft drinks and energy drinks.",
     10, "food-grocery"),
    ("Snacks & Confectionery", "food-grocery-snacks",
     "Chips, chocolates, biscuits and sweets.",
     "Snacks", "Chips, chocolates, biscuits and sweets.",
     20, "food-grocery"),
    ("Fresh Produce", "food-grocery-fresh-produce",
     "Fruits, vegetables and fresh herbs.",
     "Fresh Produce", "Fresh fruits, vegetables and herbs.",
     30, "food-grocery"),
    ("Pantry Staples", "food-grocery-pantry",
     "Rice, pasta, cooking oils and canned goods.",
     "Pantry Staples", "Rice, pasta, cooking oils and canned goods.",
     40, "food-grocery"),

    # -------------------------------------------------------
    # 9. Automotive
    # -------------------------------------------------------
    ("Automotive", "automotive",
     "Car parts, accessories, electronics and tyres.",
     "Automotive", "Car parts, accessories, electronics and tyres.",
     90, None),
    ("Car Parts", "automotive-parts-accessories",
     "Engine parts, brake pads, batteries and filters.",
     "Car Parts", "Engine parts, brake pads, batteries and filters.",
     10, "automotive"),
    ("Car Electronics", "automotive-electronics",
     "Dash cameras, GPS navigators and car audio.",
     "Car Electronics", "Dash cameras, GPS navigators and car audio.",
     20, "automotive"),
    ("Tires & Wheels", "automotive-tires-wheels",
     "Tyres, rims and wheel accessories.",
     "Tires & Wheels", "Tyres, rims and wheel accessories.",
     30, "automotive"),

    # -------------------------------------------------------
    # 10. Baby & Kids
    # -------------------------------------------------------
    ("Baby & Kids", "baby-kids",
     "Baby essentials, kids furniture and travel gear.",
     "Baby & Kids", "Baby essentials, kids furniture and travel gear.",
     100, None),
    ("Baby Essentials", "baby-kids-essentials",
     "Diapers, wipes, feeding bottles and baby care.",
     "Baby Essentials", "Diapers, wipes, feeding bottles and baby care.",
     10, "baby-kids"),
    ("Diapers & Wipes", "baby-kids-essentials-diapers-wipes",
     "Diapers, baby wipes and changing mats.",
     "Diapers & Wipes", "Diapers, baby wipes and changing mats.",
     10, "baby-kids-essentials"),
    ("Feeding", "baby-kids-essentials-feeding",
     "Bottles, breast pumps, high chairs and bibs.",
     "Feeding", "Bottles, breast pumps, high chairs and bibs.",
     20, "baby-kids-essentials"),
    ("Kids Furniture", "baby-kids-furniture",
     "Cribs, changing tables and kids desks.",
     "Kids Furniture", "Cribs, changing tables and kids desks.",
     20, "baby-kids"),
    ("Strollers", "baby-kids-strollers-car-seats",
     "Strollers, car seats and travel accessories.",
     "Strollers", "Strollers, car seats and travel accessories.",
     30, "baby-kids"),

    # -------------------------------------------------------
    # 11. Pet Supplies
    # -------------------------------------------------------
    ("Pet Supplies", "pet-supplies",
     "Food, toys, grooming and accessories for pets.",
     "Pet Supplies", "Food, toys, grooming and accessories for pets.",
     110, None),
    ("Dog Supplies", "pet-supplies-dogs",
     "Food, beds, leashes and toys for dogs.",
     "Dog Supplies", "Food, beds, leashes and toys for dogs.",
     10, "pet-supplies"),
    ("Cat Supplies", "pet-supplies-cats",
     "Food, litter, scratching posts and toys for cats.",
     "Cat Supplies", "Food, litter, scratching posts and toys for cats.",
     20, "pet-supplies"),
    ("Other Pets", "pet-supplies-other",
     "Food and accessories for birds, fish and small animals.",
     "Other Pets", "Food and accessories for birds, fish and small animals.",
     30, "pet-supplies"),
]


class Command(BaseCommand):
    help = "Seed the full e-commerce product category hierarchy."

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0
        total = len(CATEGORY_TREE)

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("Seeding product categories")
        )
        self.stdout.write(f"  Processing {total} categories ...")
        self.stdout.write("")

        # --------------------------------------------------
        # First pass - create root categories so parent
        # look-ups succeed during the second pass.
        # --------------------------------------------------

        lookup = {}  # slug -> ProductCategory instance

        for (
            name, slug, description, meta_title,
            meta_description, sort_order, parent_slug,
        ) in CATEGORY_TREE:

            if parent_slug is not None:
                continue

            obj, created = ProductCategory.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "meta_title": meta_title,
                    "meta_description": meta_description,
                    "sort_order": sort_order,
                    "is_active": True,
                    "parent": None,
                },
            )

            lookup[slug] = obj

            if created:
                created_count += 1
                self.stdout.write(f"  + Root: {name}")
            else:
                updated_count += 1
                self.stdout.write(f"  ~ Root (updated): {name}")

        # --------------------------------------------------
        # Second pass - child / grandchild categories.
        # --------------------------------------------------

        for (
            name, slug, description, meta_title,
            meta_description, sort_order, parent_slug,
        ) in CATEGORY_TREE:

            if parent_slug is None:
                continue

            parent_obj = lookup.get(parent_slug)

            if parent_obj is None:
                parent_obj = ProductCategory.objects.get(
                    slug=parent_slug,
                )

            obj, created = ProductCategory.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "meta_title": meta_title,
                    "meta_description": meta_description,
                    "sort_order": sort_order,
                    "is_active": True,
                    "parent": parent_obj,
                },
            )

            lookup[slug] = obj

            if created:
                created_count += 1
                self.stdout.write(
                    f"  + Child: {parent_obj.name} > {name}"
                )
            else:
                updated_count += 1
                self.stdout.write(
                    f"  ~ Child (updated): {parent_obj.name} > {name}"
                )

        # --------------------------------------------------
        # Summary
        # --------------------------------------------------

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done - {created_count} created, "
            f"{updated_count} updated, "
            f"{total} total."
        ))
        self.stdout.write("")

        # ======================================================
        # Seed Category Options
        # ======================================================

        self._seed_category_options()

    # ==========================================================
    # Category Options Seeding
    # ==========================================================

    def _seed_category_options(self):
        """
        Seed category options from CATEGORY_OPTIONS data.
        """

        options_created = 0
        options_updated = 0

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING("Seeding category options")
        )

        for (
            category_slug,
            options_list,
        ) in CATEGORY_OPTIONS.items():

            # Get the category
            try:
                category = ProductCategory.objects.get(
                    slug=category_slug,
                )
            except ProductCategory.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ! Category not found: {category_slug}"
                    )
                )
                continue

            for option_name, sort_order in options_list:

                option_slug = slugify(option_name)

                obj, created = (
                    CategoryOption.objects.update_or_create(
                        category=category,
                        name=option_name,
                        defaults={
                            "slug": option_slug,
                            "sort_order": sort_order,
                            "is_active": True,
                        },
                    )
                )

                if created:
                    options_created += 1
                else:
                    options_updated += 1

        total = options_created + options_updated
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done - {options_created} created, "
            f"{options_updated} updated, "
            f"{total} total."
        ))
        self.stdout.write("")
