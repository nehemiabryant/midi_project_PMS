import fitz # PyMuPDF
import io

def generate_pdf_thumbnail(pdf_bytes: bytes) -> bytes:
    """
    Takes raw PDF bytes, extracts the first page, and returns JPEG bytes.
    Everything happens in server memory for maximum speed.
    """
    try:
        # Open the PDF directly from memory
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        if len(doc) == 0:
            return None
            
        # Grab the very first page
        page = doc.load_page(0)
        
        # Scale it down so we don't save massive images
        # 0.5 means 50% of original resolution (perfect for thumbnails)
        mat = fitz.Matrix(0.5, 0.5) 
        
        # Render the page to a Pixmap (image)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert to raw JPEG bytes
        return pix.tobytes("jpeg")
        
    except Exception as e:
        print(f"Thumbnail Generation Failed: {str(e)}")
        return None