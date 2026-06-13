import warnings

warnings.warn(
    "import_to_wordpress.py is deprecated. Use 'md2wp import' instead.",
    DeprecationWarning,
    stacklevel=1,
)

from md2wp.cli import main

if __name__ == "__main__":
    main()
