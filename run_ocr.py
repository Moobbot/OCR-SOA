import os
import warnings
import time
import torch
import pypdfium2 as pdfium
from PIL import Image
from transformers import (
    LightOnOcrForConditionalGeneration,
    LightOnOcrProcessor,
)

# Suppress warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="spaces")

# Configuration
MODEL_NAME = "lightonai/LightOnOCR-2-1B"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DTYPE = torch.bfloat16 if DEVICE == "cuda" else torch.float32
ATTN_IMPLEMENTATION = "sdpa" if DEVICE == "cuda" else "eager"

print(f"Running on {DEVICE.upper()} with {DTYPE} and {ATTN_IMPLEMENTATION} attention.")


import gc


def load_model():
    """Load the model and processor locally."""
    # Clear cache before loading
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print(f"Loading model: {MODEL_NAME}...")
    start_time = time.time()
    model = (
        LightOnOcrForConditionalGeneration.from_pretrained(
            MODEL_NAME,
            attn_implementation=ATTN_IMPLEMENTATION,
            torch_dtype=DTYPE,
            trust_remote_code=True,
        )
        .to(DEVICE)
        .eval()
    )

    processor = LightOnOcrProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)
    print(f"Model loaded in {time.time() - start_time:.2f}s")
    return model, processor


def clean_output_text(text):
    """Remove chat template artifacts from output."""
    markers_to_remove = ["system", "user", "assistant"]
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.lower() not in markers_to_remove:
            cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()

    if "assistant" in text.lower():
        parts = text.split("assistant", 1)
        if len(parts) > 1:
            cleaned = parts[1].strip()

    return cleaned


def render_pdf_page(page, max_resolution=1540, scale=2.77):
    """Render a PDF page to PIL Image."""
    width, height = page.get_size()
    pixel_width = width * scale
    pixel_height = height * scale
    resize_factor = min(1, max_resolution / pixel_width, max_resolution / pixel_height)
    target_scale = scale * resize_factor
    return page.render(scale=target_scale, rev_byteorder=True).to_pil()


def extract_text(model, processor, image, max_tokens=8192):
    """Run inference on a single image."""
    chat = [
        {
            "role": "user",
            "content": [
                {"type": "image", "url": image},
            ],
        }
    ]

    inputs = processor.apply_chat_template(
        chat,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )

    inputs = {
        k: (
            v.to(device=DEVICE, dtype=DTYPE)
            if isinstance(v, torch.Tensor)
            and v.dtype in [torch.float32, torch.float16, torch.bfloat16]
            else v.to(DEVICE) if isinstance(v, torch.Tensor) else v
        )
        for k, v in inputs.items()
    }

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.0,  # Deterministic
            top_p=0.9,
            use_cache=True,
            do_sample=False,
        )

    output_text = processor.decode(outputs[0], skip_special_tokens=True)
    return clean_output_text(output_text)


def is_blank_page(image, threshold=0.99):
    """
    Check if image is blank (mostly white).
    Returns True if blank.
    """
    # Convert to grayscale
    gray = image.convert("L")
    # Get extrema (optimization: if purely one color)
    min_val, max_val = gray.getextrema()
    if min_val == max_val:
        return max_val > 250  # Pure white or light gray treated as blank

    # Calculate percentage of white pixels (brightness > 250)
    # This handles scanned docs with some noise or paper texture
    histogram = gray.histogram()
    white_pixels = sum(histogram[250:])
    total_pixels = gray.width * gray.height
    white_ratio = white_pixels / total_pixels

    return white_ratio > threshold


def process_file(file_path, model, processor):
    """Process a PDF or Image file and save output to txt."""
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    # Create outputs directory
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(file_path))[0]
    print(f"\nProcessing: {file_path}")
    print("-" * 50)

    if file_path.lower().endswith(".pdf"):
        pdf = None
        try:
            pdf = pdfium.PdfDocument(file_path)
            total_pages = len(pdf)
            print(f"PDF loaded with {total_pages} pages.")

            for i in range(total_pages):
                print(f"Processing page {i + 1}/{total_pages}...")
                page = pdf[i]
                image = render_pdf_page(page)

                # Check for blank page
                if is_blank_page(image):
                    print(f"Skipping page {i + 1} (detected as blank).")
                    continue

                start_time = time.time()
                text = extract_text(model, processor, image)
                elapsed = time.time() - start_time

                output_filename = os.path.join(output_dir, f"{base_name}_page_{i+1}.md")
                with open(output_filename, "w", encoding="utf-8") as f:
                    f.write(text)

                print(f"[Done in {elapsed:.2f}s] Saved to {output_filename}")

        except Exception as e:
            print(f"Error processing PDF: {e}")
        finally:
            if pdf:
                pdf.close()

    else:
        # Assuming Image
        try:
            image = Image.open(file_path)
            print("Image loaded.")

            start_time = time.time()
            text = extract_text(model, processor, image)
            elapsed = time.time() - start_time

            output_filename = os.path.join(output_dir, f"{base_name}.md")
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(text)

            print(f"[Done in {elapsed:.2f}s] Saved to {output_filename}")

        except Exception as e:
            print(f"Error processing Image: {e}")


def main():
    # Define files to process
    files_to_process = [r"datasets\0218.pdf", r"data-test\Hinh01.jpg"]

    # Load model once
    model, processor = load_model()

    # Process each file
    try:
        for file_path in files_to_process:
            process_file(file_path, model, processor)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")


if __name__ == "__main__":
    main()
