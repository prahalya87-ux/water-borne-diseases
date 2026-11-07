import { Route, Routes } from "react-router-dom";
import Home from "./pages/home";
import Dashboard from "./pages/dashboard";
import MapPage from "./pages/mappage";
import WaterQuality from "./pages/waterquality";
import Report from "./pages/report";
import Track from "./pages/track";
import Login from "./pages/login";
import Admin from "./pages/admin";
import Alerts from "./pages/alerts";
import Assistant from "./pages/assistant";
import Prediction from "./pages/prediction";
import Diseases from "./pages/diseases";
import Hospitals from "./pages/hospitals";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/map" element={<MapPage />} />
      <Route path="/hospitals" element={<Hospitals />} />
      <Route path="/water-quality" element={<WaterQuality />} />
      <Route path="/report" element={<Report />} />
      <Route path="/login" element={<Login />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/alerts" element={<Alerts />} />
      <Route path="/assistant" element={<Assistant />} />
      <Route path="/prediction" element={<Prediction />} />
      <Route path="/diseases" element={<Diseases />} />
      <Route path="/diseases/:slug" element={<Diseases />} />
      <Route path="/track" element={<Track />} />
      <Route path="/track/:code" element={<Track />} />
      <Route path="*" element={<div className="p-10 text-center">Page not found. <a className="text-aqua-600 underline" href="/">Go home</a></div>} />
    </Routes>
  );
}