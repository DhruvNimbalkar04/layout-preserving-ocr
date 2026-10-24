import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getDocuments, deleteDocument } from "../services/api";
import { FileText, Trash2, Clock, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";

const RecentDocuments = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    let isMounted = true;
    const fetchDocs = async () => {
      try {
        const data = await getDocuments();
        if (isMounted) {
          setDocuments(Array.isArray(data) ? data : data.results || []);
        }
      } catch (err) {
        console.error("Failed to load documents list:", err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchDocs();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this document?")) return;
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      console.error("Failed to delete document:", err);
    }
  };

  if (loading) {
    return null;
  }

  if (documents.length === 0) {
    return null;
  }

  return (
    <div className="w-full max-w-4xl mx-auto mt-12 px-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Clock size={20} className="text-gray-600" />
          Recent Documents
        </h2>
        <span className="text-xs text-gray-500 font-medium">
          {documents.length} {documents.length === 1 ? "document" : "documents"} saved
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {documents.map((doc) => {
          const isCompleted = doc.status === "completed";
          const isProcessing = doc.status === "processing" || doc.status === "pending";

          return (
            <div
              key={doc.id}
              onClick={() => navigate(`/document/${doc.id}`)}
              className="group relative flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm hover:border-gray-300 hover:shadow-md transition cursor-pointer"
            >
              <div className="flex items-center gap-3.5 min-w-0">
                <div className="p-3 rounded-lg bg-gray-100 group-hover:bg-gray-200 transition shrink-0">
                  <FileText size={24} className="text-gray-700" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-gray-900 text-sm truncate" title={doc.file_name}>
                    {doc.file_name}
                  </h3>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                    <span>{((doc.file_size || 0) / 1024 / 1024).toFixed(2)} MB</span>
                    <span>•</span>
                    <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3 shrink-0 ml-3">
                {isCompleted && (
                  <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-green-50 text-green-700 border border-green-200">
                    <CheckCircle2 size={12} /> Done
                  </span>
                )}
                {isProcessing && (
                  <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                    <Loader2 size={12} className="animate-spin" /> Processing
                  </span>
                )}
                {!isCompleted && !isProcessing && (
                  <span className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-full bg-red-50 text-red-700 border border-red-200">
                    <AlertCircle size={12} /> Failed
                  </span>
                )}

                <button
                  onClick={(e) => handleDelete(e, doc.id)}
                  className="p-1.5 rounded-lg text-gray-400 hover:text-red-600 hover:bg-red-50 transition cursor-pointer"
                  title="Delete document"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RecentDocuments;
