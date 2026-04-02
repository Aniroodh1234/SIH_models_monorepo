import os
import json
from dotenv import load_dotenv

# [DISABLED — Groq backend]
# from langchain_groq import ChatGroq

# [ACTIVE — Gemini backend]
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import HumanMessage

from app.utils.language_utils import translate_to_english
from app.services.classifier_service import predict_category


load_dotenv()

# [DISABLED — Groq API key]
# GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# [ACTIVE — Gemini API key]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

CONFIDENCE_THRESHOLD = 0.65


def build_prompt(complaint: str, predicted_category: str):

    prompt = f"""
You are an AI system for a citizen grievance redressal platform.

Your task is to classify the complaint into the correct government category
and identify the specific issue type.

A machine learning model predicted the broad category as:
{predicted_category}

Use this prediction as guidance but verify using the complaint.

If the message is:
- unrelated to civic issues
- abusive or hateful
- spam or meaningless
- not a real complaint

Return:

{{
  "category": "not_recognized",
  "issue_type": "not_recognized"
}}

Otherwise classify using ONLY the taxonomy below.

You MUST select one category and one issue_type from the list.

----------------------------------------------------------------

CATEGORIES AND ISSUE TYPES

infrastructure:
potholes
collapsed_bridge
damaged_roads
cracked_building_wall
blocked_drain
broken_footpath
damaged_flyover
opened_manhole
damaged_boundary_wall

transportation:
damaged_bus_stop_shelter
damaged_road_signage
broken_speed_breaker
damaged_parking_area
damaged_traffic_signal
missing_lane_markings

electricity_and_power:
broken_streetlight
fallen_electric_pole
exposed_live_wires
transformer_leakage
sparking_electric_panel
power_outage
low_voltage_supply

water_supply_and_sanitation:
water_pipeline_leak
no_water_supply
dirty_drinking_water
blocked_sewer_line
overflowing_sewage
broken_public_water_tap

municipal_services:
overflowing_public_dustbin
garbage_not_collected
stray_animals_issue
blocked_public_toilet
damaged_municipal_parks
open_dumping_site
illegal_dumping

environment:
plastic_waste_accumulation
water_pollution
air_pollution
garbage_overflow
tree_cutting
dead_animals_on_road
waterlogging
open_sewage
construction_debris_dumping

health:
dirty_hospital_bed
broken_hospital_stretcher
overflowing_medical_waste
unhygienic_hospital_toilet
faulty_medical_equipment
lack_of_doctors
medicine_shortage

education:
broken_blackboard
broken_classroom_bench
dirty_drinking_water
broken_school_gate
broken_classroom_ceiling
broken_window_glass
damaged_hostel_bed
unhygienic_school_toilet
lack_of_teachers

housing_and_urban_development:
illegal_construction
building_wall_damage
sewage_leak_in_building
water_tank_damage
building_crack
construction_noise

public_safety:
broken_surveillance_camera
missing_police_patrol
street_fighting
unsafe_dark_area
illegal_activity_report

----------------------------------------------------------------

Complaint:
"{complaint}"

Return ONLY valid JSON.

Format:

{{
  "category": "<category_name>",
  "issue_type": "<issue_type>"
}}
"""

    return prompt


def call_llm_classifier(complaint, predicted_category):

    prompt = build_prompt(complaint, predicted_category)

    messages = [HumanMessage(content=prompt)]

    # [DISABLED — Groq LLM]
    # model = ChatGroq(
    #     model="openai/gpt-oss-120b",
    #     groq_api_key=GROQ_API_KEY,
    #     temperature=0
    # )

    # [ACTIVE — Gemini LLM]
    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0
    )

    response = model.invoke(messages)

    result_text = response.content.strip()

    # Strip markdown formatting that Gemini might add
    if result_text.startswith("```json"):
        result_text = result_text[7:]
    elif result_text.startswith("```"):
        result_text = result_text[3:]
    if result_text.endswith("```"):
        result_text = result_text[:-3]
    result_text = result_text.strip()

    try:
        parsed = json.loads(result_text)
        return parsed
    except Exception:
        return {
            "category": "not_recognized",
            "issue_type": "not_recognized"
        }


def hybrid_predict(complaint):

    # Step 1 — Translate complaint to English
    complaint_en = translate_to_english(complaint)

    # Step 2 — Run DistilBERT classification
    local_result = predict_category(complaint_en)

    predicted_category = local_result["category"]
    confidence = local_result["confidence"]

    # Step 3 — If model confident, use its category but refine issue using LLM
    if confidence >= CONFIDENCE_THRESHOLD:

        llm_result = call_llm_classifier(
            complaint_en,
            predicted_category
        )

        return {
            "category": llm_result["category"],
            "issue_type": llm_result["issue_type"],
            "confidence": confidence
        }

    # Step 4 — Low confidence → full LLM classification
    llm_result = call_llm_classifier(
        complaint_en,
        predicted_category
    )

    return {
        "category": llm_result["category"],
        "issue_type": llm_result["issue_type"],
        "confidence": 1.0
    }