#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Markdown -> PDF converter for posts/*.md using fpdf2 (native Unicode + TTF).

Renders: headings, paragraphs, lists, tables (md style with | separators),
inline code, fenced code blocks, blockquotes, horizontal rules, links.

Strategy:
  1. Parse MD into a sequence of blocks.
  2. Each block is rendered with explicit fpdf2 calls.
"""

import sys
import re
import os
import io
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
elif sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from fpdf import FPDF
from fpdf.enums import XPos, YPos


FONTS_DIR = Path(r"C:\Users\aabro\Documents\Moses\Архитектор\posts\_fonts")


class Report(FPDF):
    def __init__(self, title: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.title_doc = title

        self.set_margins(left=18, top=16, right=18)
        self.set_auto_page_break(auto=True, margin=18)

        self.add_font("DejaVu", "", str(FONTS_DIR / "DejaVuSans.ttf"), uni=True)
        self.add_font("DejaVu", "B", str(FONTS_DIR / "DejaVuSans-Bold.ttf"), uni=True)
        self.add_font("DejaVu", "I", str(FONTS_DIR / "DejaVuSans-Oblique.ttf"), uni=True)
        self.add_font("DejaVu", "BI", str(FONTS_DIR / "DejaVuSans-BoldOblique.ttf"), uni=True)
        self.add_font("DejaVuMono", "", str(FONTS_DIR / "DejaVuSansMono.ttf"), uni=True)
        self.add_font("DejaVuMono", "B", str(FONTS_DIR / "DejaVuSansMono.ttf"), uni=True)

        self.C_HEADING = (15, 61, 110)
        self.C_HRULE = (15, 61, 110)
        self.C_TABLE_HEAD_BG = (15, 61, 110)
        self.C_TABLE_HEAD_FG = (255, 255, 255)
        self.C_TABLE_ALT_BG = (245, 247, 250)
        self.C_TABLE_BORDER = (200, 209, 222)
        self.C_QUOTE_BAR = (107, 140, 175)
        self.C_TEXT = (26, 26, 26)
        self.C_FOOTER = (120, 120, 120)

        self.set_text_color(*self.C_TEXT)
        self.set_draw_color(*self.C_TABLE_BORDER)
        self.add_page()
    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*self.C_FOOTER)
        page_label = f"{self.title_doc} - str. {self.page_no()}/{{nb}}"
        self.cell(0, 5, page_label, align="C")
        self.set_text_color(*self.C_TEXT)

    @staticmethod
    def _strip_md_inline(text: str) -> str:
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"\1", text, flags=re.S)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text, flags=re.S)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", text, flags=re.S)
        text = re.sub(r"_(.+?)_", r"\1", text, flags=re.S)
        text = re.sub(r"~~(.+?)~~", r"\1", text, flags=re.S)
        return text

    # --- Block renderers --------------------------------------------------
    def heading(self, level: int, text: str):
        if level == 1 and self.page_no() > 1:
            self.add_page()
        sizes = {1: 18, 2: 13.5, 3: 11.5, 4: 10.5}
        before = {1: 8, 2: 7, 3: 5, 4: 4}
        after = {1: 5, 2: 4, 3: 3, 4: 2.5}
        self.ln(before[level])
        self.set_font("DejaVu", "B", sizes[level])
        self.set_text_color(*self.C_HEADING)
        clean = self._strip_md_inline(text).strip()
        self.multi_cell(0, sizes[level] * 0.55, clean)
        if level <= 2:
            y = self.get_y() + 1
            self.set_draw_color(*self.C_HRULE)
            self.set_line_width(0.6 if level == 1 else 0.3)
            self.line(self.l_margin, y, self.w - self.r_margin, y)
            self.set_line_width(0.2)
            self.set_draw_color(*self.C_TABLE_BORDER)
            self.ln(after[level])
        else:
            self.ln(after[level])
        self.set_text_color(*self.C_TEXT)
        self.set_font("DejaVu", "", 9.5)

    def p(self, text: str):
        clean = self._strip_md_inline(text).strip()
        self.set_font("DejaVu", "", 9.5)
        self.set_text_color(*self.C_TEXT)
        self.multi_cell(0, 4.2, clean)
        self.ln(1.5)

    def quote(self, text: str):
        clean = self._strip_md_inline(text).strip()
        self.set_font("DejaVu", "I", 9.5)
        self.set_text_color(60, 60, 60)
        avail = self.w - self.l_margin - self.r_margin - 6
        prev_y = self.get_y()
        self.set_x(self.l_margin + 4)
        self.multi_cell(avail, 4.2, clean, new_x=XPos.LEFT, new_y=YPos.NEXT)
        end_y = self.get_y()
        self.set_draw_color(*self.C_QUOTE_BAR)
        self.set_line_width(1.2)
        self.line(self.l_margin, prev_y - 1, self.l_margin, end_y + 0.5)
        self.set_line_width(0.2)
        self.set_draw_color(*self.C_TABLE_BORDER)
        self.set_text_color(*self.C_TEXT)
        self.set_font("DejaVu", "", 9.5)
        self.set_x(self.l_margin)
        self.ln(2)

    def hr(self):
        self.ln(1)
        y = self.get_y()
        self.set_draw_color(*self.C_HRULE)
        self.set_line_width(0.3)
        self.line(self.l_margin, y, self.w - self.r_margin, y)
        self.set_line_width(0.2)
        self.set_draw_color(*self.C_TABLE_BORDER)
        self.ln(3)

    def code_block(self, code: str):
        self.set_font("DejaVuMono", "", 8.2)
        self.set_text_color(*self.C_TEXT)
        avail = self.w - self.l_margin - self.r_margin
        prev_y = self.get_y()
        self.set_x(self.l_margin + 2)
        self.multi_cell(avail - 4, 3.8, code.rstrip("\n"),
                        new_x=XPos.LEFT, new_y=YPos.NEXT)
        end_y = self.get_y()
        # Draw background under text (text already drawn is fine, but we want bg)
        # Easier: just draw bg BEFORE text using pre-measured height. We already
        # wrote text, so we draw a subtle frame instead.
        self.set_draw_color(216, 222, 230)
        self.set_line_width(0.3)
        self.rect(self.l_margin, prev_y - 0.5, avail, end_y - prev_y + 1, style="D")
        self.set_line_width(0.2)
        self.set_draw_color(*self.C_TABLE_BORDER)
        self.set_x(self.l_margin)
        self.set_font("DejaVu", "", 9.5)
        self.ln(3)

    def list_item(self, text: str, ordered: bool, idx: int):
        clean = self._strip_md_inline(text).strip()
        marker = f"{idx}." if ordered else "-"
        self.set_font("DejaVu", "", 9.5)
        self.set_text_color(*self.C_TEXT)
        x = self.l_margin
        avail = self.w - self.l_margin - self.r_margin
        indent = 6
        self.set_x(x)
        self.cell(indent, 4.2, marker)
        self.set_x(x + indent)
        self.multi_cell(avail - indent, 4.2, clean)
        self.ln(0.8)

    def render_table(self, rows: list[list[str]]):
        if not rows:
            return
        # Clean cells
        cleaned_rows = []
        max_cols = 0
        for row in rows:
            cleaned = [self._strip_md_inline(c).strip().replace("\n", " ")
                       for c in row]
            cleaned_rows.append(cleaned)
            if len(cleaned) > max_cols:
                max_cols = len(cleaned)
        for r in cleaned_rows:
            while len(r) < max_cols:
                r.append("")

        avail = self.w - self.l_margin - self.r_margin
        col_w = avail / max_cols

        # Font size scales with column count
        if max_cols <= 4:
            head_pt, body_pt = 9.0, 8.5
        elif max_cols <= 6:
            head_pt, body_pt = 8.5, 8.0
        elif max_cols <= 8:
            head_pt, body_pt = 7.8, 7.3
        else:
            head_pt, body_pt = 7.2, 6.7
        line_h_body = body_pt * 0.42
        line_h_head = head_pt * 0.45

        # Estimate chars per line per column (rough)
        # DejaVu Sans at 7pt ~ 1.55 mm per char
        def chars_per_line(pt: float) -> int:
            mm_per_char = pt * 0.21  # rough
            return max(2, int(col_w / mm_per_char))

        def cell_lines(text: str, pt: float) -> int:
            if not text:
                return 1
            cpl = chars_per_line(pt)
            # Split by spaces; long words force a line each
            total_lines = 0
            for paragraph in text.split("\n"):
                words = paragraph.split(" ")
                cur_len = 0
                for w in words:
                    if cur_len + len(w) + 1 > cpl:
                        total_lines += 1
                        cur_len = len(w)
                    else:
                        cur_len += len(w) + 1
                total_lines += 1
            return max(1, total_lines)

        # Render rows one by one
        for ri, row in enumerate(cleaned_rows):
            # Compute max lines in this row
            if ri == 0:
                pt, lh = head_pt, line_h_head
            else:
                pt, lh = body_pt, line_h_body
            max_lines = max(cell_lines(c, pt) for c in row)
            row_h = lh * (1 + (max_lines - 1) * 1.1)

            # Page break
            if self.get_y() + row_h > self.h - self.b_margin:
                self.add_page()

            y0 = self.get_y()
            x0 = self.l_margin
            for ci, cell in enumerate(row):
                x = x0 + ci * col_w
                self.set_xy(x, y0)
                if ri == 0:
                    self.set_fill_color(*self.C_TABLE_HEAD_BG)
                    self.set_text_color(*self.C_TABLE_HEAD_FG)
                    self.set_font("DejaVu", "B", pt)
                    fill = True
                else:
                    fill = (ri % 2 == 0)
                    if fill:
                        self.set_fill_color(*self.C_TABLE_ALT_BG)
                    else:
                        self.set_fill_color(255, 255, 255)
                    self.set_text_color(*self.C_TEXT)
                    self.set_font("DejaVu", "", pt)
                # multi_cell inside fixed box
                self.multi_cell(col_w, lh, cell, border=1, align="L",
                                fill=fill, max_line_height=lh)
                # multi_cell moves cursor to next cell (start of next line)
                # Restore x for next column at same y0
                self.set_xy(x0 + (ci + 1) * col_w, y0)
            # Move down by row height
            self.set_xy(self.l_margin, y0 + row_h)
        self.set_text_color(*self.C_TEXT)
        self.set_font("DejaVu", "", 9.5)
        self.ln(2)


def parse_md(md_text: str):
    blocks = []
    lines = md_text.splitlines()
    i = 0
    n = len(lines)

    def is_table_separator(line: str) -> bool:
        s = line.strip()
        if "|" not in s:
            return False
        cells = [c.strip() for c in s.strip("|").split("|")]
        return all(re.match(r"^:?-+:?$", c) for c in cells if c)

    while i < n:
        line = lines[i]
        s = line.rstrip()

        if not s.strip():
            i += 1
            continue

        if s.strip().startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].rstrip().strip().startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", "\n".join(buf)))
            continue

        m = re.match(r"^(#{1,6})\s+(.+)$", s)
        if m:
            blocks.append(("h", len(m.group(1)), m.group(2).strip()))
            i += 1
            continue

        if re.match(r"^\s*([-*_])\1{2,}\s*$", s):
            blocks.append(("hr",))
            i += 1
            continue

        if s.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            blocks.append(("quote", " ".join(buf)))
            continue

        if "|" in s and i + 1 < n and is_table_separator(lines[i + 1]):
            rows = []
            while i < n and "|" in lines[i] and lines[i].strip():
                row_cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row_cells)
                i += 1
            blocks.append(("table", rows))
            continue

        if re.match(r"^\s*([-*+]|\d+\.)\s+", s):
            ordered = bool(re.match(r"^\s*\d+\.\s+", s))
            list_blocks = []
            while i < n and re.match(r"^\s*([-*+]|\d+\.)\s+", lines[i]):
                m2 = re.match(r"^\s*(?:[-*+]|\d+\.)\s+(.+)$", lines[i])
                if m2:
                    list_blocks.append(m2.group(1))
                    i += 1
            blocks.append(("list", list_blocks, ordered))
            continue

        buf = [s]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|```|\s*[-*+]\s|>\s|\s*\d+\.\s)", lines[i]) and "|" not in lines[i]:
            buf.append(lines[i])
            i += 1
        blocks.append(("p", " ".join(buf)))

    return blocks


def convert_file(md_path: Path, pdf_path: Path) -> bool:
    print(f"\n--> Converting: {md_path.name}")
    try:
        raw = md_path.read_text(encoding="utf-8")
        raw = raw.replace("│", "|")
        blocks = parse_md(raw)

        pdf = Report(title=md_path.stem)
        pdf.alias_nb_pages()

        for block in blocks:
            kind = block[0]
            if kind == "h":
                _, level, text = block
                pdf.heading(level, text)
            elif kind == "p":
                pdf.p(block[1])
            elif kind == "quote":
                pdf.quote(block[1])
            elif kind == "hr":
                pdf.hr()
            elif kind == "code":
                pdf.code_block(block[1])
            elif kind == "list":
                _, items, ordered = block
                for idx, item in enumerate(items, start=1):
                    pdf.list_item(item, ordered, idx)
                pdf.ln(2)
            elif kind == "table":
                pdf.render_table(block[1])

        tmp_path = pdf_path.with_suffix(".pdf.tmp")
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        pdf.output(str(tmp_path))

        if pdf_path.exists():
            try:
                pdf_path.unlink()
                tmp_path.rename(pdf_path)
                out_path = pdf_path
            except PermissionError:
                fallback = pdf_path.with_name(f"{pdf_path.stem}-new.pdf")
                tmp_path.rename(fallback)
                out_path = fallback
        else:
            tmp_path.rename(pdf_path)
            out_path = pdf_path

        size_kb = out_path.stat().st_size / 1024
        suffix = " [destination was locked]" if out_path != pdf_path else ""
        print(f"  [OK] {out_path.name} ({size_kb:.0f} KB){suffix}")
        return True
    except Exception as e:
        print(f"  [ERR] Exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    posts_dir = Path(r"C:\Users\aabro\Documents\Moses\Архитектор\posts")
    targets = [
        "2026-06-17-chat-boty-2025-obzor.md",
        "2026-06-17-chat-boty-2025-otvet.md",
        "2026-06-17-vibe-coding-obzor.md",
        "2026-06-17-multiagent-mcp-swarm-obzor.md",
        "2026-06-17-ai-stack-svodny-obzor.md",
    ]
    ok, fail = 0, 0
    for name in targets:
        md = posts_dir / name
        if not md.exists():
            print(f"  [ERR] Not found: {md}")
            fail += 1
            continue
        pdf = md.with_suffix(".pdf")
        if convert_file(md, pdf):
            ok += 1
        else:
            fail += 1
    print(f"\nDone: {ok} ok, {fail} failed")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())