import { FC } from "react";
import { PanelSectionRow, ToggleField } from "@decky/ui";

export const SpeakToChatToggle: FC<{
  enabled: boolean;
  disabled?: boolean;
  onChange: (enabled: boolean) => void;
}> = ({ enabled, disabled, onChange }) => {
  return (
    <PanelSectionRow>
      <ToggleField
        label="Speak-to-Chat"
        description="Pauses music and enables ambient sound when you speak"
        disabled={disabled}
        checked={enabled}
        onChange={(checked) => onChange(checked)}
      />
    </PanelSectionRow>
  );
};
