import { FC } from "react";
import { PanelSectionRow, DropdownItem } from "@decky/ui";
import { ANCMode, ANCState } from "../types";

const ANC_OPTIONS = [
  { data: "cancelling", label: "Noise Cancelling" },
  { data: "ambient", label: "Ambient Sound" },
  { data: "off", label: "Off" },
];

export const ANCControls: FC<{
  state: ANCState;
  disabled?: boolean;
  onModeChange: (mode: ANCMode) => void;
}> = ({ state, disabled, onModeChange }) => {
  return (
    <PanelSectionRow>
      <DropdownItem
        label="Noise Control"
        disabled={disabled}
        rgOptions={ANC_OPTIONS}
        selectedOption={state.mode}
        onChange={(option) => onModeChange(option.data as ANCMode)}
      />
    </PanelSectionRow>
  );
};
