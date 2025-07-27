import os
import json
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
from bot_app.embeddings import get_embedding

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ChunkMetadata:
    """מטא-דאטה של קטע טקסט"""
    category: str = ""
    subcategory: str = ""
    service_name: str = ""
    hmo_name: str = ""
    insurance_level: str = ""
    source_file: str = ""
    chunk_type: str = ""  # paragraph, list_item, table_cell, etc.

class Config:
    HTML_DIR = "phase2_data"
    OUT_FILE = "saved_vectors/vectors.json"
    CHUNK_MIN_LEN = 20
    BATCH_SIZE = 100  
    MAX_CHUNK_LEN = 1000  

class ImprovedVectorGenerator:
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        
    def clean_text(self, text: str) -> str:
        if not text:
            return ""
        
        text = " ".join(text.split())
        
        if len(text) > self.config.MAX_CHUNK_LEN:
            text = text[:self.config.MAX_CHUNK_LEN] + "..."
            
        return text.strip()
    
    def extract_insurance_info(self, cell_content: str) -> Dict[str, str]:
        levels = {"זהב": "", "כסף": "", "ארד": ""}
        
        for level in levels.keys():
            if f"<strong>{level}:</strong>" in cell_content:
                start = cell_content.find(f"<strong>{level}:</strong>") + len(f"<strong>{level}:</strong>")
                end = cell_content.find("<br>", start)
                if end == -1:
                    end = cell_content.find(f"<strong>", start)
                if end == -1:
                    end = len(cell_content)
                
                level_text = cell_content[start:end].strip()
                levels[level] = self.clean_text(BeautifulSoup(level_text, "html.parser").get_text())
        
        return levels
    
    def create_structured_chunk(self, text: str, metadata: ChunkMetadata) -> str:
        parts = []
        
        if metadata.category:
            parts.append(f"[נושא: {metadata.category}]")
        if metadata.subcategory:
            parts.append(f"[תת-נושא: {metadata.subcategory}]")
        if metadata.service_name:
            parts.append(f"[שירות: {metadata.service_name}]")
        if metadata.hmo_name:
            parts.append(f"[קופת חולים: {metadata.hmo_name}]")
        if metadata.insurance_level:
            parts.append(f"[רמת ביטוח: {metadata.insurance_level}]")
            
        parts.append(text)
        return " ".join(parts)
    
    def extract_table_data(self, table_elem, current_heading: str, current_subheading: str) -> List[Dict[str, Any]]:
        chunks = []
        rows = table_elem.find_all("tr")
        
        if not rows or len(rows) < 2:
            return chunks
            
        headers = [self.clean_text(th.get_text()) for th in rows[0].find_all(["td", "th"])]
        
        if len(headers) < 2:
            return chunks
            
        service_col = headers[0]  
        hmo_cols = headers[1:]   
        
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) != len(headers):
                continue
                
            service_name = self.clean_text(cells[0].get_text())
            
            for i, hmo_name in enumerate(hmo_cols, 1):
                if i >= len(cells):
                    continue
                    
                cell_html = str(cells[i])
                insurance_levels = self.extract_insurance_info(cell_html)
                
                for level, details in insurance_levels.items():
                    if details and len(details) >= self.config.CHUNK_MIN_LEN:
                        metadata = ChunkMetadata(
                            category=current_heading,
                            subcategory=current_subheading,
                            service_name=service_name,
                            hmo_name=hmo_name,
                            insurance_level=level,
                            chunk_type="table_cell"
                        )
                        
                        chunk_text = self.create_structured_chunk(details, metadata)
                        chunks.append({
                            "text": chunk_text,
                            "metadata": metadata.__dict__
                        })
        
        return chunks
    
    def extract_contact_info(self, ul_elem, current_heading: str) -> List[Dict[str, Any]]:
        chunks = []
        
        for li in ul_elem.find_all("li"):
            li_text = self.clean_text(li.get_text())
            if len(li_text) >= self.config.CHUNK_MIN_LEN:
                hmo_name = ""
                if "מכבי" in li_text:
                    hmo_name = "מכבי"
                elif "מאוחדת" in li_text:
                    hmo_name = "מאוחדת"
                elif "כללית" in li_text:
                    hmo_name = "כללית"
                
                metadata = ChunkMetadata(
                    category=current_heading,
                    subcategory="פרטי יצירת קשר",
                    hmo_name=hmo_name,
                    chunk_type="contact_info"
                )
                
                chunk_text = self.create_structured_chunk(li_text, metadata)
                chunks.append({
                    "text": chunk_text,
                    "metadata": metadata.__dict__
                })
        
        return chunks
    
    def extract_chunks_with_enhanced_context(self, file_path: str, filename: str = None) -> List[Dict[str, Any]]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
        except Exception as e:
            logger.error(f"שגיאה בקריאת קובץ {file_path}: {e}")
            return []

        chunks = []
        current_heading = ""
        current_subheading = ""

        for elem in soup.find_all(["h2", "h3", "h4", "p", "ul", "ol", "table"]):
            try:
                if elem.name == "h2":
                    current_heading = self.clean_text(elem.get_text())
                    current_subheading = ""
                    
                elif elem.name in ["h3", "h4"]:
                    current_subheading = self.clean_text(elem.get_text())

                elif elem.name == "p":
                    text = self.clean_text(elem.get_text())
                    if len(text) >= self.config.CHUNK_MIN_LEN:
                        metadata = ChunkMetadata(
                            category=current_heading,
                            subcategory=current_subheading,
                            source_file=filename or "",
                            chunk_type="paragraph"
                        )
                        
                        chunk_text = self.create_structured_chunk(text, metadata)
                        chunks.append({
                            "text": chunk_text,
                            "metadata": metadata.__dict__
                        })

                elif elem.name in ["ul", "ol"]:
                    parent_h3 = elem.find_previous("h3")
                    if parent_h3 and any(keyword in parent_h3.get_text() for keyword in ["טלפון", "פרטים", "יצירת קשר"]):
                        chunks.extend(self.extract_contact_info(elem, current_heading))
                    else:
                        for li in elem.find_all("li"):
                            li_text = self.clean_text(li.get_text())
                            if len(li_text) >= self.config.CHUNK_MIN_LEN:
                                metadata = ChunkMetadata(
                                    category=current_heading,
                                    subcategory=current_subheading,
                                    source_file=filename or "",
                                    chunk_type="list_item"
                                )
                                
                                chunk_text = self.create_structured_chunk(li_text, metadata)
                                chunks.append({
                                    "text": chunk_text,
                                    "metadata": metadata.__dict__
                                })

                elif elem.name == "table":
                    table_chunks = self.extract_table_data(elem, current_heading, current_subheading)
                    for chunk in table_chunks:
                        chunk["metadata"]["source_file"] = filename or ""
                    chunks.extend(table_chunks)
                    
            except Exception as e:
                logger.warning(f"שגיאה בעיבוד אלמנט {elem.name} בקובץ {filename}: {e}")
                continue

        logger.info(f"חולצו {len(chunks)} קטעים מקובץ {filename}")
        return chunks

    def process_embeddings_in_batches(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        
        for i in range(0, len(chunks), self.config.BATCH_SIZE):
            batch = chunks[i:i + self.config.BATCH_SIZE]
            logger.info(f"מעבד batch {i//self.config.BATCH_SIZE + 1}/{(len(chunks)-1)//self.config.BATCH_SIZE + 1}")
            
            for item in batch:
                try:
                    embedding = get_embedding(item["text"])
                    result.append({
                        "text": item["text"],
                        "embedding": embedding,
                        "metadata": item.get("metadata", {})
                    })
                except Exception as e:
                    logger.error(f"שגיאה ביצירת embedding: {e}")
                    
        return result

    def generate_vectors(self) -> None:
        if not os.path.exists(self.config.HTML_DIR):
            logger.error(f"תיקייה {self.config.HTML_DIR} לא קיימת")
            return
            
        all_chunks = []
        total_files = 0
        
        html_files = [f for f in os.listdir(self.config.HTML_DIR) if f.endswith(".html")]
        logger.info(f"נמצאו {len(html_files)} קבצי HTML")
        
        for filename in html_files:
            full_path = os.path.join(self.config.HTML_DIR, filename)
            extracted = self.extract_chunks_with_enhanced_context(full_path, filename)
            
            if extracted:
                all_chunks.extend(extracted)
                total_files += 1
            else:
                logger.warning(f"לא חולצו נתונים מקובץ {filename}")

        if not all_chunks:
            logger.error("לא נמצאו נתונים לעיבוד")
            return
            
        logger.info(f"סה\"כ חולצו {len(all_chunks)} קטעים מ-{total_files} קבצים")
        
        logger.info("מתחיל יצירת embeddings...")
        result = self.process_embeddings_in_batches(all_chunks)
        
        os.makedirs(os.path.dirname(self.config.OUT_FILE), exist_ok=True)
        
        try:
            with open(self.config.OUT_FILE, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ הושלם בהצלחה: {len(result)} וקטורים נשמרו ל-{self.config.OUT_FILE}")
            
            self.print_statistics(result)
            
        except Exception as e:
            logger.error(f"שגיאה בשמירת הקובץ: {e}")

    def print_statistics(self, vectors: List[Dict[str, Any]]) -> None:
        """הדפסת סטטיסטיקות"""
        categories = {}
        hmos = {}
        chunk_types = {}
        
        for vector in vectors:
            metadata = vector.get("metadata", {})
            
            category = metadata.get("category", "לא מוגדר")
            categories[category] = categories.get(category, 0) + 1
            
            hmo = metadata.get("hmo_name", "לא מוגדר")
            hmos[hmo] = hmos.get(hmo, 0) + 1
            
            chunk_type = metadata.get("chunk_type", "לא מוגדר")
            chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1
        
        print("\n📊 סטטיסטיקות:")
        print(f"סה\"כ וקטורים: {len(vectors)}")
        
        print("\n🏥 לפי קטגוריות:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cat}: {count}")
            
        print("\n🏢 לפי קופות חולים:")
        for hmo, count in sorted(hmos.items(), key=lambda x: x[1], reverse=True):
            print(f"  {hmo}: {count}")
            
        print("\n📝 לפי סוג קטע:")
        for chunk_type, count in sorted(chunk_types.items(), key=lambda x: x[1], reverse=True):
            print(f"  {chunk_type}: {count}")

def main():
    config = Config()
    generator = ImprovedVectorGenerator(config)
    generator.generate_vectors()

if __name__ == "__main__":
    main()