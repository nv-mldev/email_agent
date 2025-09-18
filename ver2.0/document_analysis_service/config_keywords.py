# document_analysis_service/config_keywords.py
import re

_KEYWORDS_CONFIG = {
    "advance_remittance_notification": [
        "advance remittance notification",
        "remittance advice",
    ],
    "air_waybill": ["air waybill", "airway bill", "awb"],
    "analysis_certificate": ["certificate of analysis", "analysis certificate"],
    "arrival_notice": ["arrival notice", "notice of arrival"],
    "almond_inspection_certificate": ["almond inspection certificate"],
    "bill_of_exchange": ["bill of exchange"],
    "bill_of_lading": ["bill of lading", "b/l"],
    "bill_of_materials": ["bill of materials", "bom"],
    "booking_confirmation": ["booking confirmation", "booking note"],
    "booking_request": ["booking request"],
    "buyer_reconciliation": ["buyer reconciliation"],
    "cargo_damage_report": ["cargo damage report"],
    "certificate_of_origin": ["certificate of origin", "coo"],
    "certified_engineers_report": ["certified engineer’s report"],
    "claims_notification": ["claims notification"],
    "configure_to_order": ["configure to order"],
    "container_arrival_notice": ["container arrival notice"],
    "contract": ["contract", "service agreement", "supply agreement"],
    "cover_letter": ["cover letter"],
    "customs_declaration": ["customs declaration"],
    "dangerous_goods_declaration": ["dangerous goods declaration", "dgd"],
    "dangerous_goods_forms": ["dangerous goods forms"],
    "dangerous_goods_request": ["dangerous goods request"],
    "debit_credit_advice": ["debit advice", "credit advice"],
    "debit_note": ["debit note"],  # Added as requested
    "delivery_note": ["delivery note", "delivery receipt"],
    "delivery_order": ["delivery order"],
    "eur1_movement_certificate": ["eur.1", "movement certificate"],
    "export_declaration": ["export declaration"],
    "export_license": ["export license"],
    "free_sale_certificate": ["free sale certificate"],
    "fumigation_certificate": ["fumigation certificate"],
    "guarantee_of_origin": ["guarantee of origin"],
    "halal_certificate": ["halal certificate"],
    "health_certificate": ["health certificate"],
    "house_air_waybill": ["house air waybill", "hawb"],
    "house_bill_of_lading": ["house bill of lading", "hbl"],
    "import_declaration": ["import declaration"],
    "import_license": ["import license"],
    "industrial_license": ["industrial license"],
    "inspection_certificate": ["inspection certificate", "certificate of inspection"],
    "inspection_report": ["inspection report"],
    "insurance_certificate": ["insurance certificate", "certificate of insurance"],
    "insurance_policy": ["insurance policy"],
    "invoice": ["invoice", "bill to", "final invoice", "commercial invoice"],
    "letter_of_credit": ["letter of credit", "lc"],
    "letter_of_demand": ["letter of demand"],
    "letter_of_indemnity": ["letter of indemnity"],
    "letter_of_intent": ["letter of intent"],
    "master_air_waybill": ["master air waybill", "mawb"],
    "master_bill_of_lading": ["master bill of lading", "mbl"],
    "material_safety_data_sheet": ["material safety data sheet", "msds"],
    "non_gmo_statement": ["non-genetically modified statement"],
    "note": ["delivery note", "credit note", "debit note"],
    "order": ["order confirmation", "customer order"],
    "order_response": ["order response"],
    "other": ["other"],
    "packing_list": ["packing list", "packing slip"],
    "phytosanitary_certificate": ["phytosanitary certificate"],
    "product_manual": ["product manual"],
    "pro_forma_invoice": ["pro-forma invoice", "proforma invoice"],
    "promissory_note": ["promissory note"],
    "purchase_order": ["purchase order", "po number"],
    "quality_certificate": ["quality certificate", "certificate of quality"],
    "rail_waybill": ["rail waybill", "cim"],
    "request_for_payment": ["request for payment"],
    "road_waybill": ["road waybill", "cmr"],
    "sea_waybill": ["sea waybill"],
    "settlement": ["settlement"],
    "shipping_bill": ["shipping bill"],
    "shipping_instructions": ["shipping instructions"],
    "statement_on_dual_use_item": ["statement on dual-use item"],
    "straight_bill_of_lading": ["straight bill of lading"],
    "survey_report": ["survey report"],
    "technical_standard_certificate": ["technical standard certificate"],
    "terminal_handling_receipt": ["terminal handling receipt"],
    "test_report": ["test report"],
    "usda_certificate": ["usda certificate"],
    "verify_copy": ["verify copy", "verified copy"],
    "vessel_certificate": ["vessel certificate"],
    "veterinary_certificate": ["veterinary certificate"],
    "warehouse_receipt": ["warehouse receipt"],
    "warranty": ["warranty"],
    "weight_certificate": ["weight certificate", "certificate of weight"],
    "non_phytosanitary_certificate": ["non-phytosanitary certificate"],
}


def _create_spaced_regex(text: str) -> re.Pattern:
    """
    Converts a string like "purchase order" into a regex pattern that
    matches "purchase order", "p u r c h a s e o r d e r", etc.
    """
    # Split the text into words first, then process each word
    words = text.split()
    word_patterns = []

    for word in words:
        # Escape special regex characters in each word
        safe_word = re.escape(word)
        # Create pattern for spaced characters within the word:
        # h\s*e\s*l\s*l\s*o
        word_pattern = r"\s*".join(list(safe_word))
        word_patterns.append(word_pattern)

    # Join words with flexible whitespace: \s+
    full_pattern = r"\s+".join(word_patterns)

    # Compile for performance and ignore case
    return re.compile(full_pattern, re.IGNORECASE)


DOCUMENT_TITLE_KEYWORDS_REGEX = {}
for doc_type, keywords in _KEYWORDS_CONFIG.items():
    DOCUMENT_TITLE_KEYWORDS_REGEX[doc_type] = [
        _create_spaced_regex(kw) for kw in keywords
    ]
