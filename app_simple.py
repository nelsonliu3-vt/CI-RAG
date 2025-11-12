"""
CI-RAG Simplified Application
Upload competitor documents and analyze competitive impact
"""

import streamlit as st
import sys
from pathlib import Path
import uuid
from datetime import datetime
import traceback
import hashlib
import re

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Backend imports (keep all existing functionality)
from ingestion.parser import parse_document
from ingestion.detector import detect_document_type
from memory.simple_memory import get_memory
from retrieval.vector_store import get_vector_store
from retrieval.hybrid_search import get_hybrid_search
from retrieval.reranker import get_reranker
from generation.analyst import get_analyst
from core.config import CHUNK_SIZE
from core.input_sanitizer import get_sanitizer
from core.program_profile import get_program_profile
from ingestion.entity_extractor import get_entity_extractor
from memory.entity_store import get_entity_store

# ============================================================================
# HELPER FUNCTIONS FOR PRECISION-FIRST RETRIEVAL
# ============================================================================

def build_retrieval_query(program_name: str) -> str:
    """
    Build a crisp retrieval query by appending clinical keywords to program name.
    This creates a focused search query that targets relevant clinical data.
    """
    keywords = [
        "efficacy", "ORR", "PFS", "OS", "DOR",
        "safety", "adverse events", "AEs",
        "trial", "phase", "randomized", "endpoint",
        "regulatory", "FDA", "accelerated approval"
    ]
    return f"{program_name} {' '.join(keywords)}"

# Boilerplate patterns to filter out
_BOILERPLATE_PATTERNS = [
    r"forward[-\s]looking\s+statements?",
    r"safe\s+harbor",
    r"table\s+of\s+contents?",
    r"non[-\s]gaap",
    r"cautionary\s+statement"
]

def looks_like_boilerplate(text: str) -> bool:
    """
    Detect if text chunk is boilerplate (forward-looking statements, disclaimers, etc.)
    Returns True if text matches any boilerplate pattern.
    """
    text_lower = text.lower()
    for pattern in _BOILERPLATE_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False

def any_alias(text: str, names: list) -> bool:
    """
    Check if text contains any of the program names/aliases.
    Case-insensitive substring matching.
    """
    if not names:
        return False
    text_lower = text.lower()
    return any(name.lower() in text_lower for name in names if name)

def alias_hits(text: str, names: list) -> int:
    """
    Count how many times any alias appears in text.
    Used to prioritize chunks with more program mentions.
    """
    if not names:
        return 0
    text_lower = text.lower()
    return sum(text_lower.count(name.lower()) for name in names if name)

# ============================================================================
# PAGE CONFIGURATION & SESSION STATE
# ============================================================================

st.set_page_config(
    page_title="CI-RAG: Competitive Intelligence",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.documents = []

# ============================================================================
# HEADER
# ============================================================================

st.title("🔍 CI-RAG: Competitive Intelligence Analysis")
st.markdown("*Upload competitor documents • Enter your program • Get impact insights*")
st.markdown("---")

# ============================================================================
# SECTION 1: PROGRAM NAME INPUT
# ============================================================================

st.markdown("### 1️⃣ Enter Your Program Name")
program_name = st.text_input(
    "Program Name",
    placeholder="e.g., CLDN18.2 ADC in Gastric Cancer",
    help="Required for impact analysis",
    key="program_name_input"
)

aliases_raw = st.text_input(
    "Program aliases (comma-separated)",
    placeholder="e.g., datopotamab deruxtecan, Dato-DXd, DS-1062",
    help="Alternative names, codes, or abbreviations for your program",
    key="aliases_input"
)
ALIASES = [a.strip() for a in aliases_raw.split(",") if a.strip()]

if program_name:
    # Store program name in program profile
    profile_manager = get_program_profile()
    profile_manager.save_profile(
        program_name=program_name,
        indication=None,
        stage=None,
        target=None,
        differentiators=None,
        our_orr=None,
        our_pfs=None,
        our_safety_profile=None
    )
    alias_text = f" + {len(ALIASES)} aliases" if ALIASES else ""
    st.success(f"✓ Program: **{program_name}**{alias_text}")

st.markdown("---")

# ============================================================================
# SECTION 2: UPLOAD DOCUMENTS
# ============================================================================

st.markdown("### 2️⃣ Upload Competitor Documents")
st.caption("Supported: PDF, PPTX, DOCX, HTML, EML (Max 50MB per file)")

# Choose input method
input_method = st.radio(
    "Input Method",
    ["📁 Upload Files", "📝 Paste Text"],
    horizontal=True,
    help="Upload files or paste email/text content directly"
)

MAX_FILE_SIZE_MB = 50

# Clear all existing documents to start fresh
def clear_all_documents():
    """Clear vector store and memory to start fresh"""
    try:
        # Clear vector store (Qdrant)
        vector_store = get_vector_store()
        vector_store.client.delete_collection("ci_documents")
        vector_store._ensure_collection()  # Recreate empty collection

        # Clear BM25 index
        hybrid_search = get_hybrid_search()
        hybrid_search.bm25_index = None
        hybrid_search.doc_map = {}

        # Clear memory (SQLite)
        memory = get_memory()
        memory.cursor.execute("DELETE FROM documents")
        memory.cursor.execute("DELETE FROM queries")
        memory.conn.commit()

        st.success("✅ Cleared all previous documents - starting fresh!")
    except Exception as e:
        st.warning(f"Note: {str(e)}")

if input_method == "📁 Upload Files":
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=["pdf", "pptx", "docx", "html", "eml", "msg", "txt"],
        accept_multiple_files=True,
        help=f"Upload presentations, press releases, clinical trial results, etc.",
        key="file_uploader"
    )

    # Optional workspace reset
    reset_before_upload = st.checkbox(
        "Reset workspace before ingest",
        value=False,
        help="Clears all previously indexed docs. Leave unchecked to add to existing documents.",
        key="reset_upload"
    )
else:
    uploaded_files = None
    # Text paste interface
    st.subheader("Paste Email or Text Content")

    pasted_text = st.text_area(
        "Paste your content here",
        height=300,
        placeholder="Paste email body, press release, or any text content...\n\nExample:\nFrom: competitor@pharma.com\nSubject: Phase 3 Results\n\nCompany X announced positive...",
        help="Paste forwarded emails, press releases, or any text content",
        key="paste_text_area"
    )

    col1, col2 = st.columns([3, 1])
    with col1:
        paste_title = st.text_input(
            "Document Title (optional)",
            placeholder="e.g., Competitor X Phase 3 Results",
            help="Give this document a memorable name",
            key="paste_title_input"
        )
    with col2:
        st.markdown("")  # Spacer
        process_paste = st.button("📤 Process Text", type="primary", disabled=not pasted_text)

    # Optional workspace reset
    reset_before = st.checkbox(
        "Reset workspace before ingest",
        value=False,
        help="Clears all previously indexed docs. Leave unchecked to add to existing documents."
    )

# Process pasted text
if input_method == "📝 Paste Text" and 'process_paste' in locals() and process_paste and pasted_text:
    # Optionally clear all old documents first
    if reset_before:
        clear_all_documents()

    st.markdown("#### Processing Pasted Text...")

    try:
        # Sanitize pasted text
        sanitizer = get_sanitizer()
        sanitized_text = sanitizer.sanitize_query(pasted_text, max_length=50000, strict=False)

        # Generate filename
        if paste_title:
            safe_title = sanitizer.sanitize_filename(paste_title)
            filename = f"{safe_title}.txt"
        else:
            filename = f"pasted_text_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        # Save temporarily
        upload_dir = Path("data/uploads").resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        temp_path = upload_dir / filename

        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(sanitized_text)

        st.info(f"Created temporary file: {filename}")

        # Parse as text document
        with st.spinner("Parsing..."):
            parsed = parse_document(temp_path)

        st.success(f"✓ Parsed: {len(parsed['text'])} characters")

        # Detect type
        with st.spinner("Detecting type..."):
            detected = detect_document_type(parsed)

        st.caption(f"Type: {detected['detected_type'].replace('_', ' ').title()}")

        # Index the pasted text
        with st.spinner("Indexing..."):
            # Generate document ID
            doc_id = f"doc_{uuid.uuid4().hex[:8]}"

            # Chunk text
            text = parsed['text']
            chunk_size_chars = CHUNK_SIZE * 4
            chunks = []
            for i in range(0, len(text), chunk_size_chars):
                chunk = text[i:i + chunk_size_chars]
                if chunk.strip():
                    chunks.append(chunk)

            if len(chunks) == 0:
                st.warning("⚠️ No text content found")
            else:
                # Add to vector store
                vector_store = get_vector_store()
                metadata = {
                    "detected_type": detected['detected_type'],
                    "source": detected.get('source', 'pasted_text'),
                    "topics": detected.get('topics', []),
                    "file_name": filename,
                    "num_pages": 1,
                    "input_method": "paste"
                }

                chunk_ids = vector_store.add_documents(chunks, doc_id, metadata)

                # Add to BM25 index
                hybrid_search = get_hybrid_search()
                bm25_docs = [
                    {
                        "id": chunk_id,
                        "text": chunk,
                        "metadata": metadata
                    }
                    for chunk_id, chunk in zip(chunk_ids, chunks)
                ]
                hybrid_search.index_documents(bm25_docs)

                # Add to memory
                memory = get_memory()
                memory.add_document(
                    doc_id=doc_id,
                    filename=filename,
                    detected_type=detected['detected_type'],
                    source=detected.get('source', 'pasted_text'),
                    topics=detected.get('topics', []),
                    file_size=len(sanitized_text),
                    num_pages=1,
                    date_in_doc=detected.get('date')
                )
                memory.mark_indexed(doc_id)

                st.success(f"✓ Indexed: **{filename}** ({len(chunks)} chunks)")

    except Exception as e:
        st.error(f"❌ Error processing pasted text: {str(e)}")

    st.markdown("---")

    # Show database status
    memory = get_memory()
    stats = memory.get_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Documents", stats.get("total_documents", 0))
    with col2:
        st.metric("Indexed", stats.get("indexed_documents", 0))
    with col3:
        st.metric("Ready", "✓" if stats.get("indexed_documents", 0) > 0 else "⏳")

if uploaded_files:
    # Optionally clear all old documents first
    if reset_before_upload:
        clear_all_documents()

    st.markdown("#### Processing Files...")

    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    for idx, uploaded_file in enumerate(uploaded_files):
        progress = (idx + 1) / len(uploaded_files)
        progress_bar.progress(progress)
        status_placeholder.info(f"Processing {idx + 1}/{len(uploaded_files)}: {uploaded_file.name}")

        try:
            # Validate file size
            if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                st.error(f"❌ {uploaded_file.name}: File too large ({uploaded_file.size / (1024*1024):.1f}MB, max {MAX_FILE_SIZE_MB}MB)")
                continue

            if uploaded_file.size == 0:
                st.error(f"❌ {uploaded_file.name}: File is empty")
                continue

            # Sanitize filename
            sanitizer = get_sanitizer()
            safe_filename = sanitizer.sanitize_filename(uploaded_file.name)
            unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"

            # Save file temporarily
            upload_dir = Path("data/uploads").resolve()
            upload_dir.mkdir(parents=True, exist_ok=True)
            temp_path = upload_dir / unique_filename

            # Path traversal protection
            if not str(temp_path.resolve()).startswith(str(upload_dir)):
                raise ValueError("Invalid file path: potential path traversal attack")

            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # Calculate content hash for doc ID
            with open(temp_path, "rb") as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()[:16]
            doc_id = f"doc_{file_hash}"

            # Parse document
            parsed = parse_document(temp_path)

            # Detect type
            detected = detect_document_type(parsed)

            # Chunk text
            text = parsed['text']
            chunk_size_chars = CHUNK_SIZE * 4
            chunks = []
            for i in range(0, len(text), chunk_size_chars):
                chunk = text[i:i + chunk_size_chars]
                if chunk.strip():
                    chunks.append(chunk)

            if len(chunks) == 0:
                st.warning(f"⚠️ {uploaded_file.name}: No text content found")
                continue

            # Add to vector store
            vector_store = get_vector_store()
            metadata = {
                "detected_type": detected['detected_type'],
                "source": detected.get('source', ''),
                "topics": detected.get('topics', []),
                "file_name": uploaded_file.name,
                "num_pages": parsed['num_pages'],
                "file_hash": file_hash
            }

            chunk_ids = vector_store.add_documents(chunks, doc_id, metadata)

            # Add to BM25 index
            hybrid_search = get_hybrid_search()
            bm25_docs = [
                {
                    "id": chunk_id,
                    "text": chunk,
                    "metadata": metadata
                }
                for chunk_id, chunk in zip(chunk_ids, chunks)
            ]
            hybrid_search.index_documents(bm25_docs)

            # Add to memory
            memory = get_memory()
            memory.add_document(
                doc_id=doc_id,
                filename=uploaded_file.name,
                detected_type=detected['detected_type'],
                source=detected.get('source', ''),
                topics=detected.get('topics', []),
                file_size=uploaded_file.size,
                num_pages=parsed['num_pages'],
                date_in_doc=detected.get('date')
            )
            memory.mark_indexed(doc_id)

            # Extract entities (silently in background)
            try:
                extractor = get_entity_extractor()
                entity_store = get_entity_store()
                entities = extractor.extract(parsed['text'])

                # Store entities
                for company in entities.get('companies', []):
                    entity_store.add_company(
                        company['name'],
                        aliases=company.get('aliases', []),
                        role=company.get('role', 'competitor')
                    )

                for asset in entities.get('assets', []):
                    entity_store.add_asset(
                        asset['name'],
                        asset.get('company', 'Unknown'),
                        mechanism=asset.get('mechanism'),
                        indication=asset.get('indication'),
                        phase=asset.get('phase')
                    )

                for trial in entities.get('trials', []):
                    entity_store.add_trial(
                        trial['trial_id'],
                        trial.get('asset', 'Unknown'),
                        trial.get('company', 'Unknown'),
                        phase=trial.get('phase'),
                        indication=trial.get('indication'),
                        status=trial.get('status'),
                        n_patients=trial.get('n_patients')
                    )
            except Exception as e:
                # Entity extraction is optional, don't fail the upload
                pass

            st.success(f"✓ Indexed: **{uploaded_file.name}** ({len(chunks)} chunks)")

        except Exception as e:
            st.error(f"❌ {uploaded_file.name}: {str(e)}")

    progress_bar.progress(1.0)
    status_placeholder.success("✅ All files processed!")

    st.markdown("---")

    # Show database status
    memory = get_memory()
    stats = memory.get_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Documents", stats.get("total_documents", 0))
    with col2:
        st.metric("Indexed", stats.get("indexed_documents", 0))
    with col3:
        st.metric("Ready", "✓" if stats.get("indexed_documents", 0) > 0 else "⏳")

st.markdown("---")

# ============================================================================
# SECTION 3: ANALYZE IMPACT
# ============================================================================

st.markdown("### 3️⃣ Analyze Competitive Impact")

# Check if documents are indexed
memory = get_memory()
stats = memory.get_stats()
docs_ready = stats.get("indexed_documents", 0) > 0

# Auto-generate comprehensive query based on program name
if program_name:
    auto_query = f"""Analyze the competitive landscape for {program_name}:

1. **Efficacy Data**: What are the key efficacy outcomes (ORR, PFS, OS, DOR) reported in the documents? How do they compare?

2. **Safety Profile**: What are the safety findings (Grade ≥3 AEs, discontinuation rates, most common adverse events)? What are the key safety differentiators?

3. **Clinical & Regulatory**: What are the clinical development stages, trial designs, and regulatory implications mentioned? What are the competitive differentiators?

4. **Strategic Implications**: What are the key takeaways and strategic considerations for our program?

Please provide a comprehensive analysis based on all available documents."""
else:
    auto_query = ""

st.info(f"💡 **Auto-Analysis**: Will look for mentions of **{program_name if program_name else '[Your Program]'}** and related clinical signals.")

# Advanced retrieval controls
with st.expander("⚙️ Advanced retrieval", expanded=False):
    st.caption("Fine-tune retrieval precision and recall")
    topk_pool = st.slider(
        "Candidate pool size",
        min_value=10,
        max_value=100,
        value=70,
        step=5,
        help="Number of initial candidates to retrieve before filtering"
    )
    min_rrf = st.slider(
        "Min relevance score",
        min_value=0.0,
        max_value=1.0,
        value=0.04,
        step=0.01,
        help="Minimum RRF score threshold (higher = more precise)"
    )
    strict_program_match = st.checkbox(
        "Require program name in chunk text",
        value=False,
        help="Only include chunks that mention the program name or aliases"
    )
    max_contexts = st.slider(
        "Max contexts to send to model",
        min_value=3,
        max_value=10,
        value=6,
        step=1,
        help="Maximum number of context chunks for the LLM"
    )

# Analyze button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    analyze_clicked = st.button(
        "🎯 Analyze Competitive Impact for My Program",
        type="primary",
        disabled=not program_name or not docs_ready,
        use_container_width=True,
        help="Automatically analyze competitive impact" if program_name and docs_ready else "Upload documents and enter program name first"
    )

# ============================================================================
# ANALYSIS EXECUTION & RESULTS DISPLAY
# ============================================================================

if analyze_clicked:
    try:
        with st.spinner("🔍 Searching documents..."):
            # Sanitize the comprehensive query
            sanitizer = get_sanitizer()
            sanitized_query = sanitizer.sanitize_query(auto_query, max_length=2000, strict=False)

            # Build crisp retrieval query with clinical keywords
            search_query = build_retrieval_query(program_name) if program_name else sanitized_query

            # Retrieve larger candidate pool
            hybrid_search = get_hybrid_search()
            results = hybrid_search.hybrid_search(search_query, top_k=topk_pool)

            # Build program names list (program name + aliases)
            names = [program_name] + ALIASES if program_name else ALIASES

            # Filter with alias-aware matching
            if strict_program_match and names:
                results = [r for r in results if any_alias(r.get("text", ""), names)]

            # Filter by relevance threshold
            results = [r for r in results if r.get("rrf_score", 0) >= min_rrf]

            # Filter boilerplate
            results = [r for r in results if not looks_like_boilerplate(r.get("text", ""))]

            # Sort by alias hit count (prioritize chunks with more mentions)
            if names:
                results.sort(key=lambda r: alias_hits(r.get("text", ""), names), reverse=True)

        # Check results after spinner closes
        if not results:
            st.warning("⚠️ No contexts mention your program or aliases. Try:")
            st.markdown("- Lower the **Min relevance score** slider")
            st.markdown("- Uncheck **Require program name in chunk text**")
            st.markdown("- Add more **aliases** for your program")
            st.markdown("- Increase **Candidate pool size**")
            st.markdown("- Upload docs that specifically mention your program")
            st.stop()

        st.info(f"Found {len(results)} high-confidence document sections")

        # Rerank with short query (just program name for precision)
        with st.spinner("📊 Analyzing relevance..."):
            reranker = get_reranker()
            rerank_query = program_name or search_query
            results = reranker.rerank(rerank_query, results, top_k=min(max_contexts, len(results)))

        # Debug panel showing retrieval parameters
        with st.expander("🔍 Why these sources", expanded=False):
            st.code(
                f"retrieval_query = {search_query}\n"
                f"rerank_query = {rerank_query}\n"
                f"program_names = {names}\n"
                f"min_rrf = {min_rrf}\n"
                f"strict_match = {strict_program_match}\n"
                f"contexts_used = {min(max_contexts, len(results))}"
            )

        if results:
            # Generate answer
            with st.spinner("💡 Generating analysis..."):
                analyst = get_analyst()

                # Basic answer
                if analyst.is_comparison_query(sanitized_query):
                    answer = analyst.generate_comparison(sanitized_query, results)
                else:
                    answer = analyst.generate_answer(sanitized_query, results)

            # Display Answer
            st.markdown("---")
            st.markdown("## 💡 Answer")
            st.markdown(answer)

            # Generate Program-Specific Impact Analysis
            st.markdown("---")
            st.markdown("## 🎯 Impact Analysis for Your Program")
            st.info(f"Analyzing implications for: **{program_name}**")

            with st.spinner("🔬 Generating program-specific impact analysis..."):
                # Get program context
                profile_manager = get_program_profile()
                program_context = profile_manager.format_profile_context()

                # Build impact analysis prompt
                sanitized_contexts = []
                for i, r in enumerate(results[:max_contexts]):
                    doc_text = str(r.get('text', ''))[:500]
                    doc_text = doc_text.replace('"""', '').replace("'''", '')
                    doc_text = ' '.join(doc_text.split())
                    sanitized_contexts.append(f"[{i+1}] {doc_text}")

                impact_prompt = f"""Based on the following competitive intelligence:

Query: {sanitized_query}

Context from documents:
{chr(10).join(sanitized_contexts)}

Current Program Profile:
{program_context}

Please provide a structured impact analysis with the following sections:

## 🔬 Efficacy Impact
How does this intelligence affect our efficacy positioning? Compare to our program's data if available.

## ⚠️ Safety Impact
What are the safety implications for our program? Any differentiation opportunities or concerns?

## 📋 Clinical & Regulatory Impact
Strategic implications for our clinical development or regulatory strategy.

## 💡 Strategic Recommendations
Concrete action items and strategic recommendations for our program team.

Be specific, data-driven, and actionable. Focus on competitive differentiation."""

                # Generate impact analysis
                impact_analysis = analyst.generate_answer(impact_prompt, results)

            # Display impact analysis
            st.markdown(impact_analysis)

            # Show sources
            st.markdown("---")
            with st.expander("📚 View Sources", expanded=False):
                st.markdown("### Retrieved Document Sections")
                for i, result in enumerate(results, 1):
                    st.markdown(f"**[{i}] {result.get('metadata', {}).get('file_name', 'Unknown')}**")
                    st.caption(f"Relevance Score: {result.get('rrf_score', 0):.3f}")
                    st.text(result['text'][:300] + "..." if len(result['text']) > 300 else result['text'])
                    st.markdown("---")

            # Simple feedback
            st.markdown("---")
            st.markdown("### 📝 Was this helpful?")
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if st.button("👍 Yes", key="feedback_yes"):
                    memory = get_memory()
                    memory.log_query(sanitized_query, f"{answer}\n\n{impact_analysis}", [r['id'] for r in results], feedback=1)
                    st.success("Thanks for your feedback!")
            with col2:
                if st.button("👎 No", key="feedback_no"):
                    memory = get_memory()
                    memory.log_query(sanitized_query, f"{answer}\n\n{impact_analysis}", [r['id'] for r in results], feedback=-1)
                    st.info("Thanks! We'll improve based on your feedback!")

    except Exception as e:
        st.error(f"❌ Error during analysis: {str(e)}")
        with st.expander("Debug Information"):
            st.code(traceback.format_exc())

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.caption("CI-RAG: Competitive Intelligence RAG System | Powered by AI")
