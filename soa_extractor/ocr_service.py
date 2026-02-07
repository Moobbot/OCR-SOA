import os
import time
import torch
import pypdfium2 as pdfium
from PIL import Image
from transformers import (
    LightOnOcrForConditionalGeneration,
    LightOnOcrProcessor,
)


class OCRService:
    def __init__(self, model_name="lightonai/LightOnOCR-2-1B"):
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.attn_implementation = "sdpa" if self.device == "cuda" else "eager"
        self.model = None
        self.processor = None

    def load_model(self):
        if self.model is not None:
            return

        print(f"Loading OCR model: {self.model_name}...")
        start_time = time.time()
        self.model = (
            LightOnOcrForConditionalGeneration.from_pretrained(
                self.model_name,
                attn_implementation=self.attn_implementation,
                torch_dtype=self.dtype,
                trust_remote_code=True,
            )
            .to(self.device)
            .eval()
        )
        self.processor = LightOnOcrProcessor.from_pretrained(
            self.model_name, trust_remote_code=True
        )
        print(f"OCR Model loaded in {time.time() - start_time:.2f}s")

    def render_pdf_page(self, page, max_resolution=1540, scale=2.77):
        width, height = page.get_size()
        pixel_width = width * scale
        pixel_height = height * scale
        resize_factor = min(
            1, max_resolution / pixel_width, max_resolution / pixel_height
        )
        target_scale = scale * resize_factor
        return page.render(scale=target_scale, rev_byteorder=True).to_pil()

    def clean_output_text(self, text):
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

    def extract_text_from_image(self, image, max_tokens=8192):
        if self.model is None:
            self.load_model()

        chat = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": image},
                ],
            }
        ]

        inputs = self.processor.apply_chat_template(
            chat,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        )

        inputs = {
            k: (
                v.to(device=self.device, dtype=self.dtype)
                if isinstance(v, torch.Tensor)
                and v.dtype in [torch.float32, torch.float16, torch.bfloat16]
                else v.to(self.device) if isinstance(v, torch.Tensor) else v
            )
            for k, v in inputs.items()
        }

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=0.0,
                top_p=0.9,
                use_cache=True,
                do_sample=False,
            )

        output_text = self.processor.decode(outputs[0], skip_special_tokens=True)
        return self.clean_output_text(output_text)

    def process_pdf(self, pdf_path):
        """
        Yields (page_number, markdown_text) for each page.
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"{pdf_path} not found")

        pdf = pdfium.PdfDocument(pdf_path)
        total_pages = len(pdf)

        for i in range(total_pages):
            page = pdf[i]
            image = self.render_pdf_page(page)
            # Simplification: skipping blank page check for now or can add it back
            text = self.extract_text_from_image(image)
            yield i + 1, text

        pdf.close()
