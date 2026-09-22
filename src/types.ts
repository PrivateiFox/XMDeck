export type ANCMode = "cancelling" | "ambient" | "off";

export interface ConnectionStatus {
  connected: boolean;
  device_name: string | null;
  battery_level: number | null;
  charging: boolean;
  is_busy: boolean;
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
