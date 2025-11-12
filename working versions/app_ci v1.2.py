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

# Apply Graphite-Sand theme (must be before any other Streamlit commands)
from theme_bootstrap import boot_graphite_sand
boot_graphite_sand()

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

# CSS for button styling
st.markdown("""
<style>
/* Make primary button text white */
button[kind="primaryFormSubmit"] p {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)

# Tabs - Program Profile first for quick setup
tab1, tab2, tab3 = st.tabs(["⚙️ Program Profile", "📁 Upload Documents", "💬 Query & Insights"])

# ============================================================================
# TAB 1: PROGRAM PROFILE
# ============================================================================

with tab1:
    profile_manager = get_program_profile()
    current_profile = profile_manager.get_profile()

    # Display current profile status
    if current_profile:
        st.success("✓ Program Profile Active - All queries use personalized impact analysis")
    else:
        st.info("ℹ️ No program profile set - Using general CI Q&A mode")

    # Try Example button - saves example to profile directly
    if st.button("🔬 Try Example (CLDN18.2 ADC)", help="Fill form with CLDN18.2 ADC example"):
        # Save example profile directly
        profile_manager.save_profile(
            program_name="CLDN18.2 ADC",
            indication="Gastric/GEJ cancer, 2L+",
            stage="Phase 2/3",
            target="CLDN18.2",
            differentiators="Efficacy: ORR 45%, PFS 8.2 months, DoR 12.1 months\nSafety: Grade ≥3 AEs 40%, Discontinuation 8%, Most common: nausea, fatigue\nDifferentiators: First-in-class CLDN18.2 targeting, superior tumor selectivity vs chemo, better tolerability profile",
            our_orr=None,
            our_pfs=None,
            our_safety_profile=None
        )
        st.rerun()

    st.markdown("---")

    # Simplified Profile form - just the essentials
    with st.form("program_profile_form"):
        st.markdown("### Program Details")

        program_name = st.text_input(
            "Program Name / Drug / Mechanism *",
            value=current_profile.get('program_name', '') if current_profile else '',
            placeholder="e.g., CLDN18.2 ADC",
            help="Drug name, mechanism, or internal program name (REQUIRED)"
        )

        indication = st.text_input(
            "Indication (optional)",
            value=current_profile.get('indication', '') if current_profile else '',
            placeholder="e.g., Gastric/GEJ cancer, 2L+",
            help="Specific indication and line of therapy"
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
            "Molecular Target (optional)",
            value=current_profile.get('target', '') if current_profile else '',
            placeholder="e.g., CLDN18.2",
            help="Primary molecular target or mechanism"
        )

        program_data = st.text_area(
            "Program Data & Differentiators (optional)",
            value=current_profile.get('differentiators', '') if current_profile else '',
            placeholder="e.g.,\nEfficacy: ORR 45%, PFS 8.2 months, DoR 12.1 months\nSafety: Grade ≥3 AEs 40%, Discontinuation 8%, Most common: nausea, fatigue\nDifferentiators: First-in-class CLDN18.2 targeting, superior tumor selectivity vs chemo, better tolerability profile",
            help="Include efficacy data, safety data, and key competitive differentiators",
            height=120
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("💾 Save Profile", type="primary", use_container_width=True)

        with col2:
            clear = st.form_submit_button("🗑️ Clear", use_container_width=True)

    # Handle form submission
    if submitted:
        if not program_name:
            st.error("❌ Please provide at least a Program Name / Drug / Mechanism")
        else:
            try:
                # Sanitize text inputs to prevent injection attacks
                from core.input_sanitizer import get_sanitizer
                sanitizer = get_sanitizer()

                # Sanitize all text fields
                program_name_safe = sanitizer.sanitize_query(program_name, max_length=200, strict=False) if program_name else None
                indication_safe = sanitizer.sanitize_query(indication, max_length=500, strict=False) if indication else None
                target_safe = sanitizer.sanitize_query(target, max_length=200, strict=False) if target else None
                program_data_safe = sanitizer.sanitize_query(program_data, max_length=2000, strict=False) if program_data else None

                profile_manager.save_profile(
                    program_name=program_name_safe,
                    indication=indication_safe,
                    stage=stage if stage != "Not specified" else None,
                    target=target_safe,
                    differentiators=program_data_safe,  # Stores combined data in differentiators field
                    our_orr=None,  # Removed from simplified form
                    our_pfs=None,  # Removed from simplified form
                    our_safety_profile=None  # Removed from simplified form
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

    # Display current profile
    if current_profile:
        st.markdown("---")
        st.markdown("### 📋 Current Profile")
        st.code(profile_manager.format_profile_context(), language="markdown")


# ============================================================================
# TAB 2: UPLOAD & INDEX
# ============================================================================

with tab2:
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


# ============================================================================
# TAB 3: QUERY & INSIGHTS
# ============================================================================

with tab3:
    st.header("Query Your Intelligence")

    # Query input
    query = st.text_area(
        "Ask a question about your competitive intelligence:",
        height=100,
        placeholder="E.g., What is the ORR for KRAS inhibitors in 2L NSCLC?\nCompare safety profiles of PD-1 inhibitors...",
        help="Ask factual questions or request comparisons"
    )

    # Default search settings (hidden from user)
    top_k = 10
    use_reranking = True

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

                # Web search fallback if no results and vector store is empty
                if not results:
                    # Check if vector store is empty
                    from retrieval.vector_store import get_vector_store
                    from core.config import WEB_SEARCH_ENABLED, WEB_SEARCH_MIN_DOC_THRESHOLD

                    vector_store = get_vector_store()
                    stats = vector_store.get_stats()
                    total_docs = stats.get("total_points", 0)

                    if WEB_SEARCH_ENABLED and total_docs <= WEB_SEARCH_MIN_DOC_THRESHOLD:
                        st.info("📡 No documents in vector store. Searching the web for competitive intelligence...")

                        try:
                            from retrieval.web_search import get_web_search
                            web_search = get_web_search()

                            if web_search:
                                with st.spinner("Searching web for oncology CI data..."):
                                    results = web_search.search(sanitized_query, top_k=top_k)

                                if results:
                                    st.success(f"✓ Found {len(results)} results from web search")
                                    # Mark results as from web search
                                    for r in results:
                                        r['source_type'] = 'web_search'
                                else:
                                    st.warning("No relevant results found in web search either. Try rephrasing your query.")
                            else:
                                st.warning("Web search not available. Please configure TAVILY_API_KEY in .env file.")
                        except Exception as e:
                            st.error(f"Web search failed: {str(e)}")
                            st.warning("No results found. Try uploading more documents or rephrasing your query.")
                    else:
                        st.warning("No results found. Try uploading more documents or rephrasing your query.")

                if results:
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

                # Web search fallback if no results and vector store is empty
                if not results:
                    # Check if vector store is empty
                    from retrieval.vector_store import get_vector_store
                    from core.config import WEB_SEARCH_ENABLED, WEB_SEARCH_MIN_DOC_THRESHOLD

                    vector_store = get_vector_store()
                    stats = vector_store.get_stats()
                    total_docs = stats.get("total_points", 0)

                    if WEB_SEARCH_ENABLED and total_docs <= WEB_SEARCH_MIN_DOC_THRESHOLD:
                        st.info("📡 No documents in vector store. Searching the web for competitive intelligence...")

                        try:
                            from retrieval.web_search import get_web_search
                            web_search = get_web_search()

                            if web_search:
                                with st.spinner("Searching web for oncology CI data..."):
                                    results = web_search.search(sanitized_query, top_k=top_k)

                                if results:
                                    st.success(f"✓ Found {len(results)} results from web search")
                                    # Mark results as from web search
                                    for r in results:
                                        r['source_type'] = 'web_search'
                                else:
                                    st.warning("No relevant results found in web search either. Try rephrasing your query.")
                            else:
                                st.warning("Web search not available. Please configure TAVILY_API_KEY in .env file.")
                        except Exception as e:
                            st.error(f"Web search failed: {str(e)}")
                            st.warning("No results found. Try uploading more documents or rephrasing your query.")
                    else:
                        st.warning("No results found. Try uploading more documents or rephrasing your query.")

                if results:
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
