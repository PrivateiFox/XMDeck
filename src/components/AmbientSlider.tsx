import { FC } from "react";
import { PanelSectionRow, SliderField, ToggleField } from "@decky/ui";
import { ANCState } from "../types";

export const AmbientSlider: FC<{
  state: ANCState;
  disabled?: boolean;
  onLevelChange: (level: number) => void;
  onVoiceFocusChange: (voiceFocus: boolean) => void;
}> = ({ state, disabled, onLevelChange, onVoiceFocusChange }) => {
  if (state.mode !== "ambient") {
    return null;
  }

  return (
    <>
      <PanelSectionRow>
        <SliderField
          label="Ambient Sound Level"
          disabled={disabled}
          value={state.ambient_level}
          min={1}
          max={20}
          step={1}
          showValue={true}
          onChange={(val) => onLevelChange(val)}
        />
      </PanelSectionRow>
      <PanelSectionRow>
        <ToggleField
          label="Focus on Voice"
          description="Enhances voices while reducing background noise"
          disabled={disabled}
          checked={state.voice_focus}
          onChange={(checked) => onVoiceFocusChange(checked)}
        />
      </PanelSectionRow>
    </>
  );
};
