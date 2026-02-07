from extraction_utils import classify_page, classify_record, parse_html_tables
import re


class ProcessingPipeline:
    def __init__(self, plugins, rules):
        self.plugins = {p.section_name: p for p in plugins}
        self.rules = rules

    def process_page(self, markdown_text, filename):
        """
        Orchestrates the 6-step pipeline.
        """
        # Step 2: Classify Page
        page_type = classify_page(markdown_text, self.rules)
        print(f"Page {filename} classified as: {page_type}")

        if page_type == "Ignore" or page_type == "Unknown":
            return {}

        # Step 3: Record Segmentation & Routing
        records = self.segment_and_route(markdown_text, page_type)

        processed_records = []
        for record in records:
            # Step 4: Field Extraction (Modular)
            # Currently using Plugins as the "Field Extractor"
            # In future, this line can be replaced by LLM call
            # We pass the record dict {type, target_section, text, raw_row}
            extracted_data = self.extract_fields(record, page_type)

            if not extracted_data:
                continue

            # Step 5: Validation (Basic for now)
            # self.validate(extracted_data)

            # Metadata
            extracted_data["File"] = filename

            # Ensure target_section and Type are preserved from routing (Overwriting plugin defaults)
            extracted_data["target_section"] = record.get("target_section", "Unknown")

            processed_records.append(extracted_data)

        return self.group_by_section(processed_records)

    def segment_and_route(self, text, page_type):
        """
        Step 3: Segment page into records and route them.
        Returns check: list of dicts {text, type, target_section, raw_row}
        """
        records = []
        all_tables = parse_html_tables(text)

        if page_type == "Positions":
            # Rule-based segmentation for Positions
            # Logic similar to PositionsPlugin.identify/extract but just returning raw rows
            currencies = ["SGD", "USD", "CHF", "HKD", "EUR", "GBP", "JPY", "AUD", "CAD"]

            # Context-aware segmentation
            current_portfolio = ""
            # Extract Portfolio No first (Page level)
            port_match = re.search(r"Portfolio number\s+(\d{3}-\d{6}-\d{2})", text)
            if port_match:
                current_portfolio = port_match.group(1)

            # Iterate tables
            for rows, headers in all_tables:
                # Header fix
                if headers:
                    first_h = headers[0].strip()
                    if first_h and (
                        first_h[0].isdigit()
                        or any(first_h.startswith(c) for c in currencies)
                    ):
                        rows.insert(
                            0,
                            (
                                dict(zip(headers, headers))
                                if isinstance(rows[0], dict)
                                else headers
                            ),
                        )

                # Logic copied from PositionsPlugin but simplified for segmentation
                current_block = []  # Not really block based, but row based

                for row in rows:
                    if isinstance(row, dict):
                        row_vals = list(row.values())
                    else:
                        row_vals = row

                    row_text = " ".join(row_vals).strip()
                    if not row_text or row_text.lower().startswith("total"):
                        continue

                    # Logic to identify Main Row vs Detail Row
                    # For now, just treat every row as potential record if it starts with digit/Currency
                    # This is imperfect compared to stateful plugin logic.
                    # To keep it strict, we might need to rely on Plugin for segmentation until we fully port logic.
                    # BUT user wants independent steps.
                    # Let's wrap the row as a record.

                    # NOTE: PositionsPlugin has complex state logic (merging rows).
                    # For this step, we will delegate to the plugin's internal logic if possible?
                    # No, strict pipeline means we must implement segmentation here.

                    # Re-implementing simplified segmentation for Positions:
                    # We will treat each 'valid start' as a record.

                    first_col = row_vals[0].strip()
                    is_main_row = False
                    if first_col and (
                        first_col[0].isdigit()
                        or any(first_col.startswith(c) for c in currencies)
                    ):
                        if not re.match(r"\d{2}\.\d{2}\.\d{4}", first_col):
                            is_main_row = True

                    if is_main_row:
                        records.append(
                            {
                                "type": "Positions",
                                "target_section": "Positions",
                                "text": row_text,
                                "raw_row": row_vals,
                                "page_context": {"Portfolio No.": current_portfolio},
                            }
                        )
                    else:
                        # Append to last record?
                        if records:
                            records[-1]["text"] += " " + row_text
                            # Also append to raw?
                            pass

        elif page_type == "Transaction":
            # Transaction Segmentation
            for rows, headers in all_tables:
                # Header fix
                if headers:
                    if re.search(r"\d{2}\.\d{2}\.\d{4}", headers[0]):
                        rows.insert(
                            0,
                            (
                                dict(zip(headers, headers))
                                if isinstance(rows[0], dict)
                                else headers
                            ),
                        )

                for row in rows:
                    if isinstance(row, dict):
                        row_vals = list(row.values())
                    else:
                        row_vals = row

                    if not row_vals:
                        continue

                    # Filter
                    # Must have date and type
                    is_valid_date = re.match(
                        r"\d{2}\.\d{2}\.\d{4}", row_vals[0].strip()
                    )
                    has_type = len(row_vals) > 1 and row_vals[1].strip() != ""

                    if is_valid_date and has_type:
                        row_text = " ".join(row_vals)
                        # Routing Step 3b
                        txn_group, txn_type = classify_record(row_text, self.rules)

                        records.append(
                            {
                                "type": txn_type,
                                "target_section": txn_group,  # Others / FXFT / Use Trade
                                "text": row_text,
                                "raw_row": row_vals,
                                "page_context": {},
                            }
                        )

        return records

    def extract_fields(self, record, page_type):
        """
        Step 4: Extract fields from a record.
        """
        # Here we call the plugin to do the specific field extraction
        # The plugin expects 'text' or 'row'.
        # We need to adapt the plugin interface or call specific method.
        # Since we haven't changed plugin interface yet, we might need a temporary adapter.

        # We can implement specific extractions here or assume Plugins are updated.
        # Let's assume Plugins are now Field Extractors.
        # But we haven't updated them yet.
        # So we utilize the data we have.

        data = {}
        row_vals = record.get("raw_row", [])
        row_text = record.get("text", "")
        context = record.get("page_context", {})

        if record["target_section"] == "Positions":
            # Use logic from PositionsPlugin
            # Ideally: plugin.extract_fields(row_vals, context)
            plugin = self.plugins.get("Positions")
            if plugin and hasattr(plugin, "extract_row"):
                return plugin.extract_row(row_vals, row_text, context)
            else:
                # Fallback / Inline logic for now
                pass

        elif record["target_section"] in ["Trade information", "Others", "FXTS"]:
            # Use logic from TradePlugin
            plugin = self.plugins.get("Trade information")
            if plugin and hasattr(plugin, "extract_row"):
                return plugin.extract_row(row_vals, row_text, context)

        # Temporary: If plugins not ready, return empty or implement inline
        # I will implement basic extraction here to satisfy the pipeline structure
        # (or rely on next step to refactor plugins)

        return data  # returns empty if plugins not updated

    def group_by_section(self, records):
        """
        Group flat list of records by target_section for Excel output.
        """
        grouped = {}
        for r in records:
            sec = r.get("target_section", "Unknown")
            if sec not in grouped:
                grouped[sec] = []
            grouped[sec].append(r)
        return grouped
