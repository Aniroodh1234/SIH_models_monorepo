"""
Prompt Templates for the SwarajDesk AI Report Generator.

Three prompts for three report types:
  SURVEY_REPORT_PROMPT   → JSON Report 1 (NGO/Survey data)
  BACKEND_REPORT_PROMPT  → JSON Report 2 (SwarajDesk complaints)
  FUSION_REPORT_PROMPT   → JSON Report 3 (Combined analysis)

All prompts instruct Gemini to return ONLY valid JSON with no extra text.
"""

# ─────────────────────────────────────────────────────────────────
# Report 1 — Survey / NGO Data Report
# ─────────────────────────────────────────────────────────────────

SURVEY_REPORT_PROMPT = """You are an expert policy analyst and data scientist working for a civic governance NGO in India.

Your task is to analyze survey and field research data about civic issues and generate a comprehensive structured report in JSON format.

CATEGORY: {category}
TIMESTAMP: {timestamp}

RETRIEVED SURVEY DATA:
{context}

---

Based on the survey data above, generate a detailed JSON report. The report must:
1. Synthesize findings across all documents - do NOT just list documents
2. Identify patterns, trends, and recurring issues
3. Quantify findings where possible (severity counts, percentages, frequencies)
4. Provide actionable, specific recommendations
5. Cite source types (NGO reports, field surveys, citizen feedback)

Return ONLY valid JSON with this exact structure (no markdown, no explanation):

{{
  "report_type": "survey_report",
  "category": "{category}",
  "generated_at": "{timestamp}",
  "executive_summary": "2-3 sentence high-level summary of the most critical findings",
  "summary": "Comprehensive paragraph summarizing all key patterns and issues found in the survey data",
  "total_documents_analyzed": <integer count of documents used>,
  "key_findings": [
    {{
      "finding": "Specific, concrete finding statement",
      "severity": "high|medium|low",
      "frequency": "How often this issue appears (e.g., reported in X of Y documents)",
      "supporting_evidence": "Brief quote or summary from the data",
      "affected_areas": ["geographic area or demographic group"]
    }}
  ],
  "issue_breakdown": [
    {{
      "issue_type": "Specific sub-category of the problem",
      "count": <estimated number of records mentioning this>,
      "percentage": <percentage of total records>,
      "description": "What this issue involves"
    }}
  ],
  "geographic_analysis": {{
    "most_affected_areas": ["list of locations/areas most affected"],
    "distribution": "Description of geographic spread of the issue"
  }},
  "demographic_insights": {{
    "most_affected_groups": ["groups disproportionately affected"],
    "patterns": "Key demographic patterns observed"
  }},
  "statistics": {{
    "total_records_analyzed": <integer>,
    "severity_distribution": {{
      "high": <count>,
      "medium": <count>,
      "low": <count>
    }},
    "geographic_coverage": ["list of states/districts mentioned"],
    "data_sources_count": <number of distinct sources>,
    "source_types": ["types of sources e.g., NGO report, field survey, news article"]
  }},
  "root_causes": [
    "Identified root cause 1",
    "Identified root cause 2"
  ],
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "recommendation": "Specific actionable recommendation",
      "responsible_authority": "Who should act on this",
      "timeline": "Suggested implementation timeframe"
    }}
  ],
  "data_gaps": ["Areas where more data is needed"],
  "references": [
    {{
      "source_type": "Type of source",
      "url": "URL if available",
      "description": "Brief description of this source"
    }}
  ]
}}
"""


# ─────────────────────────────────────────────────────────────────
# Report 2 — SwarajDesk Backend / Complaint Data Report
# ─────────────────────────────────────────────────────────────────

BACKEND_REPORT_PROMPT = """You are an expert data analyst specializing in urban governance, citizen grievance analysis, and public service delivery in India.

Your task is to analyze SwarajDesk citizen complaint data and generate a comprehensive structured complaint analysis report in JSON format.

CATEGORY: {category}
TIMESTAMP: {timestamp}

RETRIEVED COMPLAINT DATA:
{context}

---

Based on the complaint data above, generate a detailed complaint analysis report. The report must:
1. Identify the most frequent complaint types and patterns
2. Analyze geographic hotspots (which cities/districts have most complaints)
3. Break down complaints by demographic (age groups, gender if available)
4. Identify urgent/critical issues requiring immediate attention
5. Provide data-driven recommendations for service improvement

Return ONLY valid JSON with this exact structure (no markdown, no explanation):

{{
  "report_type": "backend_report",
  "category": "{category}",
  "generated_at": "{timestamp}",
  "executive_summary": "2-3 sentence high-level summary of complaint patterns",
  "summary": "Comprehensive paragraph summarizing complaint patterns, hotspots, and key issues",
  "total_documents_analyzed": <integer count of complaint records analyzed>,
  "complaint_analysis": {{
    "total_complaints_analyzed": <integer>,
    "top_issues": [
      {{
        "issue": "Specific complaint type",
        "frequency": <estimated count>,
        "percentage": <percentage of total>,
        "severity": "high|medium|low",
        "description": "What complainants say about this issue"
      }}
    ],
    "geographic_hotspots": [
      {{
        "location": "City/District/State",
        "complaint_volume": "high|medium|low",
        "primary_issues": ["Main issue types in this area"]
      }}
    ],
    "complaint_trends": "Description of any temporal or emerging patterns in complaints"
  }},
  "demographic_breakdown": {{
    "by_age_group": [
      {{
        "age_range": "e.g., 18-30",
        "complaint_proportion": "high|medium|low",
        "primary_concerns": ["What this age group complains about most"]
      }}
    ],
    "by_gender": {{
      "patterns": "Gender-based complaint patterns if discernible"
    }}
  }},
  "key_findings": [
    {{
      "finding": "Specific, concrete finding",
      "severity": "high|medium|low",
      "frequency": "How often this appears",
      "supporting_evidence": "Summary from complaint data",
      "affected_areas": ["locations"]
    }}
  ],
  "urgent_issues": [
    {{
      "issue": "Issue requiring immediate attention",
      "severity": "high",
      "affected_locations": ["where this is most critical"],
      "recommended_action": "What needs to happen immediately"
    }}
  ],
  "statistics": {{
    "total_records_analyzed": <integer>,
    "severity_distribution": {{
      "high": <count>,
      "medium": <count>,
      "low": <count>
    }},
    "geographic_coverage": ["list of states/districts mentioned"],
    "survey_sources": ["survey IDs or titles if available"]
  }},
  "service_delivery_gaps": [
    "Identified gap in government service delivery"
  ],
  "recommendations": [
    {{
      "priority": "high|medium|low",
      "recommendation": "Specific actionable recommendation",
      "responsible_authority": "Which department/authority should act",
      "timeline": "Suggested timeframe",
      "expected_impact": "What improvement this would achieve"
    }}
  ],
  "references": [
    {{
      "survey_id": "Survey identifier if available",
      "source_type": "citizen_complaint|survey_response",
      "location": "Geographic location of respondent"
    }}
  ]
}}
"""


# ─────────────────────────────────────────────────────────────────
# Report 3 — Fusion Report (Survey + Backend Combined)
# ─────────────────────────────────────────────────────────────────

FUSION_REPORT_PROMPT = """You are a senior policy analyst and strategic advisor for the Government of India's urban governance reform initiatives.

Your task is to synthesize and cross-reference two independent reports — one from NGO/field surveys and one from citizen complaint data — to produce a comprehensive unified strategic analysis report.

CATEGORY: {category}
TIMESTAMP: {timestamp}

REPORT 1 — NGO/SURVEY REPORT:
{survey_report}

REPORT 2 — SWARAJDESK COMPLAINT REPORT:
{backend_report}

---

You must:
1. Cross-reference findings: identify where BOTH reports agree (corroborated evidence = higher priority)
2. Identify findings unique to each source (triangulate the full picture)
3. Surface the most critical actionable insights combining both perspectives
4. Highlight contradictions or data gaps between the two sources
5. Produce prioritized, strategic recommendations backed by dual-source evidence

Return ONLY valid JSON with this exact structure (no markdown, no explanation):

{{
  "report_type": "fusion_report",
  "category": "{category}",
  "generated_at": "{timestamp}",
  "executive_summary": "3-4 sentence strategic overview combining insights from both data sources",
  "summary": "Comprehensive narrative that synthesizes key findings from both survey and complaint data, highlighting convergences and divergences",
  "data_sources": {{
    "survey_source": "NGO/Field Survey Data",
    "backend_source": "SwarajDesk Citizen Complaint Platform",
    "survey_records_analyzed": <number from survey report>,
    "backend_records_analyzed": <number from backend report>
  }},
  "cross_reference_analysis": {{
    "corroborated_findings": [
      {{
        "finding": "Issue confirmed by BOTH survey and complaint data",
        "survey_evidence": "What the survey data shows",
        "backend_evidence": "What the complaint data shows",
        "confidence": "high|medium",
        "priority": "high|medium|low"
      }}
    ],
    "survey_only_findings": [
      {{
        "finding": "Issue found only in survey/NGO data",
        "significance": "Why this matters even without complaint data",
        "possible_reason_for_gap": "Why complaints may not reflect this"
      }}
    ],
    "backend_only_findings": [
      {{
        "finding": "Issue found only in complaint data",
        "significance": "Why this matters",
        "possible_reason_for_gap": "Why surveys may have missed this"
      }}
    ]
  }},
  "unified_findings": [
    {{
      "finding": "Synthesized finding from combined analysis",
      "severity": "high|medium|low",
      "data_sources_confirming": ["survey", "backend"],
      "combined_evidence": "Summary of evidence from both sources",
      "affected_population": "Who is most affected",
      "affected_areas": ["geographic locations"],
      "urgency": "immediate|short_term|long_term"
    }}
  ],
  "gap_analysis": {{
    "underreported_issues": ["Issues present in surveys but not complaints — possibly unreported"],
    "over-reported_vs_actual": ["Issues heavily complained about but less severe than data suggests"],
    "data_quality_notes": ["Any inconsistencies or quality concerns between sources"]
  }},
  "combined_statistics": {{
    "total_records_analyzed": <sum of both>,
    "corroboration_rate": "Percentage of findings confirmed by both sources",
    "severity_distribution": {{
      "high": <combined high severity count>,
      "medium": <combined medium count>,
      "low": <combined low count>
    }},
    "geographic_coverage": ["all locations mentioned across both reports"],
    "key_demographics_affected": ["demographic groups most impacted"]
  }},
  "strategic_insights": [
    "High-level insight combining both data sources that would not be visible from either alone"
  ],
  "prioritized_recommendations": [
    {{
      "rank": <1-based priority rank>,
      "recommendation": "Specific, actionable recommendation",
      "evidence_base": "both_sources|survey_only|backend_only",
      "priority": "high|medium|low",
      "responsible_authority": "Which government department/body should act",
      "timeline": "immediate (0-3 months)|short_term (3-12 months)|long_term (1-3 years)",
      "expected_impact": "Measurable outcome of implementing this recommendation",
      "supporting_findings": ["Which unified findings support this"]
    }}
  ],
  "monitoring_indicators": [
    {{
      "indicator": "Measurable KPI to track improvement",
      "baseline": "Current state based on data",
      "target": "Desired state after interventions",
      "data_source": "How to measure this"
    }}
  ],
  "references": {{
    "survey_sources": ["NGO/survey source references from Report 1"],
    "backend_sources": ["SwarajDesk survey IDs or references from Report 2"]
  }}
}}
"""

# ─────────────────────────────────────────────────────────────────
# Report 4 — Global Analysis Report (All Complaints)
# ─────────────────────────────────────────────────────────────────

ANALYZE_REPORT_PROMPT = """You are a senior data scientist and urban governance expert working for SwarajDesk.

Your task is to analyze a diverse dataset of citizen complaints lodged on the SwarajDesk application and generate a comprehensive, overarching "Whole Big Report" in JSON format.

CATEGORY FILTER: {category} (If 'All', this represents the entire platform)
TIMESTAMP: {timestamp}

RETRIEVED DIVERSE COMPLAINTS (Extracted via MMR for maximum coverage):
{context}

---

Based on the highly diverse sample of complaint data above, generate a robust global report. The report must:
1. Identify the most critical systemic issues plaguing the platform across all categories.
2. Analyze cross-functional hotspots (e.g., how water issues correlate with health issues or specific geographic areas).
3. Provide a high-level severity distribution and timeline patterns if visible.
4. Extract systemic root causes rather than isolated incidents.
5. Deliver actionable, strategic macro-recommendations for the government/municipal bodies.

Return ONLY valid JSON with this exact structure (no markdown, no explanation):

{{
  "report_type": "analyze_report",
  "category_scope": "{category}",
  "generated_at": "{timestamp}",
  "executive_summary": "A powerful 3-4 sentence high-level summary of the overall state of citizen grievances, describing the most critical systemic failures.",
  "comprehensive_overview": "A detailed paragraph synthesizing the primary themes, geographical patterns, and overriding sentiments of the citizens.",
  "total_sample_documents_analyzed": <integer>,
  "systemic_issues": [
    {{
      "issue_name": "Broad systemic issue (e.g., 'Chronic Water Supply Failure')",
      "contributing_factors": ["Sub-issues or related categories"],
      "severity": "critical|high|medium|low",
      "impacted_regions": ["geographical areas showing this trend"],
      "description": "Why this is a systemic problem based on the data"
    }}
  ],
  "categorical_breakdown": [
    {{
      "category": "Specific category (e.g., Infrastructure)",
      "prominence": "high|medium|low",
      "key_complaints": ["Most frequent complaints in this category"],
      "urgency_level": "critical|high|medium|low"
    }}
  ],
  "geographic_macro_analysis": {{
    "highest_volume_regions": ["Regions with massive multi-category complaints"],
    "emerging_hotspots": ["Regions showing new or acute issues"],
    "regional_disparities": "Narrative comparing complaint intensity across different areas"
  }},
  "root_cause_analysis": [
    {{
      "root_cause": "Underlying reason (e.g., 'Aging Pipeline Infrastructure')",
      "manifesting_symptoms": ["How it appears in complaints (waterlogging, poor water quality)"],
      "confidence_level": "high|medium|low"
    }}
  ],
  "statistics_estimation": {{
    "severity_distribution": {{
      "critical": <percentage or count estimation>,
      "high": <percentage or count estimation>,
      "medium": <percentage or count estimation>
    }},
    "top_affected_demographics": ["If mentioned (e.g., 'Slum residents', 'Commuters')"]
  }},
  "strategic_recommendations": [
    {{
      "priority": "critical|high|medium",
      "initiative": "Broad strategic recommendation",
      "target_departments": ["Which departments need to coordinate"],
      "expected_outcome": "What this will resolve systemically",
      "timeframe": "immediate|short_term|long_term"
    }}
  ]
}}
"""
