import os
import extraction_service


def main():
    # Legacy/Standalone execution
    rule_path = os.path.join("docs", "rule.json")
    output_dir = "outputs"
    output_excel = "extracted_data.xlsx"

    # Load rules once
    rules = extraction_service.load_rules(rule_path)
    plugins = extraction_service.initialize_system(rule_path)
    if not plugins:
        return

    # Initialize Pipeline
    from processing_pipeline import ProcessingPipeline

    pipeline = ProcessingPipeline(plugins, rules)

    files = [f for f in os.listdir(output_dir) if f.endswith(".md")]
    files.sort()

    print(f"\n--- Processing {len(files)} files ---")

    all_results = {}

    for filename in files:
        filepath = os.path.join(output_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # Process with Pipeline
        results = pipeline.process_page(text, filename)

        if results:
            # Merge results into all_results
            for section, rows in results.items():
                if section not in all_results:
                    all_results[section] = []
                all_results[section].extend(rows)

    if all_results:
        # Always save to ensure all 4 sheets are present even if empty
        if os.path.exists(output_excel):
            os.remove(output_excel)
        extraction_service.append_to_excel(all_results, output_excel)

    print(f"\nSuccessfully saved to {os.path.abspath(output_excel)}")


if __name__ == "__main__":
    main()
