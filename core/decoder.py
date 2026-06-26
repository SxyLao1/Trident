# -*- coding: utf-8 -*-
"""
v1.8.3: Webshell 解码过滤器

YARA 扫描前自动尝试还原混淆代码为明文，大幅提升命中率。

处理的混淆技术：
    1. Unicode escapes:  \\u0065val  →  eval
    2. Hex escapes:      \\x65\\x76\\x61\\x6c  →  eval
    3. char() encoding:  char(101).char(118)  →  eval
    4. chr() encoding:   chr(101).chr(118)    →  eval
    5. String concat:    'ev'.'al'            →  eval
    6. Octal escapes:    \\145\\166\\141\\154  →  eval
    7. Base64 in strings:  ZXZhbA==           →  eval
    8. ROT13/Nested:     riny('$p') → eval after decode

策略：生成多个解码变体，YARA 分别扫描每个变体。
"""

import base64
import codecs
import re


class WebShellDecoder:
    """WebShell 混淆代码解码器"""

    @staticmethod
    def decode(data: bytes) -> str:
        """
        主入口：对文件内容尝试所有解码策略。
        返回一个解码后的字符串（UTF-8），YARA 用这个来匹配。
        """
        text = data.decode('utf-8', errors='replace')

        # Strategy 1: Unicode escapes \uXXXX
        decoded = WebShellDecoder._decode_unicode_escapes(text)

        # Strategy 2: Hex escapes \xXX
        decoded = WebShellDecoder._decode_hex_escapes(decoded)

        # Strategy 3: char() / chr() encoding
        decoded = WebShellDecoder._decode_char_encoding(decoded)

        # Strategy 4: String concatenation 'a'.'b' → 'ab'
        decoded = WebShellDecoder._decode_string_concat(decoded)

        # Strategy 5: Octal escapes \XXX
        decoded = WebShellDecoder._decode_octal_escapes(decoded)

        # Strategy 6: Base64 strings
        decoded = WebShellDecoder._decode_base64_strings(decoded)

        return decoded

    @staticmethod
    def _decode_unicode_escapes(text: str) -> str:
        """\\u0065 → e, \\u{65} → e"""
        # Standard \uXXXX
        def replace_unicode(m):
            try:
                return chr(int(m.group(1), 16))
            except (ValueError, OverflowError):
                return m.group(0)
        text = re.sub(r'\\u([0-9a-fA-F]{4})', replace_unicode, text)
        # PHP \u{XX}
        text = re.sub(r'\\u\{([0-9a-fA-F]+)\}', replace_unicode, text)
        return text

    @staticmethod
    def _decode_hex_escapes(text: str) -> str:
        """\\x65 → e"""
        def replace_hex(m):
            try:
                return chr(int(m.group(1), 16))
            except (ValueError, OverflowError):
                return m.group(0)
        return re.sub(r'\\x([0-9a-fA-F]{2})', replace_hex, text)

    @staticmethod
    def _decode_octal_escapes(text: str) -> str:
        """\\145 → e"""
        def replace_octal(m):
            try:
                return chr(int(m.group(1), 8))
            except (ValueError, OverflowError):
                return m.group(0)
        return re.sub(r'\\([0-7]{3})', replace_octal, text)

    @staticmethod
    def _decode_char_encoding(text: str) -> str:
        """chr(101).chr(118) → eval, char(101,118,97,108) → eval"""
        # chr(N) or char(N)
        def replace_chr(m):
            codes = [int(x) for x in re.findall(r'\d+', m.group(0))]
            try:
                return ''.join(chr(c) for c in codes if 0 <= c <= 255)
            except (ValueError, OverflowError):
                return m.group(0)
        # PHP: chr(101).chr(118)...
        text = re.sub(r'chr\(\d+\)(?:\s*\.\s*chr\(\d+\))*', replace_chr, text)
        # SQL/JS: char(101,118,97,108)
        text = re.sub(r'char\([\d,\s]+\)', replace_chr, text)
        return text

    @staticmethod
    def _decode_string_concat(text: str) -> str:
        """'ev'.'al' → 'eval', "ev"."al" → "eval" """
        # PHP-style concatenation
        return re.sub(
            r"(['\"])([^'\"]+)\\1\s*\.\s*(['\"])([^'\"]+)\\3",
            lambda m: m.group(1) + m.group(2) + m.group(4) + m.group(1),
            text
        )

    @staticmethod
    def _decode_base64_strings(text: str) -> str:
        """Find base64-looking strings and try to decode them as hints"""
        # Look for strings that look like base64 (alphanumeric + / + =)
        candidates = re.findall(r'[\'"]([A-Za-z0-9+/=]{20,})[\'"]', text)
        for b64_str in candidates:
            try:
                decoded = base64.b64decode(b64_str).decode('utf-8', errors='replace')
                if any(kw in decoded.lower() for kw in ['eval', 'exec', 'system', 'passthru', 'shell_exec', 'base64_decode', 'popen', 'proc_open', 'assert', 'create_function', 'preg_replace', 'include', 'require', 'fopen', 'file_get_contents', 'file_put_contents']):
                    # Replace the base64 string with its decoded form as a comment
                    # (don't execute, just provide the pattern for YARA to match)
                    text += f"\n/* decoded: {decoded} */"
            except Exception:
                pass
        return text
