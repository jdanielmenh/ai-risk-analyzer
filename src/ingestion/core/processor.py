import logging
import os
import re

from bs4 import BeautifulSoup, NavigableString, Tag

from ingestion.core.constants import (
    ITEM_TITLE_MAPPING,
)
from models.ingestion_models import (
    ChunkMetadata,
    DocumentChunk,
    Section,
    TableOfContentsItem,
)
from utils.logging_utils import setup_logging

logger = setup_logging(__name__)


class SECProcessor:
    def __init__(self, chunk_long_items: bool = True):
        self.chunk_long_items = chunk_long_items
        # Looks for "Item", space(s), number(s), optionally letter(s), optionally "." or ":"
        self.item_pattern = re.compile(r"^\s*(Item\s+\d+[A-Z]?\.?)\b", re.IGNORECASE)
        # Pattern to find PART I, PART II, etc.
        self.part_pattern = re.compile(
            r"^\s*(PART\s+(?:I|II|III|IV))\b\.?", re.IGNORECASE
        )

    def process_document(
        self, filepath: str, company: str, year: int
    ) -> list[DocumentChunk]:
        filename = os.path.basename(filepath)
        logger.info(f"Processing {filename} for {company} ({year})...")
        try:
            soup = self._load_html(filepath)
            if soup is None:
                # Error already logged in _load_html
                return []

            toc = self._extract_table_of_contents(soup)
            if not toc:
                logger.warning(
                    f"Could not extract Table of Contents from {filename}. Cannot proceed with section extraction."
                )
                return []
            logger.info(f"Extracted {len(toc)} items from TOC in {filename}.")

            sections = self._extract_sections(soup, toc)
            logger.info(
                f"Extracted {len(sections)} sections based on TOC from {filename}."
            )

            chunks = []
            for section in sections:
                chunks.extend(self._section_to_chunks(section, company, year, filename))

            logger.info(f"Generated {len(chunks)} chunks for {filename}.")
            return chunks

        except Exception as e:
            logger.exception(f"Critical error processing document {filepath}: {e}")
            return []

    def _load_html(self, filepath: str) -> BeautifulSoup | None:
        try:
            with open(filepath, encoding="utf-8") as f:
                content = f.read()
            # Remove XML declaration if present
            content = re.sub(
                r"^<\?xml.*?\?>", "", content, flags=re.IGNORECASE | re.DOTALL
            )
            soup = BeautifulSoup(content, "lxml")
            for element in soup(["script", "style", "header", "footer", "nav"]):
                element.decompose()
            hidden_divs = soup.find_all(
                "div", style=lambda s: s and "display:none" in s.lower()
            )
            for div in hidden_divs:
                # Be cautious, sometimes hidden divs contain useful data, but usually not main text.
                div.decompose()
            return soup
        except FileNotFoundError:
            logger.error(f"HTML file not found at {filepath}")
            return None
        except Exception as e:
            logger.exception(f"Error loading or parsing HTML from {filepath}: {e}")
            return None

    def _get_item_title(self, item_id: str) -> str:
        return ITEM_TITLE_MAPPING.get(item_id.strip(), item_id)

    def _extract_table_of_contents(
        self, soup: BeautifulSoup
    ) -> list[TableOfContentsItem]:
        toc_items = []
        seen_items = set()
        potential_toc_parents = soup.find_all(["table", "ul", "ol", "div"])

        found_toc_in_links = False
        for parent in potential_toc_parents:
            links = parent.find_all(
                "a", href=lambda href: href and href.startswith("#")
            )
            if not links:
                continue

            for link in links:
                link_text = link.get_text(" ", strip=True)
                match = self.item_pattern.match(link_text)
                if match:
                    item_number = match.group(1).strip().rstrip(".")
                    anchor = link["href"]

                    if item_number.lower() not in seen_items:
                        toc_items.append(
                            TableOfContentsItem(
                                item_number=item_number,
                                title=self._get_item_title(item_number),
                                anchor_text=anchor,
                            )
                        )
                        seen_items.add(item_number.lower())
                        found_toc_in_links = True

            if found_toc_in_links:
                break

        if not toc_items:
            logger.warning(
                "TOC extraction using <a> tags failed. Trying text search fallback..."
            )
            all_text_elements = soup.find_all(string=True)
            for text_node in all_text_elements:
                if text_node.parent.name in ["script", "style"]:
                    continue
                text = text_node.strip()
                match = self.item_pattern.match(text)
                if match:
                    item_number = match.group(1).strip().rstrip(".")
                    anchor = None
                    parent_tag = text_node.find_parent()
                    if parent_tag:
                        if parent_tag.get("id"):
                            anchor = f"#{parent_tag['id']}"
                        elif parent_tag.get("name"):
                            anchor = f"#{parent_tag['name']}"

                    if item_number.lower() not in seen_items and len(item_number) < 20:
                        toc_items.append(
                            TableOfContentsItem(
                                item_number=item_number,
                                title=self._get_item_title(item_number),
                                anchor_text=anchor,
                            )
                        )
                        seen_items.add(item_number.lower())

        return toc_items

    def _find_section_start_element(
        self, soup: BeautifulSoup, item: TableOfContentsItem
    ) -> Tag | None:
        if item.anchor_text and item.anchor_text.startswith("#"):
            anchor_name = item.anchor_text[1:]
            target = soup.find(id=anchor_name) or soup.find(attrs={"name": anchor_name})
            if target:
                # If the target is an empty <a>, find the next significant sibling.
                if target.name == "a" and not target.get_text(strip=True):
                    next_sib = target.find_next_sibling()
                    # Skip potentially multiple empty sibling 'a' tags
                    while (
                        next_sib
                        and next_sib.name == "a"
                        and not next_sib.get_text(strip=True)
                    ):
                        next_sib = next_sib.find_next_sibling()
                    if next_sib:
                        return next_sib
                    else:
                        logger.warning(
                            f"Anchor '{item.anchor_text}' points to empty <a> tag with no subsequent content sibling."
                        )
                        return target  # Return anchor itself as best guess
                else:
                    return target

        potential_headers = soup.find_all(
            ["p", "div", "b", "strong", "h1", "h2", "h3", "h4"]
        )
        item_num_pattern_strict = re.compile(
            rf"^\s*{re.escape(item.item_number)}\b", re.IGNORECASE
        )

        for header in potential_headers:
            text = header.get_text(" ", strip=True)
            if item_num_pattern_strict.match(text):
                parent = header.find_parent()
                is_bold = header.name in ["b", "strong"] or (
                    parent and parent.name in ["b", "strong"]
                )
                is_short_content = (
                    len(text) < len(item.item_number) + len(item.title) + 40
                )
                if is_bold or is_short_content:
                    if (
                        header.name in ["b", "strong"]
                        and parent
                        and parent.name in ["p", "div"]
                    ):
                        return parent
                    return header

        logger.warning(
            f"Could not find start element for {item.item_number} (Anchor: {item.anchor_text})"
        )
        return None

    def _extract_content_between(self, start_node: Tag, end_node: Tag | None) -> str:
        content_parts = []
        current_node = start_node
        start_node_text = ""

        if start_node.name == "a" and not start_node.get_text(strip=True):
            current_node = start_node.next_sibling
        elif start_node.name not in ["div", "table", "tr", "p", "ul", "ol"]:
            start_node_text = start_node.get_text(" ", strip=True)
            if start_node_text:
                temp_match = self.item_pattern.match(start_node_text)
                if not temp_match or len(start_node_text) > len(temp_match.group(0)):
                    content_parts.append(start_node_text)
            current_node = start_node.next_sibling
        else:
            current_node = start_node.next_sibling

        while current_node:
            # Stop condition
            if end_node and current_node == end_node:
                break

            # Safeguard against unusual nesting
            if (
                end_node
                and isinstance(current_node, Tag)
                and end_node in current_node.descendants
            ):
                logger.warning(
                    f"End node {end_node.name} found within current node {current_node.name}. Stopping extraction here."
                )
                break

            if isinstance(current_node, NavigableString):
                text = current_node.strip()
                if text:
                    content_parts.append(text)
            elif isinstance(current_node, Tag):
                if current_node.name in ["script", "style"]:
                    current_node = current_node.next_sibling
                    continue
                tag_text = current_node.get_text(" ", strip=True)
                lower_text = tag_text.lower()
                if "table of contents" in lower_text and len(lower_text) < 100:
                    pass
                elif tag_text:
                    content_parts.append(tag_text)

            current_node = current_node.next_sibling

        # This simple join might merge lines; careful cleaning follows.
        full_content = "\n".join(content_parts).strip()
        full_content = re.sub(r"\n{3,}", "\n\n", full_content)
        full_content = re.sub(r"[ \t]{2,}", " ", full_content)
        return full_content

    def _extract_sections(
        self, soup: BeautifulSoup, toc: list[TableOfContentsItem]
    ) -> list[Section]:
        sections = []
        # Store tuples of (toc_item, start_node)
        start_nodes_info = []

        for item in toc:
            start_node = self._find_section_start_element(soup, item)
            if start_node:
                start_nodes_info.append((item, start_node))
            else:
                # Warning logged in _find_section_start_element
                pass

        # Assuming start_nodes_info maintains document order based on TOC.
        # Accurate sorting by node position is complex.

        for i, (current_item, current_start_node) in enumerate(start_nodes_info):
            end_node = None
            # End node is the start node of the *next* section found
            if i + 1 < len(start_nodes_info):
                end_node = start_nodes_info[i + 1][1]

            content = self._extract_content_between(current_start_node, end_node)
            cleaned_content = self._clean_section_content(content)

            # Only add if there is relevant content after cleaning
            if cleaned_content:
                sections.append(
                    Section(
                        item_number=current_item.item_number,
                        title=current_item.title,
                        content=cleaned_content,
                    )
                )

        # TODO: Consider capturing content before the first item and after the last item.
        return sections

    def _clean_section_content(self, text: str) -> str:
        text = re.sub(
            r"Forward-Looking Statements.*?(?:\n\n|\Z)",
            "",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(r"\s*/s/\s+[A-Za-z ]{5,}", "", text)
        lines = text.splitlines()
        # Keep lines longer than 10 chars OR lines that look like item headers themselves
        cleaned_lines = [
            line.strip()
            for line in lines
            if len(line.strip()) > 10 or self.item_pattern.match(line.strip())
        ]
        text = "\n".join(cleaned_lines).strip()
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text

    def _chunk_text(
        self, text: str, chunk_size: int = 1500, overlap: int = 200
    ) -> list[str]:
        if not text:
            return []

        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current_chunk_paragraphs = []
        current_chunk_len = 0

        for p in paragraphs:
            p_strip = p.strip()
            if not p_strip:
                continue
            p_len = len(p_strip)

            if current_chunk_paragraphs and current_chunk_len + p_len + 2 > chunk_size:
                chunks.append("\n\n".join(current_chunk_paragraphs))
                # Start new chunk, calculating overlap from the *end* of the previous chunk
                overlap_paragraphs = []
                overlap_len = 0
                for prev_p in reversed(current_chunk_paragraphs):
                    prev_p_len = len(prev_p)
                    if (
                        overlap_len + prev_p_len + (2 if overlap_paragraphs else 0)
                        <= overlap
                    ):
                        overlap_paragraphs.insert(0, prev_p)
                        overlap_len += prev_p_len + (
                            2 if len(overlap_paragraphs) > 1 else 0
                        )
                    else:
                        break
                current_chunk_paragraphs = overlap_paragraphs + [p_strip]
                current_chunk_len = (
                    overlap_len + p_len + (2 if overlap_paragraphs else 0)
                )
            else:
                if current_chunk_paragraphs:
                    current_chunk_len += 2
                current_chunk_paragraphs.append(p_strip)
                current_chunk_len += p_len

        if current_chunk_paragraphs:
            chunks.append("\n\n".join(current_chunk_paragraphs))

        # Fallback / Refinement: If any chunk is still too large, force split.
        final_chunks = []
        for chunk in chunks:
            # Allow some tolerance (30%) over chunk_size before force splitting
            if len(chunk) > chunk_size * 1.3:
                # Force split oversized chunk
                start = 0
                while start < len(chunk):
                    end = start + chunk_size
                    final_chunks.append(chunk[start:end])
                    # Apply overlap here too
                    next_start = start + chunk_size - overlap
                    if next_start <= start:  # Prevent infinite loop
                        next_start = start + 1
                    start = next_start
                    if start >= len(chunk):
                        break
            elif chunk:
                final_chunks.append(chunk)
        return final_chunks

    def _section_to_chunks(
        self, section: Section, company: str, year: int, source: str
    ) -> list[DocumentChunk]:
        content = section.content
        if not content:
            return []

        chunks_data = []
        text_chunks = self._chunk_text(content)
        if not text_chunks:
            return []

        # Determine if section should be returned as one chunk or multiple
        process_as_single_chunk = not self.chunk_long_items or len(text_chunks) == 1

        if process_as_single_chunk:
            combined_text = text_chunks[0] if len(text_chunks) == 1 else section.content
            meta = ChunkMetadata(
                company=company,
                year=year,
                item=section.item_number,
                title=section.title,
                chunk_id=0,
                source=source,
            )
            chunks_data.append(DocumentChunk(text=combined_text, metadata=meta))
        else:
            # Create multiple chunks
            for i, chunk_text in enumerate(text_chunks):
                meta = ChunkMetadata(
                    company=company,
                    year=year,
                    item=section.item_number,
                    title=section.title,
                    chunk_id=i,
                    source=source,
                )
                chunks_data.append(DocumentChunk(text=chunk_text, metadata=meta))
        return chunks_data


# --- Example Usage ---
if __name__ == "__main__":
    # IMPORTANT: Set the correct path to your SEC HTML file
    html_filepath = "aapl-20240928.htm"  # Placeholder

    if not os.path.exists(html_filepath):
        logger.error(f"Error: HTML file not found at {html_filepath}")
        logger.error("Please provide the correct path to an SEC filing HTML file.")
    else:
        company_name = "Apple Inc."
        report_year = 2024

        # chunk_long_items=True will split long sections if needed
        processor = SECProcessor(chunk_long_items=True)

        document_chunks = processor.process_document(
            html_filepath, company_name, report_year
        )

        if document_chunks:
            logger.info("--- Processing Summary ---")
            logger.info(
                f"Successfully created {len(document_chunks)} chunks from {os.path.basename(html_filepath)}."
            )

            # Example: Log count for a specific item
            item_to_analyze = "Item 7"
            specific_item_chunks = [
                c for c in document_chunks if c.metadata.item == item_to_analyze
            ]
            logger.info(
                f"Found {len(specific_item_chunks)} chunks for {item_to_analyze}."
            )
            # Add more analysis or logging here if needed

        else:
            logger.warning(
                f"Processing {os.path.basename(html_filepath)} finished, but no chunks were created. Review previous logs."
            )
