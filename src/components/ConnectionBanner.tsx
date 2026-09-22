import { FC, useState } from "react";
import { PanelSectionRow, ButtonItem, TextField } from "@decky/ui";
import { FaExclamationTriangle, FaBluetooth, FaSyncAlt } from "react-icons/fa";
import { ConnectionStatus, BluetoothDeviceInfo } from "../types";

interface ConnectionBannerProps {
  status: ConnectionStatus;
  devices?: BluetoothDeviceInfo[];
  onConnect?: (mac: string) => Promise<void>;
  onScan?: () => Promise<void>;
  disabled?: boolean;
}

export const ConnectionBanner: FC<ConnectionBannerProps> = ({
  status,
  devices = [],
  onConnect,
  onScan,
  disabled = false,
}) => {
  const [manualMac, setManualMac] = useState("");
  const [showManual, setShowManual] = useState(false);

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
            app, then tap <em>Retry Connection</em> below.
          </div>
          {onScan && (
            <ButtonItem
              layout="inline"
              onClick={() => onScan()}
              disabled={disabled}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "6px", justifyContent: "center" }}>
                <FaSyncAlt /> Retry Connection
              </div>
            </ButtonItem>
          )}
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
            padding: "14px",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              textAlign: "center",
              gap: "4px",
            }}
          >
            <FaBluetooth size={24} color="#3b82f6" style={{ opacity: 0.8 }} />
            <div style={{ fontWeight: 600, fontSize: "14px" }}>No Sony Headphones Connected</div>
            <div style={{ fontSize: "11px", color: "#9ca3af" }}>
              Pair and connect your WH-1000XM or WF-1000XM via SteamOS Bluetooth Settings.
            </div>
          </div>

          {status.last_error && (
            <div
              style={{
                backgroundColor: "rgba(239, 68, 68, 0.15)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: "6px",
                padding: "8px 10px",
                fontSize: "11px",
                color: "#fca5a5",
                wordBreak: "break-word",
              }}
            >
              <strong>Status:</strong> {status.last_error}
            </div>
          )}

          {status.mac && (
            <div style={{ fontSize: "11px", color: "#9ca3af", textAlign: "center" }}>
              Last attempted device: <strong>{status.device_name || "Sony Headphones"}</strong> ({status.mac})
            </div>
          )}

          <div style={{ display: "flex", gap: "8px", marginTop: "2px" }}>
            {onScan && (
              <ButtonItem
                layout="below"
                onClick={() => onScan()}
                disabled={disabled}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "6px", justifyContent: "center" }}>
                  <FaSyncAlt /> Scan & Reconnect
                </div>
              </ButtonItem>
            )}
          </div>

          {devices.length > 0 && (
            <div style={{ marginTop: "4px", borderTop: "1px solid rgba(255, 255, 255, 0.08)", paddingTop: "8px" }}>
              <div style={{ fontSize: "11px", fontWeight: 600, color: "#93c5fd", marginBottom: "6px" }}>
                Detected Bluetooth Devices:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {devices.map((dev) => (
                  <div
                    key={dev.mac}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      backgroundColor: dev.is_sony ? "rgba(59, 130, 246, 0.15)" : "rgba(255, 255, 255, 0.04)",
                      border: dev.is_sony ? "1px solid rgba(59, 130, 246, 0.4)" : "1px solid rgba(255, 255, 255, 0.05)",
                      padding: "6px 10px",
                      borderRadius: "6px",
                    }}
                  >
                    <div style={{ display: "flex", flexDirection: "column", maxWidth: "60%" }}>
                      <span style={{ fontSize: "12px", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {dev.name || dev.alias || dev.mac}
                      </span>
                      <span style={{ fontSize: "10px", color: "#9ca3af" }}>
                        {dev.mac} {dev.connected ? "• Connected" : "• Paired"} {dev.is_sony ? "• Sony MDR" : ""}
                      </span>
                    </div>
                    {onConnect && (
                      <button
                        onClick={() => onConnect(dev.mac)}
                        disabled={disabled}
                        style={{
                          backgroundColor: "#2563eb",
                          color: "#fff",
                          border: "none",
                          borderRadius: "4px",
                          padding: "4px 10px",
                          fontSize: "11px",
                          cursor: "pointer",
                        }}
                      >
                        Connect
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: "4px", textAlign: "center" }}>
            <button
              onClick={() => setShowManual(!showManual)}
              style={{
                background: "none",
                border: "none",
                color: "#60a5fa",
                fontSize: "11px",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              {showManual ? "Hide Manual Connect" : "Manual MAC Address Connect"}
            </button>
          </div>

          {showManual && (
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <TextField
                label="Bluetooth MAC Address"
                value={manualMac}
                onChange={(e) => setManualMac(e.target.value)}
              />
              {onConnect && (
                <ButtonItem
                  layout="below"
                  onClick={() => {
                    if (manualMac.trim()) {
                      onConnect(manualMac.trim());
                    }
                  }}
                  disabled={disabled || !manualMac.trim()}
                >
                  Connect to MAC
                </ButtonItem>
              )}
            </div>
          )}
        </div>
      </PanelSectionRow>
    );
  }

  return null;
};
