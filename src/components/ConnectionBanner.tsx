import { FC } from "react";
import { PanelSectionRow } from "@decky/ui";
import { FaExclamationTriangle, FaBluetooth } from "react-icons/fa";
import { ConnectionStatus } from "../types";

export const ConnectionBanner: FC<{ status: ConnectionStatus }> = ({ status }) => {
  if (status.is_busy) {
    return (
      <PanelSectionRow>
        <div style={{
          backgroundColor: "rgba(220, 100, 20, 0.2)",
          border: "1px solid #d46b08",
          borderRadius: "6px",
          padding: "10px",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          fontSize: "12px",
        }}>
          <FaExclamationTriangle size={24} color="#fa8c16" />
          <div>
            <strong>RFCOMM Port Busy</strong>
            <div>Your headphones may be connected to the Sony Headphones Connect smartphone app. Please disconnect from your phone to allow Steam Deck control.</div>
          </div>
        </div>
      </PanelSectionRow>
    );
  }

  if (!status.connected) {
    return (
      <PanelSectionRow>
        <div style={{
          backgroundColor: "rgba(50, 50, 50, 0.4)",
          border: "1px solid rgba(255, 255, 255, 0.15)",
          borderRadius: "6px",
          padding: "12px",
          textAlign: "center",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "6px",
        }}>
          <FaBluetooth size={22} color="#666" style={{ opacity: 0.6 }} />
          <div style={{ fontWeight: 600 }}>No Sony Headphones Connected</div>
          <div style={{ fontSize: "12px", color: "#aaa" }}>
            Connect your WH-1000XM or WF-1000XM headphones via SteamOS Bluetooth Settings to begin.
          </div>
        </div>
      </PanelSectionRow>
    );
  }

  return null;
};
