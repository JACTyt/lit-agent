"""Standalone extractor for concise answers from long agent responses.

Usage examples:
    # read from a file
    python scripts/extract_answer.py --file long_reply.txt

    # read from stdin
    cat long_reply.txt | python scripts/extract_answer.py

    # import and call
    from scripts.extract_answer import extract_answer
    short = extract_answer(long_text)
"""

import re
import sys
import argparse


def extract_answer(agent_output: str) -> str:
    """Return a concise answer parsed from a long agent response string.

    Heuristics used (in order):
    - If the agent appends a known signature (e.g., "Nya!"), return everything before it.
    - If there are 'Answer:' or 'Final Answer:' markers, return the following paragraph.
    - Otherwise, return the first non-empty paragraph trimmed to 1000 chars.
    """
    if not agent_output:
        return ""

    text = agent_output.strip()

    # Quick parse: try to extract from object-like reprs such as AIMessage(content='...')
    def _extract_all_from_repr(text: str):
        # return list of (marker, extracted_value)
        markers = ["AIMessage(content=", "ToolMessage(content=", "AIMessage(content:", "content=\'", 'content=\"']
        results = []
        for m in markers:
            start_search = 0
            while True:
                idx = text.find(m, start_search)
                if idx == -1:
                    break
                # find the start of the quoted content
                start = idx + len(m)
                # skip until the first quote char
                while start < len(text) and text[start] not in ("'", '"'):
                    start += 1
                if start >= len(text):
                    start_search = idx + 1
                    continue
                quote = text[start]
                # parse until the matching unescaped quote
                i = start + 1
                out_chars = []
                escaped = False
                while i < len(text):
                    ch = text[i]
                    if escaped:
                        out_chars.append(ch)
                        escaped = False
                    else:
                        if ch == "\\":
                            escaped = True
                        elif ch == quote:
                            results.append((m, ''.join(out_chars)))
                            break
                        else:
                            out_chars.append(ch)
                    i += 1
                start_search = idx + 1
        return results

    parsed_pairs = _extract_all_from_repr(text)
    # Prefer last AIMessage content, then ToolMessage, then any content
    ai_messages = [v for (k, v) in parsed_pairs if k.startswith("AIMessage") and v and v.strip()]
    if ai_messages:
        return ai_messages[-1].strip()[:1000]
    tool_messages = [v for (k, v) in parsed_pairs if k.startswith("ToolMessage") and v and v.strip()]
    if tool_messages:
        return tool_messages[-1].strip()[:1000]
    generic = [v for (k, v) in parsed_pairs if v and v.strip()]
    if generic:
        return generic[-1].strip()[:1000]

    # 1) Signature marker
    sigs = ["Nya!", "Nya", "-- End --"]
    for s in sigs:
        idx = text.rfind(s)
        if idx != -1:
            candidate = text[:idx].strip()
            if candidate:
                return candidate

    # 2) Explicit markers
    m = re.search(r"(?:Final Answer:|Answer:|Conclusion:|Summary:)\s*(.+)$", text, flags=re.IGNORECASE | re.DOTALL)
    if m:
        ans = m.group(1).strip()
        # take up to first blank-line or 1000 chars
        ans = ans.split("\n\n")[0].strip()
        return ans[:1000]

    # 3) Paragraph heuristic
    paras = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if paras:
        return paras[0][:1000]

    # 4) Fallback: return shortened text
    return text[:1000]


def _main():
    parser = argparse.ArgumentParser(description="Extract a concise answer from a long agent reply.")
    parser.add_argument("--file", "-f", help="Path to file containing the long agent reply. If omitted, reads stdin.")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as fh:
            content = fh.read()
    else:
        content = sys.stdin.read()

    out = extract_answer(content)
    print(out)


if __name__ == "__main__":
    _main()
