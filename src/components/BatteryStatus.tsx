import { FC } from "react";
import { PanelSectionRow } from "@decky/ui";
import {
  FaBatteryFull,
  FaBatteryThreeQuarters,
  FaBatteryHalf,
  FaBatteryQuarter,
  FaBatteryEmpty,
  FaBolt,
} from "react-icons/fa";
import { ConnectionStatus } from "../types";

export const BatterySection: FC<{ status: ConnectionStatus }> = ({ status }) => {
  if (!status.connected) {
    return null;
  }

  const level = status.battery_level;

  const renderBatteryIcon = () => {
    if (level === null || level === undefined) return <FaBatteryEmpty size={18} color="#888" />;
    if (level > 80) return <FaBatteryFull size={18} color="#52c41a" />;
    if (level > 50) return <FaBatteryThreeQuarters size={18} color="#52c41a" />;
    if (level > 25) return <FaBatteryHalf size={18} color="#faad14" />;
    if (level > 10) return <FaBatteryQuarter size={18} color="#f5222d" />;
    return <FaBatteryEmpty size={18} color="#f5222d" />;
  };

  return (
    <PanelSectionRow>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        width: "100%",
        padding: "4px 0",
      }}>
        <div style={{ display: "flex", flexDirection: "column" }}>
          <span style={{ fontWeight: 600, fontSize: "14px" }}>
            {status.device_name || "Sony Headphones"}
          </span>
          <span style={{ fontSize: "11px", color: "#8b949e" }}>Connected via RFCOMM</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {status.charging && <FaBolt size={14} color="#fadb14" title="Charging" />}
          {renderBatteryIcon()}
          <span style={{ fontWeight: 600, fontSize: "14px" }}>
            {level !== null && level !== undefined ? `${level}%` : "—"}
          </span>
        </div>
      </div>
    </PanelSectionRow>
  );
};
