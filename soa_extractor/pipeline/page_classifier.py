def classify_page(text: str, rules: dict) -> str:
    """
    Classify the page based on rules.
    Expects rules['page_classification']['rules'] to be a list of rules.
    """
    if not rules or "page_classification" not in rules:
        return "Ignore"

    page_rules = rules["page_classification"].get("rules", [])
    # Sort by priority desc
    sorted_rules = sorted(page_rules, key=lambda x: x.get("priority", 0), reverse=True)

    # Get header (first few lines)
    lines = text.split("\n")
    # heuristics for header: first 10 lines or lines starting with #
    headers = [line for line in lines[:20]]
    header_text = "\n".join(headers).lower()

    default_type = "Ignore"

    for rule in sorted_rules:
        if rule.get("fallback"):
            default_type = rule.get("type", "Ignore")
            continue

        match_in = rule.get("match_in", "header")
        contains_any = rule.get("contains_any", [])

        matched = False
        if match_in == "header":
            for keyword in contains_any:
                if keyword.lower() in header_text:
                    matched = True
                    break

        if matched:
            return rule.get("type")

    return default_type
