"""Local PDF Q&A interface. Run with `streamlit run app.py`."""

from hashlib import sha256
from pathlib import Path

import streamlit as st

from pdf_qa import pipeline
from pdf_qa.types import AppError, Settings

st.set_page_config(page_title="PDF Q&A", page_icon="📄", layout="wide")


@st.cache_resource(show_spinner=False)
def cached_index(path: str, manifest_stamp: int):
    """Reload when a persisted index is rebuilt, including across reruns."""
    return pipeline.load_index(Path(path))


def clear_document():
    for key in ("document", "last_answer", "last_hits", "last_question", "question"):
        st.session_state.pop(key, None)


st.title("Ask your PDF")
st.caption("Answers from your document, with page citations. Processing stays on this computer.")

with st.sidebar:
    st.header("Your document")
    source = st.radio("Document source", ["Upload PDF", "Saved index"], key="source")
    upload = None
    selected = None
    settings = Settings()
    if source == "Upload PDF":
        upload = st.file_uploader("Choose a PDF", type=["pdf"], key="upload")
        st.caption("One English PDF · up to 50 MB · up to 200 pages")
        extraction = st.selectbox(
            "Text extraction",
            ["Automatic", "Force OCR for all pages"],
            help="Automatic OCR reads pages with little text. Force OCR for text inside images.",
            key="extraction",
        )
        chunk_size = st.select_slider(
            "Chunk size (characters)", options=[300, 800, 1500], value=800, key="chunk_size"
        )
        settings = Settings(
            chunk_size=chunk_size, ocr_mode="auto" if extraction == "Automatic" else "force"
        )
        uploaded_bytes = upload.getvalue() if upload is not None else None
        identity = (
            source,
            sha256(uploaded_bytes).hexdigest() if uploaded_bytes else None,
            settings,
        )
    else:
        try:
            saved = pipeline.list_indexes()
        except (AppError, OSError) as exc:
            st.error(str(exc))
            saved = []
        if saved:
            entries = {str(entry["path"]): entry for entry in saved}
            selected_path = st.selectbox(
                "Saved document",
                options=list(entries),
                format_func=lambda path: (
                    f"{entries[path].get('filename', Path(path).name)} · "
                    f"{entries[path].get('settings', {}).get('chunk_size', '?')} characters · "
                    f"{Path(path).name[:8]}"
                ),
                key="saved_path",
            )
            selected = entries[selected_path]
            if selected.get("error"):
                st.error(selected["error"])
                st.info("Upload the original PDF and choose Rebuild index to repair this index.")
        else:
            st.info("No saved indexes yet. Upload a PDF to get started.")
        identity = (source, selected["path"] if selected else None)

    if st.session_state.get("document_identity") != identity:
        clear_document()
        st.session_state.document_identity = identity

    if source == "Upload PDF":
        build_col, rebuild_col = st.columns(2)
        build = build_col.button("Build index", disabled=upload is None, type="primary")
        rebuild = rebuild_col.button(
            "Rebuild index",
            disabled=upload is None,
            help="Replace a damaged or outdated cached index from this PDF.",
        )
        if build or rebuild:
            clear_document()
            progress = st.progress(0.0, text="Preparing your document…")
            try:
                with st.spinner("Reading and indexing your PDF…"):
                    st.session_state.document = pipeline.ingest(
                        uploaded_bytes,
                        upload.name,
                        settings,
                        pipeline.LocalModels(),
                        progress=lambda fraction, message: progress.progress(
                            max(0.0, min(1.0, fraction)), text=message
                        ),
                        rebuild=rebuild,
                    )
                if rebuild:
                    cached_index.clear()
            except (AppError, OSError) as exc:
                st.error(str(exc))
                st.info("Check the error, then retry. For a damaged cache, choose Rebuild index.")
            finally:
                progress.empty()
    elif st.button(
        "Load index", disabled=selected is None or bool(selected.get("error")), type="primary"
    ):
        clear_document()
        try:
            path = Path(selected["path"])
            stamp = (path / "manifest.json").stat().st_mtime_ns
            with st.spinner("Loading your saved document…"):
                st.session_state.document = cached_index(str(path), stamp)
        except (AppError, OSError) as exc:
            st.error(str(exc))
            st.info("Upload the original PDF and choose Rebuild index to repair this index.")

document = st.session_state.get("document")
if document is None:
    st.info("Upload a PDF and build its index, or load a saved index from the sidebar.")
else:
    manifest = document.manifest
    st.subheader(manifest["filename"])
    pages, chunks, size = st.columns(3)
    pages.metric("Pages", manifest["page_count"])
    chunks.metric("Searchable passages", manifest["chunk_count"])
    size.metric("Chunk size", f"{manifest['settings']['chunk_size']} characters")
    st.caption(
        "Text extraction: "
        + ("Forced OCR" if manifest["settings"]["ocr_mode"] == "force" else "Automatic")
        + ". Page citations use PDF page numbers, starting at 1."
    )
    for warning in manifest.get("warnings", []):
        st.warning(warning)

with st.form("question_form"):
    question = st.text_input(
        "What would you like to know?",
        key="question",
        disabled=document is None,
        max_chars=2000,
        placeholder="Ask a question answered by this PDF",
    )
    submit = st.form_submit_button("Find answer", type="primary", disabled=document is None)

st.caption(
    "Each question is independent. Answers may be wrong or incomplete; check the cited passages. "
    "NOT FOUND means the model declined to answer."
)
if submit and document is not None:
    for key in ("last_answer", "last_hits", "last_question"):
        st.session_state.pop(key, None)
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        try:
            with st.spinner("Finding relevant passages and writing an answer…"):
                models = pipeline.LocalModels()
                hits = pipeline.retrieve(document, question.strip(), models)
                st.session_state.last_hits = hits
                st.session_state.last_question = question.strip()
                st.session_state.last_answer = pipeline.answer(question.strip(), hits, models)
        except (AppError, OSError) as exc:
            st.error(str(exc))
            st.info(
                "Resolve the reported issue and ask again. This error is not a NOT FOUND answer."
            )

if "last_question" in st.session_state:
    st.divider()
    st.caption("Question")
    st.text(st.session_state.last_question)
if "last_answer" in st.session_state:
    answer = st.session_state.last_answer
    st.subheader("Answer")
    st.text("NOT FOUND" if answer.refused else answer.text)
    if answer.citations:
        st.caption("Source PDF pages: " + ", ".join(str(page) for page in answer.citations))
if "last_hits" in st.session_state:
    hits = st.session_state.last_hits
    with st.expander(f"Retrieved passages ({len(hits)})"):
        st.caption("Similarity scores rank passages. They are not confidence probabilities.")
        for rank, hit in enumerate(hits, 1):
            st.markdown(f"**Passage {rank} · PDF page {hit.chunk.page} · score {hit.score:.4f}**")
            st.caption(f"Chunk {hit.chunk.id} · extraction: {hit.chunk.method}")
            st.text(hit.chunk.text)
