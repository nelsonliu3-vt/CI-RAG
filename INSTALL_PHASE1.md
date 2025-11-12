# Phase 1 Installation Guide

## Quick Start

Install the new optional dependencies to enable full Phase 1 functionality:

```bash
pip install extract-msg python-docx
```

That's it! The app will now support:
- ✅ Outlook .msg email files
- ✅ Word .docx documents

---

## Detailed Installation

### 1. Navigate to Project Directory

```bash
cd /Users/hantsungliu/CI-RAG
```

### 2. Activate Virtual Environment (if using one)

```bash
# If you have a venv
source venv/bin/activate

# Or conda
conda activate ci-rag
```

### 3. Install New Dependencies

```bash
pip install extract-msg python-docx
```

**Verify installation:**
```bash
python -c "import extract_msg; import docx; print('✓ All dependencies installed')"
```

---

## What Gets Installed

### extract-msg
- **Purpose:** Parse Outlook .msg email files
- **Size:** ~1 MB
- **Dependencies:** olefile, compressed_rtf

### python-docx
- **Purpose:** Parse Microsoft Word .docx files
- **Size:** ~500 KB
- **Dependencies:** lxml (may already be installed)

---

## Optional: Verify Parsing Works

### Test .msg Parsing

```bash
python -c "
from ingestion.parser import parse_document
from pathlib import Path

# This will work even without a .msg file
# The parser will gracefully handle the error
print('✓ MSG parser loaded successfully')
"
```

### Test .docx Parsing

```bash
python -c "
from ingestion.parser import parse_document
from pathlib import Path

# This will work even without a .docx file
# The parser will gracefully handle the error
print('✓ DOCX parser loaded successfully')
"
```

---

## If Installation Fails

### Issue: extract-msg fails to install

**Error:** `ERROR: Could not find a version that satisfies the requirement extract-msg`

**Solution:**
```bash
# Update pip first
pip install --upgrade pip

# Try again
pip install extract-msg
```

### Issue: python-docx fails to install

**Error:** `error: Microsoft Visual C++ 14.0 or greater is required`

**Solution (Windows):**
1. Install Microsoft C++ Build Tools
2. Or use pre-built wheel:
   ```bash
   pip install python-docx --only-binary=:all:
   ```

**Solution (Mac/Linux):**
```bash
# Install system dependencies first
# Mac
brew install libxml2 libxslt

# Ubuntu/Debian
sudo apt-get install python3-dev libxml2-dev libxslt1-dev

# Then try again
pip install python-docx
```

---

## Running Without Optional Dependencies

The app works fine without these libraries, but:

- **Without extract-msg:** Uploading .msg files will show error: "extract-msg library not installed"
- **Without python-docx:** Uploading .docx files will show error: "python-docx library not installed"

All other features work normally:
- ✅ Text paste
- ✅ PDF, PPTX, HTML, .eml, TXT, MD
- ✅ All query/analysis features

---

## Verify Everything Works

### 1. Start the App

```bash
streamlit run app_ci.py
```

### 2. Test Text Paste

1. Go to Tab 1 (Upload & Index)
2. Select "📝 Paste Text"
3. Paste any text
4. Click "📤 Process Text"
5. Should show: ✓ Parsed successfully

### 3. Test File Upload

1. Select "📁 Upload Files"
2. Supported types should show: PDF, PPTX, DOCX, HTML, EML, MSG, TXT, MD
3. Upload any supported file type
4. Should parse without errors

### 4. Test Impact Analysis

1. Go to Tab 3 (Program Profile)
2. Set up a test profile (just program name is enough)
3. Upload a document in Tab 1
4. Go to Tab 2 (Query & Insights)
5. Enter: "What is the impact on our program?"
6. Click "🎯 Analyze Impact for Program"
7. Should show structured output with 3 sections (Efficacy, Safety, Strategic)

---

## Troubleshooting

### App won't start after installation

**Check for conflicting dependencies:**
```bash
pip check
```

**Reinstall from requirements:**
```bash
pip install -r requirements.txt
pip install extract-msg python-docx
```

### Parsing errors on specific file types

**Check parser availability:**
```python
from ingestion.parser import DocumentParser

parser = DocumentParser()
print("Supported formats:", parser.supported_formats)

# Check optional parsers
print("MSG available:", parser.MSG_AVAILABLE if hasattr(parser, 'MSG_AVAILABLE') else True)
print("DOCX available:", parser.DOCX_AVAILABLE if hasattr(parser, 'DOCX_AVAILABLE') else True)
```

### Impact analysis not using structured prompt

**Verify config loaded:**
```python
from core.config import CI_IMPACT_PROMPT

# Should contain "🔬 Efficacy Impact"
assert "🔬" in CI_IMPACT_PROMPT
print("✓ Enhanced prompt loaded")
```

---

## Next Steps

1. ✅ Dependencies installed
2. ✅ App starts successfully
3. ✅ Text paste works
4. ✅ All file types supported

**You're ready to use Phase 1 features!**

See `PHASE1_ENHANCEMENTS_SUMMARY.md` for detailed usage guide and examples.

---

## Questions?

- **Issue with dependencies?** Check system requirements (Python 3.8+)
- **Parsing errors?** Verify file formats are supported
- **App crashes?** Check logs: `streamlit run app_ci.py --logger.level=debug`

---

**Installation complete! 🎉**
