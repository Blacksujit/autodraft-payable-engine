"""__main__.py - CLI entry for autodraft pipeline.

Usage:
  python -m autodraft <doc_dir> <out_dir>   batch-process a folder of PDFs
  python -m autodraft demo                 interactive demo (open + held-back)
"""
import sys
from autodraft.pipeline import run_folder

def main():
    args = sys.argv[1:]
    if args and args[0] == "demo":
        from autodraft.demo import main as demo_main
        try:
            sys.exit(demo_main(sys.argv[2:]))
        except SystemExit:
            raise
        except KeyboardInterrupt:
            sys.exit(130)
        except Exception as e:
            print(f"demo error: {e}")
            sys.exit(1)
    doc_dir = args[0] if args else "documents"
    out_dir = args[1] if len(args) > 1 else "output"
    print(f"Autodraft: {doc_dir} -> {out_dir}")
    run_folder(doc_dir, out_dir)

if __name__ == "__main__":
    main()
