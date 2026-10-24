import { Routes, Route, Navigate } from "react-router-dom";
import Home from "./pages/Home";
import DocumentViewer from "./pages/DocumentViewer";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/document/:id" element={<DocumentViewer />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;