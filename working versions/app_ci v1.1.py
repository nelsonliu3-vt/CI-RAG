"""
CI-RAG Streamlit Application
Competitive Intelligence RAG System MVP
"""

import streamlit as st
import sys
from pathlib import Path
import uuid
from datetime import datetime
import traceback
import json
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Logger
logger = logging.getLogger(__name__)

from ingestion.parser import parse_document
from ingestion.detector import detect_document_type
from memory.simple_memory import get_memory
from retrieval.vector_store import get_vector_store
from retrieval.hybrid_search import get_hybrid_search
from retrieval.reranker import get_reranker
from generation.analyst import get_analyst
from generation.citations import add_citation_links, create_bibliography
from generation.briefs import get_brief_generator
from core.config import CHUNK_SIZE, CHUNK_OVERLAP
from core.program_profile import get_program_profile
from scheduler import get_scheduler
from ingestion.sources.session_refresh import get_session_refresh

# Page config
st.set_page_config(
    page_title="CI-RAG - Competitive Intelligence",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.documents = []
    st.session_state.query_history = []
    st.session_state.auto_fetch_enabled = False
    st.session_state.scheduler = None

# Title
st.title("🔍 CI-RAG: Competitive Intelligence RAG")
st.markdown("*Auto-sort uploads • Smart retrieval • Cited insights*")

# Tabs
tab1, tab2, tab3 = st.tabs(["📁 Upload Documents", "💬 Query & Insights", "⚙️ Program Profile"])

# ============================================================================
# TAB 1: UPLOAD & INDEX
# ============================================================================

with tab1:
    st.header("Upload Documents")
    st.markdown("Upload publications, Endpoints News, ESMO Daily, CI emails, posters, CSRs, presentations")

    # Two input methods: File upload OR text paste
    input_method = st.radio(
        "Input Method",
        ["📁 Upload Files", "📝 Paste Text"],
        horizontal=True,
        help="Upload files or paste email/text content directly"
    )

    st.markdown("---")

    # File uploader with size limit
    MAX_FILE_SIZE_MB = 50

    if input_method == "📁 Upload Files":
        uploaded_files = st.file_uploader(
            "Drag and drop files here",
            type=["pdf", "pptx", "docx", "html", "eml", "msg", "txt", "md"],
            accept_multiple_files=True,
            help=f"Supported: PDF, PPTX, DOCX, HTML, EML, MSG, TXT, MD (Max {MAX_FILE_SIZE_MB}MB per file)"
        )
    else:
        uploaded_files = None
        # Text paste interface
        st.subheader("Paste Email or Text Content")

        pasted_text = st.text_area(
            "Paste your content here",
            height=300,
            placeholder="Paste email body, press release, or any text content...\n\nExample:\nFrom: competitor@pharma.com\nSubject: Phase 3 Results\n\nCompany X announced positive...",
            help="Paste forwarded emails, press releases, or any text content"
        )

        col1, col2 = st.columns([3, 1])
        with col1:
            paste_title = st.text_input(
                "Document Title (optional)",
                placeholder="e.g., Competitor X Phase 3 Results",
                help="Give this document a memorable name"
            )
        with col2:
            st.markdown("")  # Spacer
            process_paste = st.button("📤 Process Text", type="primary", disabled=not pasted_text)

    if uploaded_files:
        st.markdown("---")
        st.subheader(f"Processing {len(uploaded_files)} file(s)...")

        for uploaded_file in uploaded_files:
            with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                try:
                    # Validate file size
                    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                        st.error(f"❌ File too large: {uploaded_file.size / (1024*1024):.1f}MB (max {MAX_FILE_SIZE_MB}MB)")
                        continue

                    # Validate file has content
                    if uploaded_file.size == 0:
                        st.error(f"❌ File is empty")
                        continue

                    # Sanitize filename using centralized sanitizer
                    from core.input_sanitizer import get_sanitizer
                    sanitizer = get_sanitizer()
                    safe_filename = sanitizer.sanitize_filename(uploaded_file.name)

                    # Use UUID to ensure uniqueness and prevent overwrites
                    unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"

                    # Save file temporarily with secure path
                    upload_dir = Path("data/uploads").resolve()  # Resolve to absolute path
                    upload_dir.mkdir(parents=True, exist_ok=True)
                    temp_path = upload_dir / unique_filename

                    # Verify the final path is still within upload directory (defense in depth)
                    if not str(temp_path.resolve()).startswith(str(upload_dir)):
                        raise ValueError(f"Invalid file path: potential path traversal attack")

                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Parse document
                    with st.spinner("Parsing..."):
                        parsed = parse_document(temp_path)

                    st.success(f"✓ Parsed: {parsed['num_pages']} pages, {len(parsed['text'])} chars")

                    # Detect type
                    with st.spinner("Detecting type..."):
                        detected = detect_document_type(parsed)

                    # Show detection result (with HTML escaping for security)
                    import html
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        # Sanitize and display type
                        detected_type_safe = html.escape(detected['detected_type'].replace("_", " ").title())
                        st.metric("Type", detected_type_safe)
                    with col2:
                        st.metric("Confidence", f"{detected.get('confidence', 0):.0%}")
                    with col3:
                        # Sanitize source
                        source_safe = html.escape(str(detected.get('source', 'Unknown')))
                        st.metric("Source", source_safe)

                    if detected.get('topics'):
                        # Sanitize topics list
                        topics_safe = [html.escape(str(topic)) for topic in detected['topics'][:5]]
                        st.markdown(f"**Topics**: {', '.join(topics_safe)}")

                    # Oncology relevance check (NEW - Oncology Focus)
                    with st.spinner("Checking oncology relevance..."):
                        from core.relevance_scorer import check_oncology_relevance

                        oncology_check = check_oncology_relevance(parsed['text'])

                        oncology_score = oncology_check['oncology_score']
                        is_oncology = oncology_check['is_oncology']
                        matched_keywords = oncology_check['matched_keywords']

                        # Display oncology relevance (manual upload - show warning but allow)
                        if oncology_score >= 0.7:
                            st.success(f"✅ **Oncology-Focused:** {oncology_score}/1.0")
                            st.caption(f"Matched keywords: {', '.join(matched_keywords[:5])}")
                        elif oncology_score >= 0.3:
                            st.info(f"📊 **Oncology-Related:** {oncology_score}/1.0")
                            st.caption(f"Matched keywords: {', '.join(matched_keywords[:5])}")
                        else:
                            # NON-ONCOLOGY: Warn but allow manual upload
                            st.warning(f"⚠️ **NON-ONCOLOGY Document:** {oncology_score}/1.0")
                            st.info(
                                "This document may not be oncology-related. "
                                "You can still index it if needed, but it may not match your program focus."
                            )
                            if matched_keywords:
                                st.caption(f"Limited oncology keywords found: {', '.join(matched_keywords[:3])}")

                    # Index button (different styling based on oncology score)
                    button_type = "primary" if is_oncology else "secondary"
                    button_label = f"🚀 Index {uploaded_file.name}" if is_oncology else f"⚠️ Index {uploaded_file.name} (Non-Oncology)"

                    if st.button(button_label, key=f"index_{uploaded_file.name}", type=button_type):
                        with st.spinner("Indexing..."):
                            try:
                                # Generate document ID
                                doc_id = f"doc_{uuid.uuid4().hex[:8]}"

                                # Chunk text
                                text = parsed['text']
                                chunk_size_chars = CHUNK_SIZE * 4  # Rough token-to-char conversion
                                chunks = []
                                for i in range(0, len(text), chunk_size_chars):
                                    chunk = text[i:i + chunk_size_chars]
                                    if chunk.strip():
                                        chunks.append(chunk)

                                st.info(f"Created {len(chunks)} chunks")

                                # Add to vector store
                                vector_store = get_vector_store()
                                metadata = {
                                    "detected_type": detected['detected_type'],
                                    "source": detected.get('source', ''),
                                    "topics": detected.get('topics', []),
                                    "file_name": uploaded_file.name,
                                    "num_pages": parsed['num_pages']
                                }

                                chunk_ids = vector_store.add_documents(chunks, doc_id, metadata)
                                st.success(f"✓ Indexed {len(chunk_ids)} chunks in vector store")

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
                                st.success(f"✓ Built BM25 index")

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
                                st.success(f"✓ Saved to memory (ID: {doc_id})")

                                # Extract entities (NEW - Phase 2A)
                                try:
                                    with st.spinner("Extracting competitive intelligence entities..."):
                                        from ingestion.entity_extractor import get_entity_extractor
                                        from memory.entity_store import get_entity_store

                                        extractor = get_entity_extractor()
                                        entity_store = get_entity_store()

                                        # Extract entities from document
                                        entities = extractor.extract(parsed['text'])

                                        # Store entities
                                        updates_detected = []

                                        # Add companies
                                        for company in entities.get('companies', []):
                                            entity_store.add_company(
                                                company['name'],
                                                aliases=company.get('aliases', []),
                                                role=company.get('role', 'competitor')
                                            )

                                        # Add assets and trials
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
                                                trial.get('company', 'Unknown'),  # Need to infer
                                                phase=trial.get('phase'),
                                                indication=trial.get('indication'),
                                                status=trial.get('status'),
                                                n_patients=trial.get('n_patients')
                                            )

                                        # Add data points and detect updates
                                        for dp in entities.get('data_points', []):
                                            trial_id = dp.get('trial_id')

                                            # Issue #6: Validate trial_id exists
                                            if not trial_id:
                                                logger.warning("Data point missing trial_id, skipping")
                                                continue

                                            # Ensure trial exists first
                                            trial_info = next(
                                                (t for t in entities.get('trials', []) if t.get('trial_id') == trial_id),
                                                None
                                            )

                                            if not trial_info:
                                                # Create minimal trial entry
                                                logger.warning(f"Creating minimal trial entry for {trial_id}")
                                                entity_store.add_trial(
                                                    trial_id,
                                                    asset_name="Unknown",
                                                    company_name="Unknown",
                                                    phase=None,
                                                    indication=None,
                                                    status="unknown",
                                                    n_patients=None
                                                )

                                            # Issue #7: Validate and convert value to float
                                            raw_value = dp.get('value')

                                            try:
                                                if isinstance(raw_value, str):
                                                    # Strip units: "45%" -> 45, "6.2 months" -> 6.2
                                                    import re
                                                    cleaned = re.sub(r'[^\d\.\-]', '', raw_value)
                                                    if not cleaned:
                                                        logger.warning(f"Cannot extract numeric value from: {raw_value}")
                                                        continue
                                                    value = float(cleaned)
                                                elif isinstance(raw_value, (int, float)):
                                                    value = float(raw_value)
                                                else:
                                                    logger.warning(f"Invalid value type for {dp.get('metric_type')}: {raw_value}")
                                                    continue
                                            except (ValueError, TypeError) as e:
                                                logger.warning(f"Could not convert value to float: {raw_value} - {e}")
                                                continue

                                            # Check for update before adding
                                            update_info = entity_store.detect_update(
                                                trial_id,
                                                dp['metric_type'],
                                                value,  # Validated float
                                                entities['date_reported']
                                            )

                                            if update_info:
                                                updates_detected.append(update_info)

                                            # Add data point with validated value
                                            dp_id = entity_store.add_data_point(
                                                trial_id,
                                                dp['metric_type'],
                                                value,  # Validated float
                                                entities['date_reported'],
                                                doc_id=doc_id,
                                                confidence_interval=dp.get('confidence_interval'),
                                                n_patients=dp.get('n_patients'),
                                                unit=dp.get('unit'),
                                                data_maturity=dp.get('data_maturity'),
                                                subgroup=dp.get('subgroup', 'overall')
                                            )

                                            if dp_id is None:
                                                logger.warning(f"Failed to add data point for trial {trial_id}")

                                        # Calculate relevance score (NEW - Document Curation)
                                        relevance_data = {}
                                        try:
                                            from core.relevance_scorer import get_relevance_scorer
                                            from core.program_profile import get_program_profile
                                            from core.config import PRE_UPLOAD_RELEVANCE_WARNING_THRESHOLD

                                            # Get program profile
                                            program = get_program_profile()

                                            if program:
                                                scorer = get_relevance_scorer(program)

                                                # Score document
                                                doc_metadata = {
                                                    'detected_type': parsed.get('detected_type', 'other'),
                                                    'source': parsed.get('source'),
                                                    'topics': parsed.get('topics', [])
                                                }

                                                relevance_data = scorer.score_document(entities, doc_metadata)

                                                # Update document metadata with relevance info
                                                memory.update_metadata(doc_id, {
                                                    'relevance_score': relevance_data.get('relevance_score'),
                                                    'relevance_tags': relevance_data.get('relevance_tags', []),
                                                    'relevance_breakdown': relevance_data.get('relevance_breakdown', {}),
                                                    'matched_entities': {
                                                        'assets': relevance_data.get('matched_assets', []),
                                                        'companies': relevance_data.get('matched_companies', []),
                                                        'indications': relevance_data.get('matched_indications', [])
                                                    },
                                                    'curation_status': 'active',
                                                    'archived': 0
                                                })

                                                logger.info(f"Relevance score for {doc_id}: {relevance_data.get('relevance_score')}")

                                        except Exception as e:
                                            logger.warning(f"Relevance scoring failed (non-critical): {e}")
                                            relevance_data = {}

                                        # Show entity extraction results
                                        if entities['companies'] or entities['assets'] or entities['trials']:
                                            st.success(f"✓ Extracted: {len(entities['companies'])} companies, "
                                                      f"{len(entities['assets'])} assets, "
                                                      f"{len(entities['trials'])} trials, "
                                                      f"{len(entities['data_points'])} data points")

                                        # Show relevance score (NEW)
                                        if relevance_data:
                                            relevance_score = relevance_data.get('relevance_score', 0.0)
                                            relevance_tags = relevance_data.get('relevance_tags', [])
                                            matched_assets = relevance_data.get('matched_assets', [])
                                            matched_companies = relevance_data.get('matched_companies', [])

                                            # Display relevance score with color coding
                                            if relevance_score >= 0.7:
                                                st.success(f"🎯 **High Relevance:** {relevance_score}/1.0")
                                            elif relevance_score >= 0.4:
                                                st.info(f"📊 **Medium Relevance:** {relevance_score}/1.0")
                                            else:
                                                st.warning(f"⚠️ **Low Relevance:** {relevance_score}/1.0 - This document may not be relevant to your program.")

                                            # Show matched entities
                                            if matched_assets or matched_companies:
                                                match_info = []
                                                if matched_assets:
                                                    match_info.append(f"Assets: {', '.join(matched_assets[:3])}")
                                                if matched_companies:
                                                    match_info.append(f"Companies: {', '.join(matched_companies[:3])}")
                                                st.caption(f"Matched: {' | '.join(match_info)}")

                                            # Show relevance tags
                                            if relevance_tags:
                                                tag_emojis = {
                                                    'indication_match': '🎯',
                                                    'stage_match': '📊',
                                                    'target_match': '🔬',
                                                    'competitor': '🏢',
                                                    'regulatory_relevant': '📋',
                                                    'clinical_data': '💊'
                                                }
                                                tag_display = ' '.join([
                                                    f"{tag_emojis.get(tag, '•')} {tag.replace('_', ' ').title()}"
                                                    for tag in relevance_tags
                                                ])
                                                st.caption(f"Tags: {tag_display}")

                                        # Show update alerts
                                        if updates_detected:
                                            st.warning(f"⚠️ **UPDATE DETECTED:** This document updates previous data!")
                                            for update in updates_detected:
                                                st.info(
                                                    f"**{update['metric_type']}** for trial {update['trial_id']}: "
                                                    f"{update['old_value']} → {update['new_value']} "
                                                    f"({update['pct_change']:+.1f}%) "
                                                    f"[{update['old_date']} → {update['new_date']}]"
                                                )

                                except Exception as e:
                                    # Entity extraction is nice-to-have, don't fail the whole indexing
                                    st.warning(f"Entity extraction failed (non-critical): {str(e)}")
                                    logger.error(f"Entity extraction error: {e}")

                                st.balloons()

                            except Exception as e:
                                st.error(f"Error indexing: {str(e)}")
                                st.code(traceback.format_exc())

                except Exception as e:
                    st.error(f"Error processing file: {str(e)}")
                    st.code(traceback.format_exc())

    # Handle pasted text processing
    if input_method == "📝 Paste Text" and 'process_paste' in locals() and process_paste and pasted_text:
        st.markdown("---")
        st.subheader("Processing Pasted Text")

        with st.expander("📄 Pasted Content", expanded=True):
            try:
                # Sanitize pasted text
                from core.input_sanitizer import get_sanitizer
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

                # Show detection result
                import html
                col1, col2, col3 = st.columns(3)
                with col1:
                    detected_type_safe = html.escape(detected['detected_type'].replace("_", " ").title())
                    st.metric("Type", detected_type_safe)
                with col2:
                    st.metric("Confidence", f"{detected.get('confidence', 0):.0%}")
                with col3:
                    source_safe = html.escape(str(detected.get('source', 'Unknown')))
                    st.metric("Source", source_safe)

                if detected.get('topics'):
                    topics_safe = [html.escape(str(topic)) for topic in detected['topics'][:5]]
                    st.markdown(f"**Topics**: {', '.join(topics_safe)}")

                # Oncology relevance check (NEW - Oncology Focus)
                with st.spinner("Checking oncology relevance..."):
                    from core.relevance_scorer import check_oncology_relevance

                    oncology_check = check_oncology_relevance(parsed['text'])

                    oncology_score = oncology_check['oncology_score']
                    is_oncology = oncology_check['is_oncology']
                    matched_keywords = oncology_check['matched_keywords']

                    # Display oncology relevance (manual paste - show warning but allow)
                    if oncology_score >= 0.7:
                        st.success(f"✅ **Oncology-Focused:** {oncology_score}/1.0")
                        st.caption(f"Matched keywords: {', '.join(matched_keywords[:5])}")
                    elif oncology_score >= 0.3:
                        st.info(f"📊 **Oncology-Related:** {oncology_score}/1.0")
                        st.caption(f"Matched keywords: {', '.join(matched_keywords[:5])}")
                    else:
                        # NON-ONCOLOGY: Warn but allow manual paste
                        st.warning(f"⚠️ **NON-ONCOLOGY Content:** {oncology_score}/1.0")
                        st.info(
                            "This content may not be oncology-related. "
                            "You can still index it if needed."
                        )
                        if matched_keywords:
                            st.caption(f"Limited oncology keywords found: {', '.join(matched_keywords[:3])}")

                # Index button (different styling based on oncology score)
                button_type = "primary" if is_oncology else "secondary"
                button_label = "🚀 Index This Document" if is_oncology else "⚠️ Index Anyway (Non-Oncology)"

                if st.button(button_label, key="index_pasted", type=button_type):
                    with st.spinner("Indexing..."):
                        try:
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

                            st.info(f"Created {len(chunks)} chunks")

                            # Add to vector store
                            vector_store = get_vector_store()
                            metadata = {
                                "detected_type": detected['detected_type'],
                                "source": detected.get('source', ''),
                                "topics": detected.get('topics', []),
                                "file_name": filename,
                                "num_pages": 1,
                                "input_method": "paste"
                            }

                            chunk_ids = vector_store.add_documents(chunks, doc_id, metadata)
                            st.success(f"✓ Indexed {len(chunk_ids)} chunks in vector store")

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
                            st.success(f"✓ Built BM25 index")

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
                            st.success(f"✓ Saved to memory (ID: {doc_id})")

                            st.balloons()

                        except Exception as e:
                            st.error(f"Error indexing: {str(e)}")
                            st.code(traceback.format_exc())

            except Exception as e:
                st.error(f"Error processing pasted text: {str(e)}")
                st.code(traceback.format_exc())

    # Document stats only (no browsing for 1000+ docs)
    st.markdown("---")
    st.subheader("📊 Library Statistics")

    try:
        memory = get_memory()
        docs = memory.list_documents(limit=10000)  # Get count only

        if docs:
            total_docs = len(docs)

            # Calculate stats
            high_relevance = sum(1 for doc in docs if doc.get('metadata', {}).get('relevance_score', 0.5) >= 0.7)
            oncology_focused = sum(1 for doc in docs if doc.get('metadata', {}).get('oncology_score', 0.5) >= 0.7)

            # Display compact stats
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Total Documents", total_docs)
            with col2:
                st.metric("🎯 High Relevance", high_relevance)
            with col3:
                st.metric("⚕️ Oncology-Focused", oncology_focused)

            oncology_pct = int((oncology_focused / total_docs) * 100) if total_docs > 0 else 0
            st.progress(oncology_pct / 100, text=f"{oncology_pct}% Oncology-Focused")

            st.caption("💡 Use the **Query & Insights** tab to search your documents")
        else:
            st.info("No documents indexed yet. Upload files above to get started!")

    except Exception as e:
        st.warning(f"Could not load statistics: {str(e)}")


# ============================================================================
# TAB 2: QUERY & INSIGHTS
# ============================================================================

with tab2:
    st.header("Query Your Intelligence")

    # Query input
    query = st.text_area(
        "Ask a question about your competitive intelligence:",
        height=100,
        placeholder="E.g., What is the ORR for KRAS inhibitors in 2L NSCLC?\nCompare safety profiles of PD-1 inhibitors...",
        help="Ask factual questions or request comparisons"
    )

    # Search options
    with st.expander("⚙️ Search Options"):
        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider("Results to retrieve", 5, 20, 10)
        with col2:
            use_reranking = st.checkbox("Use reranking", value=True)

    # Action buttons
    col1, col2 = st.columns([1, 1])
    with col1:
        search_clicked = st.button("🔍 Search", type="primary", disabled=not query, use_container_width=True)
    with col2:
        profile_manager = get_program_profile()
        has_profile = profile_manager.has_profile()
        analyze_impact_clicked = st.button(
            "🎯 Analyze Impact for Program",
            type="secondary",
            disabled=not query or not has_profile,
            use_container_width=True,
            help="Generate program-specific impact analysis" if has_profile else "Set up a program profile first"
        )

    if search_clicked:
        with st.spinner("Searching..."):
            try:
                # Sanitize query to prevent prompt injection
                from core.input_sanitizer import get_sanitizer
                sanitizer = get_sanitizer()
                sanitized_query = sanitizer.sanitize_query(query, max_length=2000, strict=False)

                # Hybrid search
                hybrid_search = get_hybrid_search()
                results = hybrid_search.hybrid_search(sanitized_query, top_k=top_k)

                st.info(f"Retrieved {len(results)} results from hybrid search")

                if not results:
                    st.warning("No results found. Try uploading more documents or rephrasing your query.")
                else:
                    # Reranking
                    if use_reranking:
                        with st.spinner("Reranking..."):
                            reranker = get_reranker()
                            results = reranker.rerank(query, results, top_k=10)
                            st.success("✓ Reranked results")

                    # Generate answer
                    with st.spinner("Generating answer..."):
                        analyst = get_analyst()

                        # Check if comparison query (use sanitized query)
                        if analyst.is_comparison_query(sanitized_query):
                            answer = analyst.generate_comparison(sanitized_query, results)
                            st.markdown("### 📊 Comparison Analysis")
                        else:
                            answer = analyst.generate_answer(sanitized_query, results)
                            st.markdown("### 💡 Answer")

                    # Format citations
                    formatted_answer, citation_details = add_citation_links(answer, results)

                    # Display answer (Streamlit's markdown already escapes HTML, but add extra safety)
                    # Note: st.markdown with allow_html=False (default) provides protection
                    st.markdown(formatted_answer)

                    # Bibliography
                    if citation_details:
                        with st.expander("📚 References", expanded=True):
                            bib = create_bibliography(citation_details)
                            st.markdown(bib)

                    # Feedback
                    st.markdown("---")
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown("**Was this helpful?**")
                    with col2:
                        feedback_col1, feedback_col2, feedback_col3 = st.columns([1, 1, 3])
                        with feedback_col1:
                            if st.button("👍 Yes"):
                                memory = get_memory()
                                memory.log_query(sanitized_query, answer, [r['id'] for r in results], feedback=1)
                                st.success("Thanks for your feedback!")
                        with feedback_col2:
                            if st.button("👎 No"):
                                memory = get_memory()
                                memory.log_query(sanitized_query, answer, [r['id'] for r in results], feedback=-1)
                                st.info("We'll improve based on your feedback!")

                    # Show retrieved sources
                    with st.expander(f"🔎 View {len(results)} Retrieved Sources"):
                        for i, result in enumerate(results, 1):
                            st.markdown(f"**[{i}]** {result.get('metadata', {}).get('file_name', 'Unknown')} "
                                        f"(Page {result.get('chunk_index', 0) + 1})")
                            st.markdown(f"*Score: {result.get('rrf_score', 0):.3f}*")
                            st.text(result['text'][:300] + "...")
                            st.markdown("---")

            except Exception as e:
                st.error(f"Error processing query: {str(e)}")
                st.code(traceback.format_exc())

    # Analyze Impact button handler
    if analyze_impact_clicked:
        with st.spinner("Analyzing impact for your program..."):
            try:
                # Sanitize query to prevent prompt injection
                from core.input_sanitizer import get_sanitizer
                sanitizer = get_sanitizer()
                sanitized_query = sanitizer.sanitize_query(query, max_length=2000, strict=False)

                # Get program profile
                profile_manager = get_program_profile()
                program_context = profile_manager.format_profile_context()

                # Hybrid search
                hybrid_search = get_hybrid_search()
                results = hybrid_search.hybrid_search(sanitized_query, top_k=top_k)

                st.info(f"Retrieved {len(results)} results from hybrid search")

                if not results:
                    st.warning("No results found. Try uploading more documents or rephrasing your query.")
                else:
                    # Reranking
                    if use_reranking:
                        with st.spinner("Reranking..."):
                            reranker = get_reranker()
                            results = reranker.rerank(query, results, top_k=10)
                            st.success("✓ Reranked results")

                    # Generate Q&A Answer first (use sanitized query)
                    st.markdown("### 💡 Answer")
                    with st.spinner("Generating answer..."):
                        analyst = get_analyst()
                        if analyst.is_comparison_query(sanitized_query):
                            answer = analyst.generate_comparison(sanitized_query, results)
                        else:
                            answer = analyst.generate_answer(sanitized_query, results)

                    # Format citations for answer
                    formatted_answer, citation_details = add_citation_links(answer, results)
                    st.markdown(formatted_answer)

                    # Bibliography for answer
                    if citation_details:
                        with st.expander("📚 References for Answer", expanded=False):
                            bib = create_bibliography(citation_details)
                            st.markdown(bib)

                    st.markdown("---")

                    # Generate Program Impact Analysis
                    st.markdown("### 🎯 Impact Analysis for Your Program")
                    st.info(f"Analyzing implications for: **{profile_manager.get_profile()['program_name']}**")

                    with st.spinner("Generating program-specific impact analysis..."):
                        # Build impact analysis prompt with sanitized content
                        # Truncate and sanitize document text to prevent prompt injection
                        sanitized_contexts = []
                        for i, r in enumerate(results[:5]):
                            # Limit each document excerpt to 500 chars
                            doc_text = str(r.get('text', ''))[:500]
                            # Remove potential prompt injection patterns
                            doc_text = doc_text.replace('"""', '').replace("'''", '')
                            # Remove excessive newlines
                            doc_text = ' '.join(doc_text.split())
                            sanitized_contexts.append(f"[{i+1}] {doc_text}")

                        impact_prompt = f"""Based on the following intelligence:

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
                        from generation.analyst import get_analyst
                        analyst = get_analyst()
                        impact_analysis = analyst.generate_answer(impact_prompt, results)

                    # Display impact analysis
                    st.markdown(impact_analysis)

                    # Show program context used
                    with st.expander("📋 Program Context Used"):
                        st.code(program_context, language="markdown")

                    # Feedback
                    st.markdown("---")
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown("**Was this helpful?**")
                    with col2:
                        feedback_col1, feedback_col2, feedback_col3 = st.columns([1, 1, 3])
                        with feedback_col1:
                            if st.button("👍 Yes", key="impact_yes"):
                                memory = get_memory()
                                memory.log_query(
                                    f"[IMPACT] {sanitized_query}",
                                    f"{answer}\n\n---\n\n{impact_analysis}",
                                    [r['id'] for r in results],
                                    feedback=1
                                )
                                st.success("Thanks for your feedback!")
                        with feedback_col2:
                            if st.button("👎 No", key="impact_no"):
                                memory = get_memory()
                                memory.log_query(
                                    f"[IMPACT] {sanitized_query}",
                                    f"{answer}\n\n---\n\n{impact_analysis}",
                                    [r['id'] for r in results],
                                    feedback=-1
                                )
                                st.info("We'll improve based on your feedback!")

                    # Show retrieved sources
                    with st.expander(f"🔎 View {len(results)} Retrieved Sources"):
                        for i, result in enumerate(results, 1):
                            st.markdown(f"**[{i}]** {result.get('metadata', {}).get('file_name', 'Unknown')} "
                                        f"(Page {result.get('chunk_index', 0) + 1})")
                            st.markdown(f"*Score: {result.get('rrf_score', 0):.3f}*")
                            st.text(result['text'][:300] + "...")
                            st.markdown("---")

            except Exception as e:
                st.error(f"Error analyzing impact: {str(e)}")
                st.code(traceback.format_exc())

    # Query history
    if st.checkbox("📜 Show Query History"):
        try:
            memory = get_memory()
            stats = memory.get_query_stats()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Queries", stats['total_queries'])
            with col2:
                st.metric("Positive Feedback", stats['positive_feedback'])
            with col3:
                st.metric("Satisfaction Rate", f"{stats.get('satisfaction_rate', 0):.0%}")

        except Exception as e:
            st.warning(f"Could not load query history: {str(e)}")


# ============================================================================
# TAB 3: PROGRAM PROFILE
# ============================================================================

with tab3:
    st.header("⚙️ Configure Your Program Profile")
    st.markdown("""
    Define your program's context once. All queries will automatically analyze competitive intelligence
    **relative to YOUR program** with structured impact analysis.

    **Only Program Name is required** - you can provide just a drug name (e.g., "Keytruda") or mechanism (e.g., "EGFR conditional TCE").
    Add more details for richer analysis.
    """)

    # Get current profile
    profile_manager = get_program_profile()
    current_profile = profile_manager.get_profile()

    # Display current profile status
    if current_profile:
        st.success("✓ Program Profile Active - All queries use personalized impact analysis")
    else:
        st.info("ℹ️ No program profile set - Using general CI Q&A mode")

    st.markdown("---")

    # Profile form
    with st.form("program_profile_form"):
        st.markdown("### Program Details")

        col1, col2 = st.columns(2)

        with col1:
            program_name = st.text_input(
                "Program Name / Drug / Mechanism *",
                value=current_profile.get('program_name', '') if current_profile else '',
                placeholder="e.g., Keytruda, EGFR conditional TCE, AZ-123",
                help="Drug name, mechanism, or internal program name (REQUIRED)"
            )

            indication = st.text_input(
                "Indication (optional)",
                value=current_profile.get('indication', '') if current_profile else '',
                placeholder="e.g., 2L+ NSCLC (KRAS G12C mutant)",
                help="Specific indication and line of therapy (optional)"
            )

            stage_options = ["Not specified", "Preclinical", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3", "Phase 3", "NDA/BLA", "Marketed"]
            default_stage = current_profile.get('stage', 'Not specified') if current_profile else 'Not specified'
            stage_index = stage_options.index(default_stage) if default_stage in stage_options else 0

            stage = st.selectbox(
                "Development Stage (optional)",
                options=stage_options,
                index=stage_index
            )

            target = st.text_input(
                "Molecular Target",
                value=current_profile.get('target', '') if current_profile else '',
                placeholder="e.g., KRAS G12C",
                help="Primary molecular target or mechanism"
            )

        with col2:
            our_orr = st.number_input(
                "Our ORR (%)",
                min_value=0.0,
                max_value=100.0,
                value=float(current_profile.get('our_orr', 0.0)) if current_profile and current_profile.get('our_orr') else 0.0,
                step=1.0,
                help="Your program's objective response rate"
            )

            our_pfs = st.number_input(
                "Our PFS (months)",
                min_value=0.0,
                max_value=100.0,
                value=float(current_profile.get('our_pfs', 0.0)) if current_profile and current_profile.get('our_pfs') else 0.0,
                step=0.1,
                help="Your program's progression-free survival"
            )

            our_safety_profile = st.text_area(
                "Our Safety Profile",
                value=current_profile.get('our_safety_profile', '') if current_profile else '',
                placeholder="e.g., Grade ≥3 AEs: 58%, Disc rate: 8%",
                help="Summary of key safety metrics",
                height=100
            )

        differentiators = st.text_area(
            "Key Differentiators",
            value=current_profile.get('differentiators', '') if current_profile else '',
            placeholder="e.g., Better tolerability, longer PFS vs sotorasib, oral QD dosing",
            help="What makes your program different from competition",
            height=100
        )

        st.markdown("---")

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            submitted = st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True)

        with col2:
            if current_profile:
                clear = st.form_submit_button("🗑️ Clear", use_container_width=True)
            else:
                clear = False

        with col3:
            st.markdown("")  # Spacer

    # Handle form submission
    if submitted:
        if not program_name:
            st.error("❌ Please provide at least a Program Name / Drug / Mechanism")
        else:
            try:
                # Sanitize text inputs to prevent injection attacks
                from core.input_sanitizer import get_sanitizer
                sanitizer = get_sanitizer()

                # Sanitize all text fields (reasonable limits, non-strict mode)
                program_name_safe = sanitizer.sanitize_query(program_name, max_length=200, strict=False) if program_name else None
                indication_safe = sanitizer.sanitize_query(indication, max_length=500, strict=False) if indication else None
                our_safety_profile_safe = sanitizer.sanitize_query(our_safety_profile, max_length=1000, strict=False) if our_safety_profile else None
                target_safe = sanitizer.sanitize_query(target, max_length=200, strict=False) if target else None
                differentiators_safe = sanitizer.sanitize_query(differentiators, max_length=1000, strict=False) if differentiators else None

                profile_manager.save_profile(
                    program_name=program_name_safe,
                    indication=indication_safe,
                    stage=stage if stage != "Not specified" else None,
                    our_orr=our_orr if our_orr > 0 else None,
                    our_pfs=our_pfs if our_pfs > 0 else None,
                    our_safety_profile=our_safety_profile_safe,
                    target=target_safe,
                    differentiators=differentiators_safe
                )
                st.success("✅ Program profile saved! All queries will now use personalized impact analysis.")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error saving profile: {str(e)}")

    if clear:
        try:
            profile_manager.delete_profile()
            st.success("✅ Profile cleared. Returning to general CI Q&A mode.")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error clearing profile: {str(e)}")

    # Program Documents Section
    if current_profile:
        st.markdown("---")
        st.markdown("### 📎 Program Documents")
        st.markdown("Upload papers, slides, or other documents specific to your program.")

        # Document upload
        uploaded_program_files = st.file_uploader(
            "Upload Program Documents",
            type=['pdf', 'pptx', 'docx', 'txt', 'md'],
            accept_multiple_files=True,
            help="Papers, slide decks, protocols, regulatory docs, etc.",
            key="program_doc_uploader"
        )

        doc_type_selection = st.selectbox(
            "Document Type",
            options=["Program Document", "Research Paper", "Slide Deck", "Protocol", "Regulatory Filing", "Other"],
            help="Categorize the document for better organization"
        )

        if uploaded_program_files:
            if st.button("📤 Upload & Link to Program", type="primary"):
                with st.spinner("Processing program documents..."):
                    success_count = 0
                    error_count = 0

                    for uploaded_file in uploaded_program_files:
                        try:
                            # Validate file size (50MB limit)
                            MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
                            if uploaded_file.size > MAX_FILE_SIZE:
                                st.error(f"❌ {uploaded_file.name}: File too large (max 50MB)")
                                error_count += 1
                                continue

                            # Sanitize filename to prevent path traversal
                            from core.input_sanitizer import get_sanitizer
                            sanitizer = get_sanitizer()
                            safe_filename = sanitizer.sanitize_filename(uploaded_file.name)

                            # Parse document
                            parsed_doc = parse_document(uploaded_file)

                            # Detect type
                            detected_type = detect_document_type(parsed_doc)

                            # Generate doc_id
                            doc_id = f"prog_{uuid.uuid4().hex[:12]}"

                            # Add to memory with sanitized filename
                            memory = get_memory()
                            memory.add_document(
                                doc_id=doc_id,
                                filename=safe_filename,  # Use sanitized filename
                                detected_type=detected_type,
                                source="program_upload",
                                topics=[],
                                file_size=uploaded_file.size,
                                num_pages=len(parsed_doc['pages']),
                                metadata={
                                    "upload_source": "program_profile",
                                    "program_doc_type": doc_type_selection.lower().replace(" ", "_"),
                                    "original_filename": uploaded_file.name  # Keep original for reference
                                }
                            )

                            # Index document
                            from ingestion.chunker import chunk_text
                            full_text = "\n\n".join([p['text'] for p in parsed_doc['pages']])
                            chunks = chunk_text(full_text, CHUNK_SIZE, CHUNK_OVERLAP)

                            vector_store = get_vector_store()
                            chunk_ids = vector_store.add_documents(
                                chunks=chunks,
                                doc_id=doc_id,
                                metadata={
                                    "detected_type": detected_type,
                                    "source": "program_upload",
                                    "file_name": safe_filename,  # Use sanitized filename
                                    "program_doc_type": doc_type_selection.lower().replace(" ", "_")
                                }
                            )

                            # Index into BM25
                            hybrid_search = get_hybrid_search()
                            chunk_dicts = [
                                {"id": cid, "text": chunk, "metadata": {"detected_type": detected_type}}
                                for cid, chunk in zip(chunk_ids, chunks)
                            ]
                            hybrid_search.index_documents(chunk_dicts)

                            # Link to program
                            profile_manager.link_document_to_program(
                                doc_id=doc_id,
                                doc_type=doc_type_selection.lower().replace(" ", "_")
                            )

                            # Mark as indexed
                            memory.mark_indexed(doc_id)

                            success_count += 1

                        except Exception as e:
                            logger.error(f"Error uploading program document {uploaded_file.name}: {e}")
                            error_count += 1

                    if success_count > 0:
                        st.success(f"✅ Uploaded and linked {success_count} program document(s)!")
                    if error_count > 0:
                        st.error(f"❌ Failed to upload {error_count} document(s)")

                    st.rerun()

        # Display linked documents
        st.markdown("#### Linked Program Documents")
        program_docs = profile_manager.get_program_documents()

        if program_docs:
            for doc in program_docs:
                with st.expander(f"📄 {doc['filename']} ({doc['detected_type']})"):
                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.markdown(f"**Type**: {doc['detected_type']}")
                        st.markdown(f"**Pages**: {doc['num_pages']}")
                    with col2:
                        st.markdown(f"**Uploaded**: {doc['upload_date'][:10]}")
                        st.markdown(f"**Size**: {doc['file_size'] / 1024:.1f} KB")
                    with col3:
                        if st.button("🗑️ Unlink", key=f"unlink_{doc['doc_id']}"):
                            profile_manager.unlink_document_from_program(doc['doc_id'])
                            st.success(f"Unlinked {doc['filename']}")
                            st.rerun()
        else:
            st.info("No program documents uploaded yet. Upload papers, slides, or protocols above.")

    # Display current profile
    if current_profile:
        st.markdown("---")
        st.markdown("### 📋 Current Profile")
        st.code(profile_manager.format_profile_context(), language="markdown")


# Sidebar
with st.sidebar:
    st.markdown("## CI-RAG System")
    st.markdown("*Competitive Intelligence RAG*")

    st.markdown("---")

    # Stats
    st.markdown("### 📊 System Stats")
    try:
        memory = get_memory()
        stats = memory.get_stats()

        st.metric("Documents Indexed", stats['total_documents'])
        st.metric("Corrections", stats['total_corrections'])

        if stats['documents_by_type']:
            st.markdown("**By Type:**")
            for doc_type, count in stats['documents_by_type'].items():
                st.markdown(f"- {doc_type}: {count}")

    except Exception as e:
        st.warning(f"Stats unavailable: {str(e)}")

    st.markdown("---")
    st.markdown("### 🚀 Quick Start")
    st.markdown("""
1. **Upload** documents in Tab 1
2. Click **Index** to process
3. **Query** in Tab 2
4. Get cited insights!
    """)

    st.markdown("---")
    st.markdown("### 🤖 Auto-Fetch")

    # Initialize if not exists
    if "auto_fetch_enabled" not in st.session_state:
        st.session_state.auto_fetch_enabled = False
    if "scheduler" not in st.session_state:
        st.session_state.scheduler = None

    # Auto-fetch toggle
    auto_fetch = st.checkbox(
        "Enable Auto-Fetch",
        value=st.session_state.auto_fetch_enabled,
        help="Automatically fetch and index FDA, EMA, and biopharma news (hourly)"
    )

    # Handle toggle change
    if auto_fetch != st.session_state.auto_fetch_enabled:
        st.session_state.auto_fetch_enabled = auto_fetch

        if auto_fetch:
            # Start scheduler
            if st.session_state.scheduler is None:
                st.session_state.scheduler = get_scheduler(interval_minutes=60)
                st.session_state.scheduler.start()
                st.success("✓ Auto-fetch enabled! Running hourly.")
        else:
            # Stop scheduler
            if st.session_state.scheduler is not None:
                st.session_state.scheduler.stop()
                st.session_state.scheduler = None
                st.info("Auto-fetch disabled.")

    # Show status if enabled
    if st.session_state.auto_fetch_enabled and st.session_state.scheduler:
        status = st.session_state.scheduler.get_status()
        if status["last_run"]:
            st.caption(f"Last run: {status['last_run'][:16]}")
            if status["last_stats"]:
                st.caption(f"New items: {status['last_stats']['indexed']}")

    st.markdown("---")
    st.markdown("### 📋 SAB Tools")

    # Generate Pre-Read button
    if st.button("Generate SAB Pre-Read", use_container_width=True):
        with st.spinner("Generating SAB Pre-Read..."):
            try:
                generator = get_brief_generator()
                brief = generator.generate_preread(weeks_back=2)

                if "error" in brief:
                    st.error(brief["error"])
                else:
                    st.success("✓ SAB Pre-Read generated!")

                    # Export to HTML
                    html = generator.export_to_html(brief)
                    st.download_button(
                        "📥 Download Pre-Read (HTML)",
                        data=html,
                        file_name=f"SAB_PreRead_{datetime.now().strftime('%Y%m%d')}.html",
                        mime="text/html"
                    )
            except Exception as e:
                st.error(f"Error: {str(e)}")

    # Refresh Intelligence button
    if st.button("🔄 Refresh Intelligence", use_container_width=True, help="Fetch latest papers from PubMed and regulatory updates"):
        # Initialize session state for refresh
        if "refresh_progress" not in st.session_state:
            st.session_state.refresh_progress = []

        progress_container = st.empty()

        def progress_callback(message: str):
            """Update progress in UI"""
            st.session_state.refresh_progress.append(message)
            progress_container.markdown("\n".join([f"- {msg}" for msg in st.session_state.refresh_progress[-5:]]))

        with st.spinner("Refreshing intelligence..."):
            try:
                refresher = get_session_refresh(progress_callback=progress_callback)
                stats = refresher.refresh_all(max_papers=20, max_rss_items=50, days_back=90)

                # Show summary
                st.success(f"✓ Refresh complete!")
                st.metric("New Documents", stats['total_new'])
                st.metric("Updated Documents", stats['total_updated'])

                # Show details
                with st.expander("📊 Details"):
                    st.write(f"**PubMed:** {stats['pubmed']['indexed']} new, {stats['pubmed']['updated']} updated")
                    st.write(f"**RSS Feeds:** {stats['rss']['indexed']} new, {stats['rss']['updated']} updated")

                    if stats.get('errors'):
                        st.warning("⚠️ Some errors occurred:")
                        for error in stats['errors']:
                            st.write(f"- {error}")

                # Clear progress
                st.session_state.refresh_progress = []

            except Exception as e:
                st.error(f"Error during refresh: {str(e)}")
                st.write(traceback.format_exc())

    st.markdown("---")
    st.markdown("### ⚙️ Requirements")
    st.markdown("""
- Qdrant running on port 6333
- OPENAI_API_KEY in .env
- See README.md for setup
    """)
