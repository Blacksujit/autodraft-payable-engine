"""__main__.py - CLI entry for autodraft pipeline."""
import sys
from autodraft.pipeline import run_folder

def main():
    doc_dir = sys.argv[1] if len(sys.argv) > 1 else "documents"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "output"
    print(f"Autodraft: {doc_dir} -> {out_dir}")
    run_folder(doc_dir, out_dir)

if __name__ == "__main__":
    main()
