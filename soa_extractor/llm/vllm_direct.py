from typing import List, Optional
from vllm import LLM, SamplingParams

try:
    from vllm.sampling_params import GuidedDecodingParams
except ImportError:
    # Older vvlm versions might use different import or not support it easily
    # But user asked for it, assuming vllm >= 0.6.x
    GuidedDecodingParams = None

from soa_extractor.llm.base import LLMClient


class VLLMDirectClient(LLMClient):
    def __init__(self, model_name: str, max_model_len: int = 8192, dtype: str = "auto"):
        self.model_name = model_name
        self.llm = LLM(model=model_name, dtype=dtype, max_model_len=max_model_len)
        self.sampling = SamplingParams(temperature=0, top_p=1, max_tokens=1024)

    def generate(self, prompt: str) -> str:
        return self.generate_batch([prompt])[0]

    def generate_batch(self, prompts: List[str]) -> List[str]:
        outputs = self.llm.generate(prompts, self.sampling)
        return [output.outputs[0].text for output in outputs]

    def generate_with_schema(self, prompt: str, json_schema: str) -> str:
        return self.generate_batch_with_schema([prompt], json_schema)[0]

    def generate_batch_with_schema(
        self, prompts: List[str], json_schema: str
    ) -> List[str]:
        # Use guided decoding if available and schema provided
        sampling = self.sampling
        if json_schema:
            if GuidedDecodingParams:
                # Create a new sampling params with guided decoding
                sampling = SamplingParams(
                    temperature=0,
                    top_p=1,
                    max_tokens=1024,
                    guided_decoding=GuidedDecodingParams(json=json_schema),
                )
            else:
                print(
                    "Warning: GuidedDecodingParams not available in installed vLLM version."
                )

        outputs = self.llm.generate(prompts, sampling)
        return [output.outputs[0].text for output in outputs]
