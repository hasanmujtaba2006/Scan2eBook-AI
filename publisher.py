import os
from ebooklib import epub

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "Complete_Draft.txt")
OUTPUT_EPUB = os.path.join(SCRIPT_DIR, "My_Scanned_Book.epub")

def create_epub():
    print(f"📖 Reading text from: {INPUT_FILE}")
    
    # 1. Create the Book Object
    book = epub.EpubBook()
    
    # Set Metadata (You can make these dynamic later)
    book.set_identifier("id123456")
    book.set_title("My Scanned Project")
    book.set_language("en")
    book.add_author("Scan2Ebook User")

    # 2. Read your text file
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        full_text = f.read()

    # 3. Create Chapters
    # We split the text by the marker we added in the previous script
    # "--- Page X ---"
    raw_pages = full_text.split("--- Page")
    
    chapters = []
    
    # Skip the first split if it's empty
    for i, content in enumerate(raw_pages):
        if not content.strip(): continue
        
        # Clean up the page number header
        # The split removes "--- Page", so we fix the rest
        # content looks like: " 1 ---\n\nActual text..."
        parts = content.split("---", 1)
        if len(parts) < 2: continue
        
        page_num = parts[0].strip()
        body_text = parts[1].strip()
        
        # Create an EPUB Chapter
        chapter_title = f"Page {page_num}"
        chapter_file = f"page_{page_num}.xhtml"
        
        c = epub.EpubHtml(title=chapter_title, file_name=chapter_file, lang='en')
        
        # Add the text as HTML (Professional formatting)
        # We replace newlines with <br> or <p> tags
        formatted_body = body_text.replace("\n", "<br>")
        c.content = f"<h1>{chapter_title}</h1><p>{formatted_body}</p>"
        
        book.add_item(c)
        chapters.append(c)

    # 4. Define Table of Contents and Navigation
    book.toc = tuple(chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Add default CSS (Make it look pretty)
    style = 'h1 { text-align: center; color: #333; } p { font-family: sans-serif; }'
    nav_css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
    book.add_item(nav_css)

    # Order of content in the book
    book.spine = ['nav'] + chapters

    # 5. Write the File
    epub.write_epub(OUTPUT_EPUB, book, {})
    print(f"✅ Success! eBook saved to: {OUTPUT_EPUB}")

if __name__ == "__main__":
    create_epub()