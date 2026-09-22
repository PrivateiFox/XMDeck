import {
  definePlugin,
  PanelSection,
  staticClasses,
} from "@decky/ui";
import { call, addEventListener, removeEventListener } from "@decky/api";
import { FC, useState, useEffect, useCallback } from "react";
import { FaHeadphones } from "react-icons/fa";

import {
  ANCMode,
  ANCState,
  BluetoothDeviceInfo,
  ConnectionStatus,
  PluginStateUpdate,
} from "./types";
import { ConnectionBanner } from "./components/ConnectionBanner";
import { BatterySection } from "./components/BatteryStatus";
import { ANCControls } from "./components/ANCControls";
import { AmbientSlider } from "./components/AmbientSlider";
import { SpeakToChatToggle } from "./components/SpeakToChatToggle";

const XMDeckPanel: FC = () => {
  const [connection, setConnection] = useState<ConnectionStatus>({
    connected: false,
    device_name: null,
    battery_level: null,
    charging: false,
    is_busy: false,
    last_error: null,
  });

  const [devices, setDevices] = useState<BluetoothDeviceInfo[]>([]);
  const [anc, setAnc] = useState<ANCState>({
    mode: "cancelling",
    ambient_level: 1,
    voice_focus: false,
  });

  const [speakToChat, setSpeakToChat] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch initial statuses from backend daemon
  const refreshStatus = useCallback(async () => {
    try {
      const connStatus = await call<[], ConnectionStatus>("get_connection_status");
      if (connStatus) {
        setConnection(connStatus);
      }

      if (connStatus?.connected) {
        const ancState = await call<[], ANCState>("get_anc_state");
        if (ancState) {
          setAnc(ancState);
        }
      }
    } catch (e) {
      console.error("[XMDeck] Failed refreshing status:", e);
    }
  }, []);

  const fetchDevices = useCallback(async () => {
    try {
      const scanned = await call<[], BluetoothDeviceInfo[]>("scan_devices");
      if (scanned) {
        setDevices(scanned);
      }
    } catch (e) {
      console.error("[XMDeck] Failed scanning Bluetooth devices:", e);
    }
  }, []);

  useEffect(() => {
    refreshStatus();
    fetchDevices();

    const onStateChanged = (update: PluginStateUpdate) => {
      if (update.connection) {
        setConnection(update.connection);
      }
      if (update.anc) {
        setAnc(update.anc);
      }
      if (update.speak_to_chat !== undefined) {
        setSpeakToChat(update.speak_to_chat);
      }
    };

    addEventListener<[PluginStateUpdate]>("xmdeck_state_changed", onStateChanged);

    // Poll periodically as fallback
    const interval = setInterval(() => {
      refreshStatus();
      if (!connection.connected) {
        fetchDevices();
      }
    }, 4000);

    return () => {
      removeEventListener("xmdeck_state_changed", onStateChanged);
      clearInterval(interval);
    };
  }, [refreshStatus, fetchDevices, connection.connected]);

  // Handlers with optimistic UI updates
  const handleModeChange = async (mode: ANCMode) => {
    setAnc((prev) => ({ ...prev, mode }));
    setLoading(true);
    try {
      await call<[string], boolean>("set_anc_mode", mode);
    } catch (e) {
      console.error("[XMDeck] Failed setting ANC mode:", e);
      refreshStatus();
    } finally {
      setLoading(false);
    }
  };

  const handleLevelChange = async (ambient_level: number) => {
    setAnc((prev) => ({ ...prev, ambient_level }));
    try {
      await call<[number, boolean], boolean>("set_ambient_sound", ambient_level, anc.voice_focus);
    } catch (e) {
      console.error("[XMDeck] Failed setting ambient level:", e);
    }
  };

  const handleVoiceFocusChange = async (voice_focus: boolean) => {
    setAnc((prev) => ({ ...prev, voice_focus }));
    try {
      await call<[number, boolean], boolean>("set_ambient_sound", anc.ambient_level, voice_focus);
    } catch (e) {
      console.error("[XMDeck] Failed setting voice focus:", e);
    }
  };

  const handleSpeakToChatChange = async (enabled: boolean) => {
    setSpeakToChat(enabled);
    try {
      await call<[boolean], boolean>("set_speak_to_chat", enabled);
    } catch (e) {
      console.error("[XMDeck] Failed setting Speak-to-Chat:", e);
      refreshStatus();
    }
  };

  const handleManualConnect = async (mac: string) => {
    setLoading(true);
    try {
      await call<[string], boolean>("connect_device", mac);
      await refreshStatus();
    } catch (e) {
      console.error("[XMDeck] Manual connect failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleManualScan = async () => {
    setLoading(true);
    try {
      await call("trigger_connect");
      await fetchDevices();
      await refreshStatus();
    } catch (e) {
      console.error("[XMDeck] Manual scan failed:", e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <PanelSection title="Sony WH/WF Headphones">
      <ConnectionBanner
        status={connection}
        devices={devices}
        onConnect={handleManualConnect}
        onScan={handleManualScan}
        disabled={loading}
      />

      {connection.connected && (
        <>
          <BatterySection status={connection} />

          <ANCControls
            state={anc}
            disabled={loading}
            onModeChange={handleModeChange}
          />

          <AmbientSlider
            state={anc}
            disabled={loading}
            onLevelChange={handleLevelChange}
            onVoiceFocusChange={handleVoiceFocusChange}
          />

          <SpeakToChatToggle
            enabled={speakToChat}
            disabled={loading}
            onChange={handleSpeakToChatChange}
          />
        </>
      )}
    </PanelSection>
  );
};

export default definePlugin(() => {
  return {
    title: <div className={staticClasses.Title}>XMDeck</div>,
    content: <XMDeckPanel />,
    icon: <FaHeadphones />,
    onDismount() {},
  };
});
