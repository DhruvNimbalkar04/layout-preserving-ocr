import { FileText, X } from 'lucide-react';

const FilePreview = ({ file, onRemove, onContinue, documentKind }) => {
  return (
    <div className="w-full rounded-2xl border border-gray-200 p-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-gray-100">
            <FileText size={28} className="text-gray-600" />
          </div>

          <div>
            <p className="font-semibold text-gray-900">
              {file.name}
            </p>

            <p className="text-sm text-gray-500">
              {(file.size / 1024 / 1024).toFixed(2)} MB
              {documentKind === "scanned" ? " · Scanned · PaddleOCR" : " · Normal PDF"}
            </p>
          </div>
        </div>

        <button
          onClick={onRemove}
          className="p-2 rounded-lg hover:bg-gray-100 transition cursor-pointer"
          title="Remove file"
        >
          <X size={20} />
        </button>
      </div>

      <button
        onClick={onContinue}
        className="mt-6 w-full bg-[#111827] text-white py-3 rounded-xl font-semibold hover:bg-gray-800 transition cursor-pointer flex items-center justify-center gap-2"
      >
        Continue to Document
      </button>
    </div>
  );
};

export default FilePreview;