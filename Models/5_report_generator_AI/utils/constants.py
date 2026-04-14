# ── Vector Store Collection Names ─────────────────────────────────
SURVEY_COLLECTION = "survey_collection"
BACKEND_COLLECTION = "backend_collection"

# ── Default Retrieval Parameters ──────────────────────────────────
DEFAULT_TOP_K = 20          # Documents to retrieve per collection
RERANKER_TOP_K = 10         # Documents after reranking
MMR_FETCH_K = 60            # Candidates for MMR diversity sampling
MMR_LAMBDA = 0.7            # MMR diversity (0=max diverse, 1=max relevant)

# ── User-Facing Categories ────────────────────────────────────────
# These are the categories exposed to the API consumer.
# Each maps to relevant categories in both datasets.

CATEGORY_MAP = {
    # ── Infrastructure & Roads ────────────────────────────────────
    "Infrastructure": {
        "survey_categories": [
            "damaged_roads", "potholes", "broken_footpath",
            "collapsed_bridge", "damaged_flyover", "bus_stop_infra",
            "boundary_wall_damage", "damaged_boundary_wall",
            "cracked_building_wall", "signboard_damage",
        ],
        "backend_categories": ["Infrastructure"],
        "keywords": [
            "road", "pothole", "bridge", "footpath", "flyover",
            "construction", "building", "infrastructure", "repair",
        ],
    },

    # ── Water Supply & Sanitation ─────────────────────────────────
    "Water Supply & Sanitation": {
        "survey_categories": [
            "water_shortage", "water_supply_interruptions",
            "contaminated_water", "water_supply_and_sanitation",
            "Water & Sewerage Budget", "Wastewater Treatment",
            "sewage_overflow", "blocked_drain", "waterlogging",
            "flooding",
        ],
        "backend_categories": ["Water Supply & Sanitation"],
        "keywords": [
            "water", "sanitation", "sewage", "drain", "flood",
            "waterlogging", "pipeline", "contaminated", "supply",
        ],
    },

    # ── Health ────────────────────────────────────────────────────
    "Health": {
        "survey_categories": [
            "health", "mosquito_breeding",
        ],
        "backend_categories": ["Health"],
        "keywords": [
            "health", "hospital", "disease", "medical", "mosquito",
            "dengue", "malaria", "clinic", "sanitation",
        ],
    },

    # ── Education ─────────────────────────────────────────────────
    "Education": {
        "survey_categories": ["education"],
        "backend_categories": ["Education"],
        "keywords": [
            "education", "school", "college", "teacher", "student",
            "literacy", "classroom", "enrollment",
        ],
    },

    # ── Environment ───────────────────────────────────────────────
    "Environment": {
        "survey_categories": [
            "environment", "air_pollution", "noise_pollution",
            "tree_fall", "tree_fall_hazard",
            "solid_waste_mismanagement", "solid_waste_uncollected",
        ],
        "backend_categories": ["Environment"],
        "keywords": [
            "environment", "pollution", "air", "noise", "waste",
            "garbage", "tree", "green", "climate", "emission",
        ],
    },

    # ── Electricity & Power ───────────────────────────────────────
    "Electricity & Power": {
        "survey_categories": [
            "electricity_and_power", "power_outage",
            "street_light_failure", "streetlight_outage",
            "broken_traffic_light",
        ],
        "backend_categories": ["Electricity & Power"],
        "keywords": [
            "electricity", "power", "streetlight", "outage",
            "transformer", "voltage", "light", "electric",
        ],
    },

    # ── Municipal Services ────────────────────────────────────────
    "Municipal Services": {
        "survey_categories": [
            "municipal_services", "open_manhole", "opened_manhole",
            "park_maintenance", "Community Toilets",
            "Toilet Complaints", "public_toilet_hygiene",
            "public_toilet_shortage", "encroachment",
        ],
        "backend_categories": ["Municipal Services"],
        "keywords": [
            "municipal", "manhole", "park", "toilet", "civic",
            "garbage", "cleaning", "sweeping", "encroachment",
        ],
    },

    # ── Transportation ────────────────────────────────────────────
    "Transportation": {
        "survey_categories": [
            "transportation", "transport_safety",
            "bus_stop_issues", "illegal_parking",
        ],
        "backend_categories": ["Transportation"],
        "keywords": [
            "transport", "bus", "traffic", "road", "vehicle",
            "parking", "metro", "railway", "commute",
        ],
    },

    # ── Police Services ───────────────────────────────────────────
    "Police Services": {
        "survey_categories": [
            "police_services", "stray_animals", "stray_dogs",
        ],
        "backend_categories": ["Police Services"],
        "keywords": [
            "police", "crime", "safety", "security", "stray",
            "dog", "animal", "theft", "law",
        ],
    },

    # ── Housing & Urban Development ───────────────────────────────
    "Housing & Urban Development": {
        "survey_categories": ["housing_and_urban_development"],
        "backend_categories": ["Housing & Urban Development"],
        "keywords": [
            "housing", "urban", "development", "slum",
            "construction", "building", "apartment", "colony",
        ],
    },

    # ── Social Welfare ────────────────────────────────────────────
    "Social Welfare": {
        "survey_categories": [
            "social_welfare", "women_and_child_development",
        ],
        "backend_categories": ["Social Welfare"],
        "keywords": [
            "social", "welfare", "women", "child", "pension",
            "disability", "ration", "scheme", "benefit",
        ],
    },

    # ── Public Grievances ─────────────────────────────────────────
    "Public Grievances": {
        "survey_categories": ["public_grievances"],
        "backend_categories": ["Public Grievances"],
        "keywords": [
            "grievance", "complaint", "public", "citizen",
            "redressal", "corruption", "service",
        ],
    },

    # ── Revenue ───────────────────────────────────────────────────
    "Revenue": {
        "survey_categories": ["revenue"],
        "backend_categories": ["Revenue"],
        "keywords": [
            "revenue", "tax", "property", "land", "registration",
            "mutation", "assessment",
        ],
    },

    # ── Agriculture ───────────────────────────────────────────────
    "Agriculture": {
        "survey_categories": [
            "agriculture", "rural_development",
        ],
        "backend_categories": [],  # Not in SwarajDesk dataset
        "keywords": [
            "agriculture", "farming", "crop", "irrigation",
            "rural", "farmer", "harvest", "soil",
        ],
    },

    # ── Fire & Emergency ──────────────────────────────────────────
    "Fire & Emergency": {
        "survey_categories": ["fire_and_emergency"],
        "backend_categories": [],
        "keywords": [
            "fire", "emergency", "rescue", "disaster",
            "ambulance", "hazard",
        ],
    },

    # ── Sports & Youth ────────────────────────────────────────────
    "Sports & Youth Affairs": {
        "survey_categories": ["sports_and_youth_affairs"],
        "backend_categories": [],
        "keywords": [
            "sports", "youth", "playground", "stadium",
            "athletics", "recreation",
        ],
    },

    # ── Tourism & Culture ─────────────────────────────────────────
    "Tourism & Culture": {
        "survey_categories": ["tourism_and_culture"],
        "backend_categories": [],
        "keywords": [
            "tourism", "culture", "heritage", "monument",
            "museum", "festival",
        ],
    },
}

# ── Flat list of valid user-facing categories ─────────────────────
VALID_CATEGORIES = list(CATEGORY_MAP.keys())


def get_all_keywords() -> dict[str, list[str]]:
    """Return category -> keywords mapping for fuzzy matching."""
    return {cat: info["keywords"] for cat, info in CATEGORY_MAP.items()}
