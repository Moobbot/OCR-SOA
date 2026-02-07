import re


def normalize_text(text):
    """Step 1: Normalize text (case-insensitive, collapse spaces)."""
    if not text:
        return ""
    # Collapse multiple spaces
    text = " ".join(text.split())
    return text


def clean_html_text(text):
    """Remove HTML tags and entities."""
    # Remove tags
    clean = re.sub(r"<[^>]+>", "", text)
    # Simple entity decoding
    clean = (
        clean.replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
    )
    return clean.strip()


def parse_html_tables(text):
    """
    Parse ALL HTML tables in text.
    Returns list of (rows, headers) tuples.
    rows are list of dicts (if headers match) or list of lists.
    """
    tables = []
    # Simple table parser - same as in BaseSectionPlugin
    table_matches = re.finditer(r"<table>(.*?)</table>", text, re.DOTALL)

    for match in table_matches:
        table_content = match.group(1)

        # Parse headers
        headers = []
        thead_match = re.search(r"<thead>(.*?)</thead>", table_content, re.DOTALL)
        if thead_match:
            header_row = re.findall(r"<th>(.*?)</th>", thead_match.group(1), re.DOTALL)
            headers = [clean_html_text(h) for h in header_row]

        # Parse rows
        rows = []
        tbody_match = re.search(r"<tbody>(.*?)</tbody>", table_content, re.DOTALL)
        if tbody_match:
            tr_matches = re.findall(r"<tr>(.*?)</tr>", tbody_match.group(1), re.DOTALL)
            for tr in tr_matches:
                # Capture cell content, handle empty cells
                td_matches = re.findall(r"<td>(.*?)</td>", tr, re.DOTALL)
                row_values = [clean_html_text(td) for td in td_matches]

                # If we have headers and lengths match, create a dict
                if headers and len(headers) == len(row_values):
                    rows.append(dict(zip(headers, row_values)))
                else:
                    rows.append(row_values)

        tables.append((rows, headers))

    return tables


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
