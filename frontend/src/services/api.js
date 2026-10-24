import axios from "axios";

const API_ORIGIN = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

export const BASE_URL = API_ORIGIN;

const API = axios.create({
    baseURL: `${API_ORIGIN}/api/`,
});

export const getMediaUrl = (fileUrl) => {
    if (!fileUrl) return "";
    if (fileUrl.startsWith("http://") || fileUrl.startsWith("https://")) {
        return fileUrl;
    }
    return fileUrl.startsWith("/") ? fileUrl : `/${fileUrl}`;
};

export const getPageImageUrl = (id, pageNum) => {
    return `${API_ORIGIN}/api/documents/${id}/pages/${pageNum}/`;
};

export const getExportUrl = (id, format = "pdf") => {
    return `${API_ORIGIN}/api/documents/${id}/export/?export_format=${format}`;
};

export const uploadDocument = async (file, documentKind = "normal") => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("document_kind", documentKind === "scanned" ? "scanned" : "normal");

    const response = await API.post("documents/", formData);
    return response.data;
};

export const getDocuments = async () => {
    const response = await API.get("documents/");
    return response.data;
};

export const getDocument = async (id) => {
    const response = await API.get(`documents/${id}/`);
    return response.data;
};

export const deleteDocument = async (id) => {
    const response = await API.delete(`documents/${id}/`);
    return response.data;
};

export const getDocumentLayout = async (documentId, { refresh = false } = {}) => {
    const response = await API.get(`documents/${documentId}/layout/`, {
        params: refresh ? { refresh: true } : undefined,
    });
    return { httpStatus: response.status, data: response.data };
};

export const getDocumentStatus = async (documentId) => {
    const response = await API.get(`documents/${documentId}/status/`);
    return response.data;
};

export const saveDocumentLayout = async (documentId, layoutData) => {
    const response = await API.patch(`documents/${documentId}/layout/`, {
        layout_data: layoutData
    });
    return response.data;
};