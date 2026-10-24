import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
    ArrowLeft,
    Save,
    ChevronLeft,
    ChevronRight,
    Download,
    ZoomIn,
    ZoomOut,
    Maximize2,
    Loader2,
    Bold,
    Italic,
    AlignLeft,
    AlignCenter,
    AlignRight,
    RefreshCw,
} from "lucide-react";
import {
    getDocument,
    getPageImageUrl,
    getDocumentLayout,
    getDocumentStatus,
    saveDocumentLayout,
    getExportUrl,
} from "../services/api";

function PageSidebar({ docId, pageNumbers, activePage, onSelect, isOpen, onToggle, isRight }) {
    if (!isOpen) {
        return (
            <button
                onClick={onToggle}
                className={`h-full px-1 border-${isRight ? "l" : "r"} border-gray-200 bg-gray-50 text-gray-400 hover:bg-gray-100 cursor-pointer text-xs`}
                title="Show Page List"
            >
                {isRight ? "‹" : "›"}
            </button>
        );
    }

    return (
        <aside className={`w-24 shrink-0 overflow-y-auto border-${isRight ? "l" : "r"} border-gray-200 bg-white p-1.5`}>
            <div className="flex items-center justify-between pb-1 mb-1 border-b border-gray-100 text-xs font-semibold text-gray-600">
                <span>Pages</span>
                <button
                    onClick={onToggle}
                    className="text-gray-400 hover:text-gray-600 cursor-pointer p-0.5"
                    title="Collapse"
                >
                    {isRight ? "›" : "‹"}
                </button>
            </div>
            <div className="flex flex-col gap-1.5">
                {pageNumbers.map((p) => (
                    <div
                        key={p}
                        onClick={() => onSelect(p)}
                        className={`cursor-pointer rounded p-1 text-center border transition ${
                            p === activePage ? "border-blue-600 bg-blue-50/50 shadow-xs" : "border-gray-200 hover:border-gray-300"
                        }`}
                    >
                        <div className="h-20 w-full bg-gray-100 overflow-hidden rounded">
                            <img
                                src={getPageImageUrl(docId, p)}
                                alt=""
                                className="h-full w-full object-cover"
                                loading="lazy"
                            />
                        </div>
                        <span className="text-[11px] font-medium text-gray-600 mt-0.5 block">{p}</span>
                    </div>
                ))}
            </div>
        </aside>
    );
}

function DocumentViewer() {
    const { id: documentId } = useParams();
    const navigate = useNavigate();

    const [docData, setDocData] = useState(null);
    const [layout, setLayout] = useState(null);
    const [activePage, setActivePage] = useState(1);
    const [activeElId, setActiveElId] = useState(null);

    const [loading, setLoading] = useState(true);
    const [layoutLoading, setLayoutLoading] = useState(true);
    const [layoutError, setLayoutError] = useState("");
    const [job, setJob] = useState(null);
    const [saving, setSaving] = useState(false);
    const [isDirty, setIsDirty] = useState(false);
    const [saveNotice, setSaveNotice] = useState("");
    const [showLeftPages, setShowLeftPages] = useState(true);
    const [showRightPages, setShowRightPages] = useState(true);
    const [scale, setScale] = useState(0.85);

    const loadLayout = useCallback(
        async ({ refresh = false } = {}) => {
            const { httpStatus, data } = await getDocumentLayout(documentId, { refresh });

            if (httpStatus === 202 || data?.status === "processing") {
                setJob({
                    state: "processing",
                    page: data?.page || 0,
                    total: data?.total || 0,
                });
                setLayoutLoading(true);
                return false;
            }

            if (data?.status === "failed") {
                setJob({ state: "failed", error: data?.error || "" });
                setLayoutError(data?.error || "Text extraction failed. Please try again.");
                setLayoutLoading(false);
                return false;
            }

            if (!data?.pages?.length) {
                setLayout(null);
                setJob(null);
                setLayoutError("No text was extracted from this document.");
                setLayoutLoading(false);
                return false;
            }

            setLayout(data);
            setJob({ state: "completed" });
            setLayoutError("");
            setLayoutLoading(false);
            setIsDirty(false);
            return true;
        },
        [documentId]
    );

    useEffect(() => {
        let isMounted = true;
        (async () => {
            try {
                setLoading(true);
                setLayoutLoading(true);
                setLayoutError("");
                setJob(null);
                const dRes = await getDocument(documentId);
                if (!isMounted) return;
                setDocData(dRes);
                setLoading(false);

                await loadLayout();
            } catch (err) {
                console.error("Load failed:", err);
                if (isMounted) {
                    setLayoutError(
                        err.response?.data?.details ||
                            err.response?.data?.error ||
                            err.message ||
                            "Failed to load document layout"
                    );
                    setLayoutLoading(false);
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        })();
        return () => { isMounted = false; };
    }, [documentId, loadLayout]);

    useEffect(() => {
        if (job?.state !== "processing") return;

        let cancelled = false;
        let timer = null;
        let failedPolls = 0;

        const poll = async () => {
            try {
                const st = await getDocumentStatus(documentId);
                if (cancelled) return;
                failedPolls = 0;

                if (st.status === "completed") {
                    if (st.has_layout) {
                        const ok = await loadLayout();
                        if (!cancelled && !ok) timer = setTimeout(poll, 2000);
                    } else if (!cancelled) {
                        setJob(null);
                        setLayoutLoading(false);
                        setLayoutError("Extraction finished but no layout was found.");
                    }
                    return;
                }

                if (st.status === "failed") {
                    if (!cancelled) {
                        setJob({ state: "failed", error: st.error || "" });
                        setLayoutError(st.error || "Text extraction failed. Please try again.");
                        setLayoutLoading(false);
                    }
                    return;
                }

                setJob({
                    state: "processing",
                    page: st.page || 0,
                    total: st.total || 0,
                });
                timer = setTimeout(poll, 2000);
            } catch {
                if (cancelled) return;
                failedPolls += 1;
                if (failedPolls >= 5) {
                    setJob(null);
                    setLayoutLoading(false);
                    setLayoutError("Lost connection to the OCR service. Please retry.");
                    return;
                }
                timer = setTimeout(poll, 3000);
            }
        };

        timer = setTimeout(poll, 1500);
        return () => {
            cancelled = true;
            if (timer) clearTimeout(timer);
        };
    }, [job?.state, documentId, loadLayout]);

    const handleRetry = async () => {
        setLayoutError("");
        setJob(null);
        setLayoutLoading(true);
        try {
            const ok = await loadLayout({ refresh: true });
            if (!ok) return;
            setSaveNotice("Re-extracted!");
            setTimeout(() => setSaveNotice(""), 2000);
        } catch (err) {
            setLayoutError(
                err.response?.data?.details ||
                    err.response?.data?.error ||
                    err.message ||
                    "Failed to restart extraction"
            );
            setLayoutLoading(false);
        }
    };

    const page = layout?.pages?.find((p) => p.page_number === activePage);
    const pw = page?.width || 595.2;
    const ph = page?.height || 841.92;
    const elements = page?.elements || [];
    const activeEl = elements.find((el) => el.id === activeElId);

    const updateElement = (id, patch) => {
        setLayout((prev) => {
            if (!prev) return prev;
            return {
                ...prev,
                pages: prev.pages.map((p) =>
                    p.page_number !== activePage
                        ? p
                        : {
                              ...p,
                              elements: p.elements.map((el) => (el.id === id ? { ...el, ...patch } : el)),
                          }
                ),
            };
        });
        setIsDirty(true);
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await saveDocumentLayout(documentId, layout);
            setIsDirty(false);
            setSaveNotice("Saved!");
            setTimeout(() => setSaveNotice(""), 2000);
        } catch {
            setSaveNotice("Error saving");
            setTimeout(() => setSaveNotice(""), 2000);
        } finally {
            setSaving(false);
        }
    };

    const handleDownload = (format) => {
        const link = document.createElement("a");
        link.href = getExportUrl(documentId, format);
        link.target = "_blank";
        link.click();
    };

    const numPages = docData?.num_pages || layout?.pages?.length || 1;
    const pageNumbers = Array.from({ length: numPages }, (_, i) => i + 1);

    if (loading) {
        return (
            <div className="flex h-screen items-center justify-center bg-gray-50">
                <Loader2 className="animate-spin text-blue-600" size={32} />
                <span className="ml-2 font-medium text-gray-600">
                    {docData?.document_kind === "scanned"
                        ? "Running PaddleOCR on scanned document..."
                        : "Loading document..."}
                </span>
            </div>
        );
    }

    return (
        <div className="flex h-screen w-full flex-col overflow-hidden bg-gray-100 select-none">
            <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 shadow-xs">
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => navigate("/")}
                        className="flex items-center gap-1 text-sm font-medium text-gray-600 hover:text-black cursor-pointer"
                    >
                        <ArrowLeft size={16} />
                        <span>Back</span>
                    </button>
                    <span className="text-gray-300">|</span>
                    <span className="text-sm font-semibold text-gray-800 truncate max-w-xs md:max-w-md">
                        {docData?.file_name || "Document.docx"}
                    </span>
                </div>

                <div className="flex items-center gap-2 border border-gray-200 rounded-md px-2 py-1 bg-gray-50">
                    <button
                        onClick={() => setActivePage((p) => Math.max(1, p - 1))}
                        disabled={activePage <= 1}
                        className="cursor-pointer text-gray-600 hover:text-black disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                        <ChevronLeft size={16} />
                    </button>
                    <span className="text-xs font-semibold text-gray-700 min-w-[75px] text-center">
                        Page {activePage} of {numPages}
                    </span>
                    <button
                        onClick={() => setActivePage((p) => Math.min(numPages, p + 1))}
                        disabled={activePage >= numPages}
                        className="cursor-pointer text-gray-600 hover:text-black disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                        <ChevronRight size={16} />
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    {saveNotice && (
                        <span className="text-xs font-medium text-emerald-600 mr-1">{saveNotice}</span>
                    )}

                    <button
                        onClick={handleSave}
                        disabled={saving || layoutLoading || !layout?.pages?.length}
                        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold text-white transition cursor-pointer disabled:cursor-not-allowed disabled:opacity-60 ${
                            isDirty ? "bg-blue-600 hover:bg-blue-700" : "bg-gray-800 hover:bg-gray-900"
                        }`}
                    >
                        {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                        <span>{saving ? "Saving..." : isDirty ? "Save *" : "Saved"}</span>
                    </button>

                    <button
                        onClick={() => handleDownload("docx")}
                        className="flex items-center gap-1.5 bg-[#2b579a] hover:bg-[#1e3f70] text-white px-3 py-1.5 rounded-md text-xs font-semibold cursor-pointer"
                        title="Download Word Document"
                    >
                        <Download size={13} />
                        <span>Word (.docx)</span>
                    </button>

                    <button
                        onClick={() => handleDownload("pdf")}
                        className="border border-gray-200 hover:bg-gray-50 px-2.5 py-1.5 rounded-md text-xs font-medium text-gray-700 cursor-pointer"
                        title="Download PDF"
                    >
                        PDF
                    </button>
                </div>
            </header>

            <main className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2 gap-3 p-3">
                <section className="flex min-h-0 flex-col rounded-lg border border-gray-200 bg-white overflow-hidden shadow-xs">
                    <div className="flex h-10 items-center justify-between border-b border-gray-200 px-3 bg-gray-50">
                        <span className="text-xs font-bold uppercase tracking-wider text-gray-600">
                            Original Source (Page {activePage})
                        </span>

                        <div className="flex items-center gap-1">
                            <button
                                onClick={() => setScale((s) => Math.max(0.5, s - 0.08))}
                                className="p-1 text-gray-500 hover:text-black rounded hover:bg-gray-200 cursor-pointer"
                                title="Zoom out"
                            >
                                <ZoomOut size={13} />
                            </button>
                            <span className="text-[11px] font-medium text-gray-600 min-w-[32px] text-center">
                                {Math.round(scale * 100)}%
                            </span>
                            <button
                                onClick={() => setScale((s) => Math.min(1.5, s + 0.08))}
                                className="p-1 text-gray-500 hover:text-black rounded hover:bg-gray-200 cursor-pointer"
                                title="Zoom in"
                            >
                                <ZoomIn size={13} />
                            </button>
                            <button
                                onClick={() => setScale(0.85)}
                                className="p-1 text-gray-500 hover:text-black rounded hover:bg-gray-200 cursor-pointer"
                                title="Fit page"
                            >
                                <Maximize2 size={13} />
                            </button>
                        </div>
                    </div>

                    <div className="flex min-h-0 flex-1">
                        <PageSidebar
                            docId={documentId}
                            pageNumbers={pageNumbers}
                            activePage={activePage}
                            onSelect={setActivePage}
                            isOpen={showLeftPages}
                            onToggle={() => setShowLeftPages(!showLeftPages)}
                            isRight={false}
                        />

                        <div className="flex min-w-0 flex-1 items-start justify-center overflow-auto bg-gray-200 p-3 select-text">
                            <div
                                className="relative bg-white shadow-md border border-gray-300 select-text cursor-text"
                                style={{ width: `${pw * scale}px`, height: `${ph * scale}px` }}
                            >
                                <img
                                    src={getPageImageUrl(documentId, activePage)}
                                    alt=""
                                    className="block h-full w-full pointer-events-none"
                                />

                                <div className="absolute inset-0 pointer-events-auto select-text cursor-text">
                                    {elements.map((el) => {
                                        if (el.type === "image" || !el.text) return null;
                                        return (
                                            <span
                                                key={el.id}
                                                style={{
                                                    position: "absolute",
                                                    left: `${(el.bbox.x / pw) * 100}%`,
                                                    top: `${(el.bbox.y / ph) * 100}%`,
                                                    width: `${(el.bbox.width / pw) * 100}%`,
                                                    height: `${(el.bbox.height / ph) * 100}%`,
                                                    fontSize: `${(el.style?.fontSize || 12) * scale}px`,
                                                    fontFamily: el.style?.fontFamily || "serif",
                                                    color: "transparent",
                                                    userSelect: "text",
                                                    cursor: "text",
                                                    whiteSpace: "nowrap",
                                                }}
                                                className="selection:bg-blue-300/60 selection:text-blue-900"
                                            >
                                                {el.text}
                                            </span>
                                        );
                                    })}
                                </div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="flex min-h-0 flex-col rounded-lg border border-gray-200 bg-white overflow-hidden shadow-xs">
                    <div className="flex items-center justify-between border-b border-gray-200 px-3 py-1.5 bg-gray-50 text-xs text-gray-700">
                        <div className="flex items-center gap-1.5">
                            <select
                                value={activeEl?.style?.fontSize ? Math.round(activeEl.style.fontSize) : 14}
                                onChange={(e) =>
                                    updateElement(activeElId, {
                                        style: { ...activeEl?.style, fontSize: Number(e.target.value) },
                                    })
                                }
                                className="rounded border border-gray-200 bg-white px-2 py-1 text-xs outline-none"
                            >
                                {[10, 12, 14, 16, 18, 20, 22, 26].map((sz) => (
                                    <option key={sz} value={sz}>{sz}</option>
                                ))}
                            </select>

                            <button
                                onClick={() =>
                                    updateElement(activeElId, {
                                        style: { ...activeEl?.style, bold: !activeEl?.style?.bold },
                                    })
                                }
                                className={`rounded p-1 cursor-pointer ${
                                    activeEl?.style?.bold ? "bg-blue-100 text-blue-700" : "hover:bg-gray-200"
                                }`}
                                title="Bold"
                            >
                                <Bold size={14} />
                            </button>

                            <button
                                onClick={() =>
                                    updateElement(activeElId, {
                                        style: { ...activeEl?.style, italic: !activeEl?.style?.italic },
                                    })
                                }
                                className={`rounded p-1 cursor-pointer ${
                                    activeEl?.style?.italic ? "bg-blue-100 text-blue-700" : "hover:bg-gray-200"
                                }`}
                                title="Italic"
                            >
                                <Italic size={14} />
                            </button>

                            <div className="h-4 w-[1px] bg-gray-200 mx-0.5" />

                            <button
                                onClick={() =>
                                    updateElement(activeElId, {
                                        style: { ...activeEl?.style, align: "left" },
                                    })
                                }
                                className="rounded p-1 hover:bg-gray-200 cursor-pointer"
                                title="Align Left"
                            >
                                <AlignLeft size={14} />
                            </button>
                            <button
                                onClick={() =>
                                    updateElement(activeElId, {
                                        style: { ...activeEl?.style, align: "center" },
                                    })
                                }
                                className="rounded p-1 hover:bg-gray-200 cursor-pointer"
                                title="Align Center"
                            >
                                <AlignCenter size={14} />
                            </button>
                            <button
                                onClick={() =>
                                    updateElement(activeElId, {
                                        style: { ...activeEl?.style, align: "right" },
                                    })
                                }
                                className="rounded p-1 hover:bg-gray-200 cursor-pointer"
                                title="Align Right"
                            >
                                <AlignRight size={14} />
                            </button>
                        </div>

                        <span className="text-[11px] text-gray-400">Click any text to edit directly</span>
                    </div>

                    <div className="flex min-h-0 flex-1">
                        <div
                            className="min-w-0 flex-1 overflow-auto bg-gray-200 p-3 select-text cursor-text flex justify-center items-start"
                            onClick={(e) => {
                                if (e.target === e.currentTarget) setActiveElId(null);
                            }}
                        >
                            <div
                                className="relative bg-white shadow-md border border-gray-300 select-text cursor-text"
                                style={{
                                    width: `${pw * scale}px`,
                                    height: `${ph * scale}px`,
                                    fontFamily: '"Times New Roman", Times, serif',
                                }}
                            >
                                {layoutLoading && (
                                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-1 bg-white/85 text-sm text-gray-600">
                                        <div className="flex items-center">
                                            <Loader2 className="mr-2 animate-spin text-blue-600" size={18} />
                                            {job?.state === "processing"
                                                ? "Running PaddleOCR..."
                                                : "Extracting text..."}
                                        </div>
                                        {job?.state === "processing" && (
                                            <span className="text-xs text-gray-500">
                                                Page {Math.max(job.page || 1, 1)} of {job.total || numPages}
                                            </span>
                                        )}
                                    </div>
                                )}
                                {!layoutLoading && layoutError && (
                                    <div className="absolute inset-0 z-20 flex flex-col items-center justify-center gap-3 p-6 text-center text-sm text-red-600">
                                        <span>{layoutError}</span>
                                        <button
                                            onClick={handleRetry}
                                            className="flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-700 cursor-pointer"
                                        >
                                            <RefreshCw size={13} />
                                            Retry extraction
                                        </button>
                                    </div>
                                )}
                                {elements.map((el) => {
                                    if (el.type === "fill") {
                                        return (
                                            <div
                                                key={el.id}
                                                style={{
                                                    position: "absolute",
                                                    left: `${(el.bbox.x / pw) * 100}%`,
                                                    top: `${(el.bbox.y / ph) * 100}%`,
                                                    width: `${(el.bbox.width / pw) * 100}%`,
                                                    height: `${(el.bbox.height / ph) * 100}%`,
                                                    backgroundColor: el.color,
                                                    zIndex: 1,
                                                    pointerEvents: "none",
                                                }}
                                            />
                                        );
                                    }

                                    if (el.type === 'line') return null;
                                    if (el.type === "image") {
                                        if (el.isBackground) return null;
                                        const imgW = el.bbox?.width || 100;
                                        const imgH = el.bbox?.height || 50;

                                        return (
                                            <div
                                                key={el.id}
                                                style={{
                                                    position: "absolute",
                                                    left: `${(el.bbox.x / pw) * 100}%`,
                                                    top: `${(el.bbox.y / ph) * 100}%`,
                                                    width: `${(imgW / pw) * 100}%`,
                                                    height: `${(imgH / ph) * 100}%`,
                                                    zIndex: 3,
                                                    pointerEvents: "none",
                                                }}
                                                className="flex items-center justify-center"
                                            >
                                                <img
                                                    src={el.src}
                                                    alt="Graphic"
                                                    style={{ width: "100%", height: "100%", objectFit: "contain" }}
                                                    className="block"
                                                />
                                            </div>
                                        );
                                    }

                                    return (
                                        <div
                                            key={el.id}
                                            contentEditable={true}
                                            suppressContentEditableWarning={true}
                                            title={
                                                el.confidence != null && el.confidence < 0.8
                                                    ? `Low OCR confidence: ${Math.round(el.confidence * 100)}%`
                                                    : undefined
                                            }
                                            onClick={() => setActiveElId(el.id)}
                                            onFocus={() => setActiveElId(el.id)}
                                            onBlur={(e) => {
                                                const txt = e.currentTarget.innerText.trim();
                                                if (txt !== el.text) updateElement(el.id, { text: txt });
                                            }}
                                            style={{
                                                position: "absolute",
                                                left: `${(el.bbox.x / pw) * 100}%`,
                                                top: `${(el.bbox.y / ph) * 100}%`,
                                                width: `${(Math.max(pw - el.bbox.x, 24) / pw) * 100}%`,
                                                fontSize: `${(el.style?.fontSize || 14) * scale}px`,
                                                fontFamily: el.style?.fontFamily || '"Times New Roman", Times, serif',
                                                fontWeight: el.style?.bold ? "bold" : "normal",
                                                fontStyle: el.style?.italic ? "italic" : "normal",
                                                color: el.style?.color || "#000000",
                                                lineHeight: 1.15,
                                                whiteSpace: "pre-wrap",
                                                overflowWrap: "anywhere",
                                                outline: "none",
                                                border: "none",
                                                borderBottom:
                                                    el.confidence != null && el.confidence < 0.8
                                                        ? "2px dotted #f59e0b"
                                                        : "none",
                                                cursor: "text",
                                                zIndex: 10,
                                            }}
                                        >
                                            {el.text}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>

                        <PageSidebar
                            docId={documentId}
                            pageNumbers={pageNumbers}
                            activePage={activePage}
                            onSelect={setActivePage}
                            isOpen={showRightPages}
                            onToggle={() => setShowRightPages(!showRightPages)}
                            isRight={true}
                        />
                    </div>
                </section>
            </main>
        </div>
    );
}

export default DocumentViewer;
