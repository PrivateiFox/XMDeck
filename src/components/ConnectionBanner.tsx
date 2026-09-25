import { FC } from "react";
import { PanelSectionRow } from "@decky/ui";
import { FaExclamationTriangle, FaHeadphones } from "react-icons/fa";
import { ConnectionStatus } from "../types";

interface ConnectionBannerProps {
  status: ConnectionStatus;
}

export const ConnectionBanner: FC<ConnectionBannerProps> = ({ status }) => {
  if (status.is_busy) {
    return (
      <PanelSectionRow>
        <div
          style={{
            backgroundColor: "rgba(220, 100, 20, 0.2)",
            border: "1px solid #d46b08",
            borderRadius: "6px",
            padding: "12px",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
            fontSize: "12px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <FaExclamationTriangle size={24} color="#fa8c16" />
            <div>
              <strong style={{ fontSize: "13px" }}>RFCOMM Port Busy / In Use</strong>
              <div style={{ marginTop: "4px", color: "#ddd" }}>
                Sony headphones only allow one active control connection at a time. If your headphones are
                currently connected to the Sony Sound Connect / Headphones Connect app on your smartphone,
                the RFCOMM channel is locked.
              </div>
            </div>
          </div>
          <div style={{ backgroundColor: "rgba(0, 0, 0, 0.2)", padding: "6px 8px", borderRadius: "4px" }}>
            💡 <strong>Quick Fix:</strong> Turn off Bluetooth on your phone for 10 seconds or close the Sony
            app so Steam Deck can connect.
          </div>
        </div>
      </PanelSectionRow>
    );
  }

  if (!status.connected) {
    return (
      <PanelSectionRow>
        <div
          style={{
            backgroundColor: "rgba(35, 38, 46, 0.7)",
            border: "1px solid rgba(255, 255, 255, 0.12)",
            borderRadius: "8px",
            padding: "18px 14px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            textAlign: "center",
            gap: "10px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
              gap: "6px",
            }}
          >
            <FaHeadphones size={30} color="#3b82f6" style={{ opacity: 0.85 }} />
            <div style={{ fontWeight: 600, fontSize: "14px" }}>No Sony Headphones Connected</div>
            <div style={{ fontSize: "12px", color: "#9ca3af", lineHeight: "1.4" }}>
              Turn on and connect your WH-1000XM or WF-1000XM headphones in SteamOS Bluetooth settings.
            </div>
          </div>

          {status.last_error && (
            <div
              style={{
                width: "100%",
                backgroundColor: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "6px",
                padding: "8px 10px",
                fontSize: "11px",
                color: "#fca5a5",
                wordBreak: "break-word",
                textAlign: "left",
              }}
            >
              <strong>Status:</strong> {status.last_error}
            </div>
          )}

          {status.mac && (
            <div style={{ fontSize: "11px", color: "#9ca3af" }}>
              Last device: <strong>{status.device_name || "Sony Headphones"}</strong> ({status.mac})
            </div>
          )}
        </div>
      </PanelSectionRow>
    );
  }

  return null;
};
