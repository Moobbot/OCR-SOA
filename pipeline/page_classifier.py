def classify_page(text, rules):
    """Step 2: Classify Page-level."""
    page_type = "Ignore"

    if not rules or "page_classification" not in rules:
        return "Ignore"

    page_rules = rules["page_classification"].get("rules", [])
    sorted_rules = sorted(page_rules, key=lambda x: x.get("priority", 0), reverse=True)

    lines = text.split("\n")
    headers = [line for line in lines if line.strip().startswith("#")]
    header_text = "\n".join(headers) if headers else "\n".join(lines[:10])
    normalized_header = header_text.lower()

    for rule in sorted_rules:
        if rule.get("fallback"):
            page_type = rule.get("type", "Ignore")
            continue

        match_in = rule.get("match_in", "header")
        contains_any = rule.get("contains_any", [])

        matched = False
        if match_in == "header":
            for keyword in contains_any:
                if keyword.lower() in normalized_header:
                    matched = True
                    break

        if matched:
            return rule.get("type")

    return page_type
