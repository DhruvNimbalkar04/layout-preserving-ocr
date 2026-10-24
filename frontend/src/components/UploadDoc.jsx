import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, Globe, Upload, Loader2, ScanLine, FileType } from "lucide-react";
import { uploadDocument } from "../services/api";
import FilePreview from "./FilePreview";

const UploadDoc = () => {
  const [activeTab, setActiveTab] = useState("convert");
  const [documentKind, setDocumentKind] = useState("normal");
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadedDocument, setUploadedDocument] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");
  const navigate = useNavigate();

  const handleFileUpload = async (file) => {
    if (!file) return;

    const isImage = /\.(jpg|jpeg|png|heic|webp|bmp|tif|tiff)$/i.test(file.name);
    const kind = isImage ? "scanned" : documentKind;
    if (isImage) setDocumentKind("scanned");

    setSelectedFile(file);
    setErrorMsg("");
    setUploading(true);

    try {
      const data = await uploadDocument(file, kind);
      console.log("Uploaded successfully:", data);
      setUploadedDocument(data);
    } catch (error) {
      console.error("Upload Failed:", error.response?.data || error.message);
      setSelectedFile(null);
      setUploadedDocument(null);
      if (error.code === "ERR_NETWORK" || error.message?.includes("Network Error")) {
        setErrorMsg("Backend server is not running. Please start the Django server (python backend/manage.py runserver).");
      } else {
        setErrorMsg(`Upload failed: ${error.response?.data?.detail || error.message || "Unknown error"}`);
      }
    } finally {
      setUploading(false);
    }
  };

  const handleTypeChange = (event) => {
    const file = event.target.files[0];
    if (file) handleFileUpload(file);
  };

  const handleDrop = (event) => {
    event.preventDefault();
    event.stopPropagation();
    const file = event.dataTransfer.files[0];
    if (file) handleFileUpload(file);
  };

  const handleDragOver = (event) => {
    event.preventDefault();
    event.stopPropagation();
  };

  const handleContinue = () => {
    if (!uploadedDocument?.id) {
      console.error("Document ID missing");
      return;
    }

    sessionStorage.setItem("uploadedDocument", JSON.stringify(uploadedDocument));
    navigate(`/document/${uploadedDocument.id}`);
  };

  return (
    <div className="flex min-h-screen flex-col items-center bg-white pt-12 pb-20 px-4">
      <section className="w-[560px] max-w-[95%] rounded-2xl border border-gray-200 p-8 shadow-sm bg-white">
        <div className="flex items-center justify-center gap-10 border-b border-gray-200">
          <button
            onClick={() => setActiveTab("convert")}
            className={`relative flex items-center gap-3 pb-4 text-[16px] font-medium transition ${
              activeTab === "convert" ? "text-black font-semibold" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <FileText size={20} strokeWidth={1.8} />
            <span>Convert Only</span>
            {activeTab === "convert" && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-green-600 rounded-full" />
            )}
          </button>

          <button
            onClick={() => setActiveTab("translate")}
            className={`relative flex items-center gap-3 pb-4 text-[16px] font-medium transition ${
              activeTab === "translate" ? "text-black font-semibold" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Globe size={20} strokeWidth={1.8} />
            <span>Convert & Translate</span>
            {activeTab === "translate" && (
              <span className="absolute bottom-0 left-0 right-0 h-[2px] bg-green-600 rounded-full" />
            )}
          </button>
        </div>

        {errorMsg && (
          <div className="mt-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm text-center">
            {errorMsg}
          </div>
        )}

        <div className="mt-8">
          <p className="text-[15px] font-semibold text-gray-800">
            What kind of document are you uploading?
          </p>
          <p className="mt-1 text-[13px] text-gray-500">
            Choose scanned if the PDF is a photo or scan. PaddleOCR will read the text.
          </p>

          <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setDocumentKind("normal")}
              disabled={uploading}
              className={`rounded-xl border p-4 text-left transition ${
                documentKind === "normal"
                  ? "border-green-600 bg-green-50 ring-1 ring-green-600"
                  : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <FileType size={20} className={documentKind === "normal" ? "text-green-700" : "text-gray-400"} />
              <p className="mt-2 text-sm font-semibold text-gray-900">Normal PDF</p>
              <p className="mt-1 text-[12px] leading-5 text-gray-500">
                Digital PDF with selectable text. Extract layout without OCR.
              </p>
            </button>

            <button
              type="button"
              onClick={() => setDocumentKind("scanned")}
              disabled={uploading}
              className={`rounded-xl border p-4 text-left transition ${
                documentKind === "scanned"
                  ? "border-green-600 bg-green-50 ring-1 ring-green-600"
                  : "border-gray-200 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <ScanLine size={20} className={documentKind === "scanned" ? "text-green-700" : "text-gray-400"} />
              <p className="mt-2 text-sm font-semibold text-gray-900">Scanned PDF / Image</p>
              <p className="mt-1 text-[12px] leading-5 text-gray-500">
                Photo, scan, or image-only PDF. Run PaddleOCR to detect text.
              </p>
            </button>
          </div>
        </div>

        {!selectedFile ? (
          <div className="mt-8">
            <label
              htmlFor="file-upload"
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              className="flex h-[275px] w-full cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-gray-300 transition hover:border-gray-400 hover:bg-gray-50/50"
            >
              {uploading ? (
                <div className="flex flex-col items-center justify-center">
                  <Loader2 size={40} className="animate-spin text-green-600 mb-3" />
                  <span className="text-base font-medium text-gray-700">
                    {documentKind === "scanned" ? "Uploading for PaddleOCR..." : "Uploading document..."}
                  </span>
                </div>
              ) : (
                <>
                  <Upload size={48} strokeWidth={1.5} className="mb-5 text-gray-400" />
                  <span className="rounded-xl bg-[#111827] px-8 py-4 text-[16px] font-semibold text-white hover:bg-gray-800 transition">
                    Upload Document
                  </span>
                  <p className="mt-5 text-[15px] text-[#64748b]">
                    or drag & drop your file here
                  </p>
                  <p className="mt-2 text-[13px] text-gray-400 font-medium">
                    Supports PDF, JPG, PNG
                  </p>
                </>
              )}

              <input
                id="file-upload"
                type="file"
                className="hidden"
                accept=".pdf,.jpg,.jpeg,.png,.heic,.webp,.bmp"
                onChange={handleTypeChange}
                disabled={uploading}
              />
            </label>
          </div>
        ) : (
          <div className="mt-8">
            {uploading ? (
              <div className="flex h-[200px] flex-col items-center justify-center rounded-2xl border border-gray-200 bg-gray-50 p-6 text-center">
                <Loader2 size={40} className="animate-spin text-green-600 mb-3" />
                <span className="text-base font-semibold text-gray-800">Uploading document...</span>
                <span className="text-xs text-gray-500 mt-1">{selectedFile.name}</span>
              </div>
            ) : (
              <FilePreview
                file={selectedFile}
                documentKind={documentKind}
                onRemove={() => {
                  setSelectedFile(null);
                  setUploadedDocument(null);
                }}
                onContinue={handleContinue}
              />
            )}
          </div>
        )}
      </section>

      <p className="mt-8 max-w-[560px] text-center text-[13px] leading-6 text-[#94a3b8]">
        By uploading a document you agree to our{" "}
        <a href="#" className="underline hover:text-gray-600">
          Terms of Service
        </a>
        . To learn more about how our OCR engine handles your document data, check our{" "}
        <a href="#" className="underline hover:text-gray-600">
          Privacy Policy
        </a>
        .
      </p>
    </div>
  );
};

export default UploadDoc;