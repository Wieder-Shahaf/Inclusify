import sys
import os
import tempfile
from docling.document_converter import DocumentConverter

def main():
    # Attempt to load a default PDF or create a small markdown file to test Docling
    ext = ".md"
    content = b"# Test Title\n\nBy John Doe\n\nThis is a test."
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    try:
        converter = DocumentConverter()
        result = converter.convert(temp_path)
        print("DIR result.document:")
        print(dir(result.document))
        
        # Check what metadata attributes exist
        print("\nHas meta?", hasattr(result.document, "meta") or None)
        print("Has properties?", hasattr(result.document, "properties") or None)
        print("Has core_metadata?", hasattr(result.document, "core_metadata") or None)
        print("Has doc_info?", hasattr(result.document, "doc_info") or None)
        
        for attr in ['meta', 'metadata', 'properties', 'core_metadata', 'doc_info', 'info']:
            if hasattr(result.document, attr):
                obj = getattr(result.document, attr)
                print(f"\nDIR result.document.{attr}:")
                print(dir(obj))
                print(f"Content: {obj}")

        # Let's also look at the origin attribute, sometimes metadata is there
        if hasattr(result.document, 'origin'):
            print("\nDIR result.document.origin:")
            print(dir(result.document.origin))

    finally:
        os.unlink(temp_path)

if __name__ == "__main__":
    main()
