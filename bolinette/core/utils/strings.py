def indent(text: str, /, spaces: int = 4, *, skip_first: bool = False) -> str:
    if not text:
        return text
    lines = text.splitlines()
    if skip_first:
        if len(lines) < 2:
            return text
        return lines[0] + "\n" + "\n".join(" " * spaces + line for line in lines[1:])
    return "\n".join(" " * spaces + line for line in lines)
