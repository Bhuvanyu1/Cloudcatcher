import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Layout from "@/components/Layout";
import Dashboard from "@/pages/Dashboard";
import CloudAccounts from "@/pages/CloudAccounts";
import Inventory from "@/pages/Inventory";
import Recommendations from "@/pages/Recommendations";

function App() {
  return (
    <div className="App min-h-screen bg-background">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="accounts" element={<CloudAccounts />} />
            <Route path="inventory" element={<Inventory />} />
            <Route path="recommendations" element={<Recommendations />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster 
        position="top-right" 
        theme="dark"
        toastOptions={{
          style: {
            background: '#050505',
            border: '2px solid #333',
            color: '#fff',
            fontFamily: 'JetBrains Mono, monospace'
          }
        }}
      />
    </div>
  );
}

export default App;
