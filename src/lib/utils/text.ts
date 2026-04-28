/**
 * Normalize LLM response text by removing/replacing special patterns
 * Currently strips <think>...</think> thinking blocks
 */
export function normalizeLLMResponse(text: string): string {
  if (!text) return "";
  // Remove <think>...</think> blocks (DeepSeek reasoning style)
  return text.replace(/<think>[\s\S]*?<\/think>/g, "").trim();
}
