class LLMClient:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def generate_batch(self, prompts: list[str]) -> list[str]:
        raise NotImplementedError

    def generate_with_schema(self, prompt: str, json_schema: str) -> str:
        # Default fallback if not supported
        return self.generate(prompt)

    def generate_batch_with_schema(
        self, prompts: list[str], json_schema: str
    ) -> list[str]:
        # Default fallback
        return [self.generate_with_schema(p, json_schema) for p in prompts]
