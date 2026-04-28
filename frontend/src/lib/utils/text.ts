/**
 * Normalize LLM response text for clean Markdown display.
 *
 * This function is safe to apply incrementally during streaming because:
 * - All transformations are context-local (do not depend on full document structure)
 * - No state is carried between chunks; each chunk is self-contained
 * - Regex patterns match within lines only, avoiding multi-chunk boundary issues
 *
 * Transformations:
 * 1. Collapse excessive blank lines (3+ → 2) to prevent UI stretching
 * 2. Insert newline before list items that are glued to preceding punctuation
 * 3. Normalize list markers to "N. " format (from "1.Item", "1  Item", etc.)
 * 4. Normalize unordered list markers to have exactly one space after
 * 5. Trim trailing whitespace on every line
 *
 * IMPORTANT: This does NOT add blank lines between list items or around headers.
 * Those are stylistic choices better handled by CSS (margin/padding) to keep
 * the normalization logic simple and streaming-safe.
 */
export function normalizeLLMResponse(text: string): string {
  if (!text) return "";

  // Step 1: Collapse 3+ consecutive newlines to exactly 2
  // Rationale: LLMs sometimes output many blank lines; 2 is sufficient for visual separation
  let normalized = text.replace(/\n{3,}/g, "\n\n");
  normalized = normalized.replace(/([a-z])([.!?])([A-Z])/g, "$1$2 $3");
  normalized = normalized.replace(/([a-z0-9])([,;])([a-z0-9])/gi, "$1$2 $3");
  normalized = normalized.replace(/\n{3,}/g, "\n\n");
  normalized = normalized.replace(/([.:;])(?=\d+\.\s|[-*]\s)/g, "$1\n");

  // Step 2: Insert newline before list items attached to preceding sentence
  // Pattern: punctuation (., :, ;) followed immediately by list marker
  // Replacement: insert newline between punctuation and list marker
  // Example: "such as:1. Item" → "such as:\n1. Item"
  // Why not include "!" or "?"? Rarely used before lists and could interfere with
  // legitimate "?!." sequences in dialogue. Stick to sentence-ending punctuation.
  normalized = normalized.replace(/([.:;])(?=\d+\.\s+)/g, "$1\n");
  normalized = normalized.replace(/([.:;])(?=\-\s+|\*\s+)/g, "$1\n");
  normalized = normalized.replace(/^(\s*)(\d+)[\.\)\s]+\s*(.*?\S)\s*$/gm, (match, indent, num, content) => {
    if (!content) return match;
    return `${indent}${num}. ${content}`;
  });
  normalized = normalized.replace(/^(\s*)([\-\*])\s+(.*?\S)\s*$/gm, (match, indent, marker, content) => {
    if (!content) return match;
    return `${indent}${marker} ${content}`;
  });

  // Step 3: Normalize ordered list markers to "N. " format
  // Matches lines that START with a number followed by optional punctuation/whitespace
  // Flags: m (multiline) so ^/$ match line boundaries, g (global)
  // Preserves leading indentation (for nested lists) and captures content
  normalized = normalized.replace(/^(\s*)(\d+)[\.\)\s]+\s*(.*?\S)\s*$/gm, (match, indent, num, content) => {
    // If content is empty (blank line that matched), keep original
    if (!content) return match;
    // Standardize to "indent + number + period + space + content"
    return `${indent}${num}. ${content}`;
  });

  // Step 4: Normalize unordered list markers to have exactly one space after
  normalized = normalized.replace(/^(\s*)([\-\*])\s+(.*?\S)\s*$/gm, (match, indent, marker, content) => {
    if (!content) return match;
    return `${indent}${marker} ${content}`;
  });
  normalized = normalized.replace(/([a-z])\.([A-Z]{2,})/g, "$1. $2");

  // Step 5: Trim trailing whitespace on every line
  // This cleans up spaces/tabs at line ends that can accumulate during streaming
  normalized = normalized
    .split("\n")
    .map((line) => line.trimEnd())
    .join("\n")
    .trim();

  return normalized;
}
