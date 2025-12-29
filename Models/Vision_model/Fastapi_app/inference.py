import os
import base64
import json
from io import BytesIO

import torch
from transformers import ViTForImageClassification
from groq import Groq

from .utils import load_image, get_top_class

# ========= CORE CONFIG =========

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY environment variable is not set")

groq_client = Groq(api_key=GROQ_API_KEY)


def normalize_key(text: str | None) -> str | None:
    if text is None:
        return None
    return text.strip().lower().replace(" ", "_")


def key_to_display(key: str | None) -> str | None:
    if key is None:
        return None
    return " ".join([w.capitalize() for w in key.split("_")])


# ========= SECTORS + PROBLEMS (20 SECTORS) =========

SECTOR_CATEGORIES: dict[str, list[str]] = {
    "infrastructure": [
        "potholes",
        "collapsed_bridge",
        "broken_traffic_light",
        "damaged_roads",
        "cracked_building_wall",
        "blocked_drain",
        "broken_footpath",
        "damaged_flyover",
        "opened_manhole",
        "damaged_boundary_wall",
    ],
    "education": [
        "broken_blackboard",
        "broken_classroom_bench",
        "dirty_drinking_water",
        "broken_school_gate",
        "broken_classroom_ceiling",
        "broken_window_glass",
        "damaged_hostel_bed",
        "unhygienic_school_toilet",
        "broken_projector_screen",
        "playground_equipment_broken",
    ],
    "environment": [
        "plastic_waste_accumulation",
        "water_pollution",
        "air_pollution",
        "chemical_dumping",
        "garbage_overflow",
        "tree_cutting",
        "dead_animals_on_road",
        "waterlogging",
        "open_sewage",
        "construction_debris_dumping",
    ],
    "health": [
        "dirty_hospital_bed",
        "broken_hospital_stretcher",
        "overflowing_medical_waste",
        "unhygienic_hospital_toilet",
        "broken_hospital_window",
        "broken_air_conditioner_in_ward",
        "crowded_outpatient_area",
        "faulty_medical_equipment",
        "dirty_hospital_kitchen",
        "damaged_hospital_ceiling",
    ],
    "water_supply_and_sanitation": [
        "broken_water_pipeline",
        "contaminated_drinking_water",
        "no_water_supply",
        "leaking_water_tap",
        "dirty_water_storage_tank",
        "waterlogging_near_pipeline",
        "broken_hand_pump",
        "dry_water_tank",
        "damaged_public_water_cooler",
        "broken_sanitation_pipe",
    ],
    "electricity_and_power": [
        "broken_streetlight",
        "fallen_electric_pole",
        "exposed_live_wires",
        "transformer_leakage",
        "sparking_electric_panel",
        "broken_power_meter",
        "power_cable_hanging",
        "broken_electric_switchboard",
        "damaged_solar_panel",
        "power_substation_damage",
    ],
    "transportation": [
        "damaged_bus_stop_shelter",
        "broken_railway_crossing",
        "damaged_road_signage",
        "broken_speed_breaker",
        "damaged_foot_over_bridge",
        "broken_toll_gate",
        "damaged_parking_area",
        "bus_overcrowded",
        "broken_railway_platform_floor",
        "damaged_public_bicycle_stand",
    ],
    "municipal_services": [
        "overflowing_public_dustbin",
        "stray_animals_issue",
        "public_urination_spots",
        "blocked_public_toilet",
        "damaged_municipal_parks",
        "open_dumping_site",
        "street_dog_attack_issue",
        "unattended_dead_animals",
        "street_vendor_encroachment",
        "improper_public_cleaning",
    ],
    "police_services": [
        "broken_police_booth",
        "damaged_surveillance_camera",
        "broken_traffic_barricade",
        "damaged_traffic_signal_post",
        "damaged_police_vehicle",
        "broken_police_station_furniture",
        "missing_police_patrolling",
        "overcrowded_police_station",
        "broken_weapon_storage_locker",
        "damaged_lockup_cells",
    ],
    "revenue": [
        "damaged_property_tax_center_building",
        "broken_payment_kiosk",
        "damaged_revenue_office_board",
        "misplaced_notice_board",
        "broken_public_workstation",
        "non_functional_token_system",
        "damaged_public_sitting_area",
        "broken_grievance_box",
        "broken_queue_barrier",
        "torn_public_notice_banner",
    ],
    "housing_and_urban_development": [
        "illegal_construction",
        "broken_sewage_line_in_residential_area",
        "collapsed_house_ceiling",
        "damaged_residential_wall",
        "broken_water_tank_on_building",
        "damaged_parking_shed",
        "building_construction_debris_dumped",
        "encroachment_on_footpath",
        "broken_building_entrance_door",
        "improper_residential_wiring_exposed",
    ],
    "social_welfare": [
        "broken_old_age_home_bed",
        "dirty_orphanage_kitchen",
        "damaged_shelter_home_toilet",
        "broken_child_care_center_toys",
        "broken_wheelchair",
        "damaged_public_disability_ramp",
        "unhygienic_soup_kitchen",
        "broken_blind_school_braille_board",
        "damaged_public_shelter_floor",
        "broken_old_age_home_furniture",
    ],
    "public_grievances": [
        "damaged_public_notice_board",
        "broken_suggestion_box",
        "damaged_citizen_service_center_chair",
        "broken_public_help_counter",
        "torn_feedback_posters",
        "broken_queue_token_display",
        "broken_public_signage",
        "damaged_complaint_cell_infrastructure",
        "dirty_public_feedback_room",
        "damaged_public_information_kiosk",
    ],
    "tourism_and_culture": [
        "broken_heritage_monument_area",
        "dirty_tourist_spot",
        "broken_public_viewing_gallery",
        "damaged_statue",
        "damaged_historical_wall",
        "broken_tourist_rest_hut",
        "broken_ticket_counter_booth",
        "damaged_cultural_stage",
        "broken_water_fountain",
        "improper_direction_boards",
    ],
    "agriculture": [
        "broken_irrigation_canal",
        "pesticide_waste_dumping",
        "damaged_greenhouse",
        "crop_burning_air_pollution",
        "damaged_agri_borewell",
        "broken_farm_fence",
        "damaged_crop_storage_warehouse",
        "damaged_agricultural_cold_storage",
        "broken_solar_farm_panels",
        "livestock_shelter_damage",
    ],
    "rural_development": [
        "damaged_gram_panchayat_building",
        "broken_panchayat_road",
        "broken_chowk_streetlight",
        "damaged_ration_shop",
        "damaged_panchayat_notice_board",
        "dirty_village_pond",
        "broken_public_borewell",
        "broken_common_water_pot_area",
        "broken_village_bus_shelter",
        "garbage_near_temple_area",
    ],
    "women_and_child_development": [
        "broken_angawadi_center",
        "broken_creche_furniture",
        "broken_lactation_room_facilities",
        "unhygienic_child_care_food_area",
        "broken_child_protection_home_gate",
        "damaged_menstrual_hygiene_disposal_bin",
        "broken_mother_and_child_room_bed",
        "broken_child_playground_area",
        "dirty_maternity_care_unit",
        "broken_breastfeeding_room_chair",
    ],
    "sports_and_youth_affairs": [
        "broken_stadium_seating",
        "damaged_badminton_net",
        "damaged_turf_ground",
        "broken_gym_equipment",
        "damaged_scoreboard",
        "broken_swimming_pool_diving_board",
        "broken_basketball_hoop",
        "damaged_cricket_practice_net",
        "broken_skate_ramp",
        "broken_public_sports_store_room",
    ],
    "fire_and_emergency": [
        "broken_fire_hydrant",
        "damaged_fire_alarm",
        "blocked_fire_exit_route",
        "damaged_fire_extinguisher",
        "broken_emergency_siren",
        "broken_fire_station_gate",
        "broken_rescue_stretcher",
        "broken_emergency_influence_glass",
        "blocked_fire_truck_path",
        "damaged_fire_hose_coil",
    ],
    "transport_safety": [
        "broken_guard_rail",
        "damaged_speed_bump",
        "broken_pedestrian_crossing_signal",
        "damaged_road_reflector",
        "broken_crash_barrier",
        "broken_median_fence",
        "broken_foot_overbridge_handrail",
        "broken_street_signage",
        "damaged_highway_pollution_barrier",
        "broken_railway_warning_gate",
    ],
}

ALL_SECTORS = set(SECTOR_CATEGORIES.keys())
VIT_SUPPORTED_SECTORS = {"infrastructure", "education", "environment"}


# ========= VIT MODELS (GUARD FOR 3 SECTORS) =========

def load_vit_model(model_path, id2label):
    model = ViTForImageClassification.from_pretrained(
        "google/vit-base-patch16-224-in21k",
        num_labels=len(id2label),
        id2label=id2label,
        label2id={v: k for k, v in id2label.items()},
    )
    state_dict = torch.load(model_path, map_location=device)
    model.load_state_dict(state_dict)
    model.to(device)
    model.eval()
    return model


sector_id2label = {0: "infrastructure", 1: "education", 2: "environment", 3: "invalid"}
sector_model = load_vit_model(os.path.join(MODEL_DIR, "sector_model.pt"), sector_id2label)

infra_id2label = {0: "collapsed_bridge", 1: "fallen_electric_pole", 2: "potholes", 3: "invalid"}
infra_model = load_vit_model(os.path.join(MODEL_DIR, "infra_model.pt"), infra_id2label)

edu_id2label = {
    0: "broken_blackboard",
    1: "broken_classroom_bench",
    2: "dirty_drinking_water",
    3: "invalid",
}
education_model = load_vit_model(os.path.join(MODEL_DIR, "education_model.pt"), edu_id2label)

env_id2label = {
    0: "air_pollution",
    1: "water_pollution",
    2: "plastic_waste_accumulation",
    3: "invalid",
}
environment_model = load_vit_model(os.path.join(MODEL_DIR, "environment_model.pt"), env_id2label)


def vit_predict(image_bytes: bytes) -> dict:
    """Run ViT sector + subclass models (only for the 3 supported sectors)."""
    tensor = load_image(BytesIO(image_bytes)).to(device)

    sector_logits = sector_model(tensor).logits
    sector_idx, sector_conf = get_top_class(sector_logits)
    sector = sector_id2label[sector_idx]

    category = None
    cat_conf = None

    if sector == "infrastructure":
        logits = infra_model(tensor).logits
        idx, conf = get_top_class(logits)
        category = infra_id2label[idx]
        cat_conf = conf
    elif sector == "education":
        logits = education_model(tensor).logits
        idx, conf = get_top_class(logits)
        category = edu_id2label[idx]
        cat_conf = conf
    elif sector == "environment":
        logits = environment_model(tensor).logits
        idx, conf = get_top_class(logits)
        category = env_id2label[idx]
        cat_conf = conf
    else:
        category = None
        cat_conf = sector_conf

    return {
        "sector": sector,
        "category": category,
        "sector_confidence": round(sector_conf, 3),
        "category_confidence": round(cat_conf, 3) if cat_conf is not None else None,
    }


# ========= VLM (GROQ) — PRIMARY BRAIN =========

def call_vlm(image_bytes: bytes) -> dict:
    """
    Groq Vision (LLaMA) classifier for all 20 sectors.
    Returns sector_key, problem_key, is_valid.
    """
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    sectors_list = sorted(list(ALL_SECTORS))
    prompt = f"""
You are an image classifier for government civic complaints in India.

You MUST output a JSON object with EXACTLY these keys:
- "sector": one of {sectors_list + ["invalid"]}
- "category": one specific problem key from the allowed list for that sector, or null if invalid
- "is_valid": true or false

Sectors and their allowed problem category keys are:

1) infrastructure: {SECTOR_CATEGORIES["infrastructure"]}
2) education: {SECTOR_CATEGORIES["education"]}
3) environment: {SECTOR_CATEGORIES["environment"]}
4) health: {SECTOR_CATEGORIES["health"]}
5) water_supply_and_sanitation: {SECTOR_CATEGORIES["water_supply_and_sanitation"]}
6) electricity_and_power: {SECTOR_CATEGORIES["electricity_and_power"]}
7) transportation: {SECTOR_CATEGORIES["transportation"]}
8) municipal_services: {SECTOR_CATEGORIES["municipal_services"]}
9) police_services: {SECTOR_CATEGORIES["police_services"]}
10) revenue: {SECTOR_CATEGORIES["revenue"]}
11) housing_and_urban_development: {SECTOR_CATEGORIES["housing_and_urban_development"]}
12) social_welfare: {SECTOR_CATEGORIES["social_welfare"]}
13) public_grievances: {SECTOR_CATEGORIES["public_grievances"]}
14) tourism_and_culture: {SECTOR_CATEGORIES["tourism_and_culture"]}
15) agriculture: {SECTOR_CATEGORIES["agriculture"]}
16) rural_development: {SECTOR_CATEGORIES["rural_development"]}
17) women_and_child_development: {SECTOR_CATEGORIES["women_and_child_development"]}
18) sports_and_youth_affairs: {SECTOR_CATEGORIES["sports_and_youth_affairs"]}
19) fire_and_emergency: {SECTOR_CATEGORIES["fire_and_emergency"]}
20) transport_safety: {SECTOR_CATEGORIES["transport_safety"]}

Rules:
- If the image clearly shows one of the civic issues above, choose the correct "sector" and "category" and set "is_valid": true.
- If the image is irrelevant (selfie, random object, mountains, animals, unrelated scenes),
  set "sector": "invalid", "category": null, "is_valid": false.

Return ONLY a JSON object, no explanation.
"""

    completion = groq_client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        temperature=0,
        max_completion_tokens=256,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
    )

    content = completion.choices[0].message.content
    if isinstance(content, str):
        data = json.loads(content)
    else:
        data = content

    sector_key = normalize_key(data.get("sector", "invalid"))
    category_key = data.get("category", None)
    if isinstance(category_key, str):
        category_key = normalize_key(category_key)
    is_valid = bool(data.get("is_valid", False))

    return {
        "sector_key": sector_key,
        "category_key": category_key,
        "is_valid": is_valid,
    }


# ========= HYBRID DECISION (VLM PRIMARY + ViT GUARD FOR 3 SECTORS) =========

def predict_issue_hybrid(image_bytes: bytes) -> dict:
    """
    1) VLM decides sector + category for 20 sectors.
    2) ViT validates only infra/education/environment and can override to invalid.
    3) Returns a rich JSON with is_valid_issue boolean.
    """

    # 1) VLM classification
    vlm = call_vlm(image_bytes)
    vlm_sector_key = vlm["sector_key"]
    vlm_category_key = vlm["category_key"]
    vlm_is_valid = vlm["is_valid"]

    # Normalize if VLM goes out of spec
    if vlm_sector_key not in ALL_SECTORS and vlm_sector_key != "invalid":
        vlm_sector_key = "invalid"
        vlm_category_key = None
        vlm_is_valid = False

    if vlm_sector_key in ALL_SECTORS:
        allowed_cats = set(SECTOR_CATEGORIES[vlm_sector_key])
        if vlm_category_key not in allowed_cats:
            # if VLM gives weird category, null it out
            vlm_category_key = None

    # 2) ViT guard (only for infra / education / environment)
    vit = vit_predict(image_bytes)
    vit_sector = vit["sector"]
    vit_category = vit["category"]
    vit_sector_conf = vit["sector_confidence"]
    vit_cat_conf = vit["category_confidence"]

    # ----- Final decision -----

    final_sector_key: str
    final_problem_key: str | None
    is_supported_by_vit = False

    # Case A: VLM says invalid or not valid issue
    if (not vlm_is_valid) or vlm_sector_key == "invalid":
        final_sector_key = "invalid"
        final_problem_key = None
        is_valid_issue = False
        status = "rejected"
        source = "vlm_invalid"

    # Case B: VLM sector is one of the 3 ViT-supported → add guardrail
    elif vlm_sector_key in VIT_SUPPORTED_SECTORS:
        is_supported_by_vit = True

        # If ViT is very confident it's invalid, override for safety
        if vit_sector == "invalid" and vit_sector_conf is not None and vit_sector_conf >= 0.75:
            final_sector_key = "invalid"
            final_problem_key = None
            is_valid_issue = False
            status = "rejected"
            source = "vit_override_invalid"
        else:
            final_sector_key = vlm_sector_key
            final_problem_key = vlm_category_key
            is_valid_issue = True
            status = "accepted"
            source = "vlm_primary_vit_guard"

    # Case C: VLM sector is one of the other 17 sectors → trust VLM
    else:
        final_sector_key = vlm_sector_key
        final_problem_key = vlm_category_key
        is_valid_issue = True
        status = "accepted"
        source = "vlm_primary_no_vit_needed"

    return {
        "sector": key_to_display(final_sector_key) if final_sector_key != "invalid" else "Invalid",
        "category": final_problem_key,
        "is_valid": is_valid_issue,
        "source": source,  # VLM_primary, VLM_primary_ViT_guard, vit_override_invalid, etc.
        "confidence_vlm": 1.0 if vlm_is_valid else 0.0,
        "confidence_vit": vit_cat_conf if is_supported_by_vit else None
    }

