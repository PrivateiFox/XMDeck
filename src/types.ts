export type ANCMode = "cancelling" | "ambient" | "off";

export interface BluetoothDeviceInfo {
  mac: string;
  name: string;
  alias: string;
  connected: boolean;
  uuids: string[];
  icon: string;
  is_sony: boolean;
  is_le: boolean;
}

export interface ConnectionStatus {
  connected: boolean;
  device_name: string | null;
  mac?: string | null;
  battery_level: number | null;
  charging: boolean;
  is_busy: boolean;
  last_error?: string | null;
  channel?: number | null;
}

export interface ANCState {
  mode: ANCMode;
  ambient_level: number;
  voice_focus: boolean;
}

export interface PluginStateUpdate {
  event: string;
  connection: ConnectionStatus;
  anc: ANCState;
  speak_to_chat: boolean;
}

export interface DiagnosticsInfo {
  connected: boolean;
  mac: string | null;
  device_name: string | null;
  rfcomm_supported: boolean;
  last_error: string | null;
  channel: number | null;
  devices: BluetoothDeviceInfo[];
}
