from vllm import LLM, SamplingParams
from soa_extractor.llm.base import LLMClient


class VLLMDirectClient(LLMClient):
    def __init__(self, model_name: str, max_model_len: int = 8192, dtype: str = "auto"):
        self.model_name = model_name
        self.llm = LLM(model=model_name, dtype=dtype, max_model_len=max_model_len)
        self.sampling = SamplingParams(temperature=0, top_p=1, max_tokens=1024)

    def generate(self, prompt: str) -> str:
        outputs = self.llm.generate([prompt], self.sampling)
        return outputs[0].outputs[0].text
