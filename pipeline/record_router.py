def classify_record(row_text, rules):
    """Step 3b: Classify Record (only for Transaction pages)."""
    txn_group = "Trade"
    txn_type = "Trade"

    if not rules or "record_classification" not in rules:
        return txn_group, txn_type

    rec_rules = rules["record_classification"].get("rules", [])
    sorted_rules = sorted(rec_rules, key=lambda x: x.get("priority", 0), reverse=True)

    row_lower = row_text.lower()

    for rule in sorted_rules:
        if rule.get("fallback"):
            txn_group = rule.get("output_group", "Trade")
            txn_type = rule.get("output", "Trade")
            continue

        match_any = rule.get("match_any", [])
        matched = False
        for keyword in match_any:
            if keyword.lower() in row_lower:
                matched = True
                break

        if matched:
            return rule.get("output_group"), rule.get("output")

    return txn_group, txn_type
