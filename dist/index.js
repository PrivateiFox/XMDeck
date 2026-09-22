const manifest = {"name":"XMDeck"};
const API_VERSION = 2;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
let api;
try {
    api = internalAPIConnection.connect(API_VERSION, manifest.name);
}
catch {
    api = internalAPIConnection.connect(1, manifest.name);
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version 1. Some features may not work.`);
}
if (api._version != API_VERSION) {
    console.warn(`[@decky/api] Requested API version ${API_VERSION} but the running loader only supports version ${api._version}. Some features may not work.`);
}
const call = api.call;
const addEventListener = api.addEventListener;
const removeEventListener = api.removeEventListener;

var DefaultContext = {
  color: undefined,
  size: undefined,
  className: undefined,
  style: undefined,
  attr: undefined
};
var IconContext = SP_REACT.createContext && /*#__PURE__*/SP_REACT.createContext(DefaultContext);

var _excluded = ["attr", "size", "title"];
function _objectWithoutProperties(e, t) { if (null == e) return {}; var o, r, i = _objectWithoutPropertiesLoose(e, t); if (Object.getOwnPropertySymbols) { var n = Object.getOwnPropertySymbols(e); for (r = 0; r < n.length; r++) o = n[r], -1 === t.indexOf(o) && {}.propertyIsEnumerable.call(e, o) && (i[o] = e[o]); } return i; }
function _objectWithoutPropertiesLoose(r, e) { if (null == r) return {}; var t = {}; for (var n in r) if ({}.hasOwnProperty.call(r, n)) { if (-1 !== e.indexOf(n)) continue; t[n] = r[n]; } return t; }
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
function ownKeys(e, r) { var t = Object.keys(e); if (Object.getOwnPropertySymbols) { var o = Object.getOwnPropertySymbols(e); r && (o = o.filter(function (r) { return Object.getOwnPropertyDescriptor(e, r).enumerable; })), t.push.apply(t, o); } return t; }
function _objectSpread(e) { for (var r = 1; r < arguments.length; r++) { var t = null != arguments[r] ? arguments[r] : {}; r % 2 ? ownKeys(Object(t), true).forEach(function (r) { _defineProperty(e, r, t[r]); }) : Object.getOwnPropertyDescriptors ? Object.defineProperties(e, Object.getOwnPropertyDescriptors(t)) : ownKeys(Object(t)).forEach(function (r) { Object.defineProperty(e, r, Object.getOwnPropertyDescriptor(t, r)); }); } return e; }
function _defineProperty(e, r, t) { return (r = _toPropertyKey(r)) in e ? Object.defineProperty(e, r, { value: t, enumerable: true, configurable: true, writable: true }) : e[r] = t, e; }
function _toPropertyKey(t) { var i = _toPrimitive(t, "string"); return "symbol" == typeof i ? i : i + ""; }
function _toPrimitive(t, r) { if ("object" != typeof t || !t) return t; var e = t[Symbol.toPrimitive]; if (void 0 !== e) { var i = e.call(t, r); if ("object" != typeof i) return i; throw new TypeError("@@toPrimitive must return a primitive value."); } return ("string" === r ? String : Number)(t); }
function Tree2Element(tree) {
  return tree && tree.map((node, i) => /*#__PURE__*/SP_REACT.createElement(node.tag, _objectSpread({
    key: i
  }, node.attr), Tree2Element(node.child)));
}
function GenIcon(data) {
  return props => /*#__PURE__*/SP_REACT.createElement(IconBase, _extends({
    attr: _objectSpread({}, data.attr)
  }, props), Tree2Element(data.child));
}
function IconBase(props) {
  var elem = conf => {
    var attr = props.attr,
      size = props.size,
      title = props.title,
      svgProps = _objectWithoutProperties(props, _excluded);
    var computedSize = size || conf.size || "1em";
    var className;
    if (conf.className) className = conf.className;
    if (props.className) className = (className ? className + " " : "") + props.className;
    return /*#__PURE__*/SP_REACT.createElement("svg", _extends({
      stroke: "currentColor",
      fill: "currentColor",
      strokeWidth: "0"
    }, conf.attr, attr, svgProps, {
      className: className,
      style: _objectSpread(_objectSpread({
        color: props.color || conf.color
      }, conf.style), props.style),
      height: computedSize,
      width: computedSize,
      xmlns: "http://www.w3.org/2000/svg"
    }), title && /*#__PURE__*/SP_REACT.createElement("title", null, title), props.children);
  };
  return IconContext !== undefined ? /*#__PURE__*/SP_REACT.createElement(IconContext.Consumer, null, conf => elem(conf)) : elem(DefaultContext);
}

// THIS FILE IS AUTO GENERATED
function FaBluetooth (props) {
  return GenIcon({"attr":{"viewBox":"0 0 448 512"},"child":[{"tag":"path","attr":{"d":"M292.6 171.1L249.7 214l-.3-86 43.2 43.1m-43.2 219.8l43.1-43.1-42.9-42.9-.2 86zM416 259.4C416 465 344.1 512 230.9 512S32 465 32 259.4 115.4 0 228.6 0 416 53.9 416 259.4zm-158.5 0l79.4-88.6L211.8 36.5v176.9L138 139.6l-27 26.9 92.7 93-92.7 93 26.9 26.9 73.8-73.8 2.3 170 127.4-127.5-83.9-88.7z"},"child":[]}]})(props);
}function FaSyncAlt (props) {
  return GenIcon({"attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M370.72 133.28C339.458 104.008 298.888 87.962 255.848 88c-77.458.068-144.328 53.178-162.791 126.85-1.344 5.363-6.122 9.15-11.651 9.15H24.103c-7.498 0-13.194-6.807-11.807-14.176C33.933 94.924 134.813 8 256 8c66.448 0 126.791 26.136 171.315 68.685L463.03 40.97C478.149 25.851 504 36.559 504 57.941V192c0 13.255-10.745 24-24 24H345.941c-21.382 0-32.09-25.851-16.971-40.971l41.75-41.749zM32 296h134.059c21.382 0 32.09 25.851 16.971 40.971l-41.75 41.75c31.262 29.273 71.835 45.319 114.876 45.28 77.418-.07 144.315-53.144 162.787-126.849 1.344-5.363 6.122-9.15 11.651-9.15h57.304c7.498 0 13.194 6.807 11.807 14.176C478.067 417.076 377.187 504 256 504c-66.448 0-126.791-26.136-171.315-68.685L48.97 471.03C33.851 486.149 8 475.441 8 454.059V320c0-13.255 10.745-24 24-24z"},"child":[]}]})(props);
}function FaHeadphones (props) {
  return GenIcon({"attr":{"viewBox":"0 0 512 512"},"child":[{"tag":"path","attr":{"d":"M256 32C114.52 32 0 146.496 0 288v48a32 32 0 0 0 17.689 28.622l14.383 7.191C34.083 431.903 83.421 480 144 480h24c13.255 0 24-10.745 24-24V280c0-13.255-10.745-24-24-24h-24c-31.342 0-59.671 12.879-80 33.627V288c0-105.869 86.131-192 192-192s192 86.131 192 192v1.627C427.671 268.879 399.342 256 368 256h-24c-13.255 0-24 10.745-24 24v176c0 13.255 10.745 24 24 24h24c60.579 0 109.917-48.098 111.928-108.187l14.382-7.191A32 32 0 0 0 512 336v-48c0-141.479-114.496-256-256-256z"},"child":[]}]})(props);
}function FaExclamationTriangle (props) {
  return GenIcon({"attr":{"viewBox":"0 0 576 512"},"child":[{"tag":"path","attr":{"d":"M569.517 440.013C587.975 472.007 564.806 512 527.94 512H48.054c-36.937 0-59.999-40.055-41.577-71.987L246.423 23.985c18.467-32.009 64.72-31.951 83.154 0l239.94 416.028zM288 354c-25.405 0-46 20.595-46 46s20.595 46 46 46 46-20.595 46-46-20.595-46-46-46zm-43.673-165.346l7.418 136c.347 6.364 5.609 11.346 11.982 11.346h48.546c6.373 0 11.635-4.982 11.982-11.346l7.418-136c.375-6.874-5.098-12.654-11.982-12.654h-63.383c-6.884 0-12.356 5.78-11.981 12.654z"},"child":[]}]})(props);
}function FaBolt (props) {
  return GenIcon({"attr":{"viewBox":"0 0 320 512"},"child":[{"tag":"path","attr":{"d":"M296 160H180.6l42.6-129.8C227.2 15 215.7 0 200 0H56C44 0 33.8 8.9 32.2 20.8l-32 240C-1.7 275.2 9.5 288 24 288h118.7L96.6 482.5c-3.6 15.2 8 29.5 23.3 29.5 8.4 0 16.4-4.4 20.8-12l176-304c9.3-15.9-2.2-36-20.7-36z"},"child":[]}]})(props);
}function FaBatteryThreeQuarters (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M544 160v64h32v64h-32v64H64V160h480m16-64H48c-26.51 0-48 21.49-48 48v224c0 26.51 21.49 48 48 48h512c26.51 0 48-21.49 48-48v-16h8c13.255 0 24-10.745 24-24V184c0-13.255-10.745-24-24-24h-8v-16c0-26.51-21.49-48-48-48zm-144 96H96v128h320V192z"},"child":[]}]})(props);
}function FaBatteryQuarter (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M544 160v64h32v64h-32v64H64V160h480m16-64H48c-26.51 0-48 21.49-48 48v224c0 26.51 21.49 48 48 48h512c26.51 0 48-21.49 48-48v-16h8c13.255 0 24-10.745 24-24V184c0-13.255-10.745-24-24-24h-8v-16c0-26.51-21.49-48-48-48zm-336 96H96v128h128V192z"},"child":[]}]})(props);
}function FaBatteryHalf (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M544 160v64h32v64h-32v64H64V160h480m16-64H48c-26.51 0-48 21.49-48 48v224c0 26.51 21.49 48 48 48h512c26.51 0 48-21.49 48-48v-16h8c13.255 0 24-10.745 24-24V184c0-13.255-10.745-24-24-24h-8v-16c0-26.51-21.49-48-48-48zm-240 96H96v128h224V192z"},"child":[]}]})(props);
}function FaBatteryFull (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M544 160v64h32v64h-32v64H64V160h480m16-64H48c-26.51 0-48 21.49-48 48v224c0 26.51 21.49 48 48 48h512c26.51 0 48-21.49 48-48v-16h8c13.255 0 24-10.745 24-24V184c0-13.255-10.745-24-24-24h-8v-16c0-26.51-21.49-48-48-48zm-48 96H96v128h416V192z"},"child":[]}]})(props);
}function FaBatteryEmpty (props) {
  return GenIcon({"attr":{"viewBox":"0 0 640 512"},"child":[{"tag":"path","attr":{"d":"M544 160v64h32v64h-32v64H64V160h480m16-64H48c-26.51 0-48 21.49-48 48v224c0 26.51 21.49 48 48 48h512c26.51 0 48-21.49 48-48v-16h8c13.255 0 24-10.745 24-24V184c0-13.255-10.745-24-24-24h-8v-16c0-26.51-21.49-48-48-48z"},"child":[]}]})(props);
}

const ConnectionBanner = ({ status, devices = [], onConnect, onScan, disabled = false, }) => {
    const [manualMac, setManualMac] = SP_REACT.useState("");
    const [showManual, setShowManual] = SP_REACT.useState(false);
    if (status.is_busy) {
        return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: {
                    backgroundColor: "rgba(220, 100, 20, 0.2)",
                    border: "1px solid #d46b08",
                    borderRadius: "6px",
                    padding: "12px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "8px",
                    fontSize: "12px",
                }, children: [SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "10px" }, children: [SP_JSX.jsx(FaExclamationTriangle, { size: 24, color: "#fa8c16" }), SP_JSX.jsxs("div", { children: [SP_JSX.jsx("strong", { style: { fontSize: "13px" }, children: "RFCOMM Port Busy / In Use" }), SP_JSX.jsx("div", { style: { marginTop: "4px", color: "#ddd" }, children: "Sony headphones only allow one active control connection at a time. If your headphones are currently connected to the Sony Sound Connect / Headphones Connect app on your smartphone, the RFCOMM channel is locked." })] })] }), SP_JSX.jsxs("div", { style: { backgroundColor: "rgba(0, 0, 0, 0.2)", padding: "6px 8px", borderRadius: "4px" }, children: ["\uD83D\uDCA1 ", SP_JSX.jsx("strong", { children: "Quick Fix:" }), " Turn off Bluetooth on your phone for 10 seconds or close the Sony app, then tap ", SP_JSX.jsx("em", { children: "Retry Connection" }), " below."] }), onScan && (SP_JSX.jsx(DFL.ButtonItem, { layout: "inline", onClick: () => onScan(), disabled: disabled, children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "6px", justifyContent: "center" }, children: [SP_JSX.jsx(FaSyncAlt, {}), " Retry Connection"] }) }))] }) }));
    }
    if (!status.connected) {
        return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: {
                    backgroundColor: "rgba(35, 38, 46, 0.7)",
                    border: "1px solid rgba(255, 255, 255, 0.12)",
                    borderRadius: "8px",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "10px",
                }, children: [SP_JSX.jsxs("div", { style: {
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            textAlign: "center",
                            gap: "4px",
                        }, children: [SP_JSX.jsx(FaBluetooth, { size: 24, color: "#3b82f6", style: { opacity: 0.8 } }), SP_JSX.jsx("div", { style: { fontWeight: 600, fontSize: "14px" }, children: "No Sony Headphones Connected" }), SP_JSX.jsx("div", { style: { fontSize: "11px", color: "#9ca3af" }, children: "Pair and connect your WH-1000XM or WF-1000XM via SteamOS Bluetooth Settings." })] }), status.last_error && (SP_JSX.jsxs("div", { style: {
                            backgroundColor: "rgba(239, 68, 68, 0.15)",
                            border: "1px solid rgba(239, 68, 68, 0.3)",
                            borderRadius: "6px",
                            padding: "8px 10px",
                            fontSize: "11px",
                            color: "#fca5a5",
                            wordBreak: "break-word",
                        }, children: [SP_JSX.jsx("strong", { children: "Status:" }), " ", status.last_error] })), status.mac && (SP_JSX.jsxs("div", { style: { fontSize: "11px", color: "#9ca3af", textAlign: "center" }, children: ["Last attempted device: ", SP_JSX.jsx("strong", { children: status.device_name || "Sony Headphones" }), " (", status.mac, ")"] })), SP_JSX.jsx("div", { style: { display: "flex", gap: "8px", marginTop: "2px" }, children: onScan && (SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => onScan(), disabled: disabled, children: SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "6px", justifyContent: "center" }, children: [SP_JSX.jsx(FaSyncAlt, {}), " Scan & Reconnect"] }) })) }), devices.length > 0 && (SP_JSX.jsxs("div", { style: { marginTop: "4px", borderTop: "1px solid rgba(255, 255, 255, 0.08)", paddingTop: "8px" }, children: [SP_JSX.jsx("div", { style: { fontSize: "11px", fontWeight: 600, color: "#93c5fd", marginBottom: "6px" }, children: "Detected Bluetooth Devices:" }), SP_JSX.jsx("div", { style: { display: "flex", flexDirection: "column", gap: "6px" }, children: devices.map((dev) => (SP_JSX.jsxs("div", { style: {
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "space-between",
                                        backgroundColor: dev.is_sony ? "rgba(59, 130, 246, 0.15)" : "rgba(255, 255, 255, 0.04)",
                                        border: dev.is_sony ? "1px solid rgba(59, 130, 246, 0.4)" : "1px solid rgba(255, 255, 255, 0.05)",
                                        padding: "6px 10px",
                                        borderRadius: "6px",
                                    }, children: [SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", maxWidth: "60%" }, children: [SP_JSX.jsx("span", { style: { fontSize: "12px", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }, children: dev.name || dev.alias || dev.mac }), SP_JSX.jsxs("span", { style: { fontSize: "10px", color: "#9ca3af" }, children: [dev.mac, " ", dev.connected ? "• Connected" : "• Paired", " ", dev.is_sony ? "• Sony MDR" : ""] })] }), onConnect && (SP_JSX.jsx("button", { onClick: () => onConnect(dev.mac), disabled: disabled, style: {
                                                backgroundColor: "#2563eb",
                                                color: "#fff",
                                                border: "none",
                                                borderRadius: "4px",
                                                padding: "4px 10px",
                                                fontSize: "11px",
                                                cursor: "pointer",
                                            }, children: "Connect" }))] }, dev.mac))) })] })), SP_JSX.jsx("div", { style: { marginTop: "4px", textAlign: "center" }, children: SP_JSX.jsx("button", { onClick: () => setShowManual(!showManual), style: {
                                background: "none",
                                border: "none",
                                color: "#60a5fa",
                                fontSize: "11px",
                                cursor: "pointer",
                                textDecoration: "underline",
                            }, children: showManual ? "Hide Manual Connect" : "Manual MAC Address Connect" }) }), showManual && (SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column", gap: "6px" }, children: [SP_JSX.jsx(DFL.TextField, { label: "Bluetooth MAC Address", value: manualMac, onChange: (e) => setManualMac(e.target.value) }), onConnect && (SP_JSX.jsx(DFL.ButtonItem, { layout: "below", onClick: () => {
                                    if (manualMac.trim()) {
                                        onConnect(manualMac.trim());
                                    }
                                }, disabled: disabled || !manualMac.trim(), children: "Connect to MAC" }))] }))] }) }));
    }
    return null;
};

const BatterySection = ({ status }) => {
    if (!status.connected) {
        return null;
    }
    const level = status.battery_level;
    const renderBatteryIcon = () => {
        if (level === null || level === undefined)
            return SP_JSX.jsx(FaBatteryEmpty, { size: 18, color: "#888" });
        if (level > 80)
            return SP_JSX.jsx(FaBatteryFull, { size: 18, color: "#52c41a" });
        if (level > 50)
            return SP_JSX.jsx(FaBatteryThreeQuarters, { size: 18, color: "#52c41a" });
        if (level > 25)
            return SP_JSX.jsx(FaBatteryHalf, { size: 18, color: "#faad14" });
        if (level > 10)
            return SP_JSX.jsx(FaBatteryQuarter, { size: 18, color: "#f5222d" });
        return SP_JSX.jsx(FaBatteryEmpty, { size: 18, color: "#f5222d" });
    };
    return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsxs("div", { style: {
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                width: "100%",
                padding: "4px 0",
            }, children: [SP_JSX.jsxs("div", { style: { display: "flex", flexDirection: "column" }, children: [SP_JSX.jsx("span", { style: { fontWeight: 600, fontSize: "14px" }, children: status.device_name || "Sony Headphones" }), SP_JSX.jsx("span", { style: { fontSize: "11px", color: "#8b949e" }, children: "Connected via RFCOMM" })] }), SP_JSX.jsxs("div", { style: { display: "flex", alignItems: "center", gap: "6px" }, children: [status.charging && SP_JSX.jsx(FaBolt, { size: 14, color: "#fadb14", title: "Charging" }), renderBatteryIcon(), SP_JSX.jsx("span", { style: { fontWeight: 600, fontSize: "14px" }, children: level !== null && level !== undefined ? `${level}%` : "—" })] })] }) }));
};

const ANC_OPTIONS = [
    { data: "cancelling", label: "Noise Cancelling" },
    { data: "ambient", label: "Ambient Sound" },
    { data: "off", label: "Off" },
];
const ANCControls = ({ state, disabled, onModeChange }) => {
    return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.DropdownItem, { label: "Noise Control", disabled: disabled, rgOptions: ANC_OPTIONS, selectedOption: state.mode, onChange: (option) => onModeChange(option.data) }) }));
};

const AmbientSlider = ({ state, disabled, onLevelChange, onVoiceFocusChange }) => {
    if (state.mode !== "ambient") {
        return null;
    }
    return (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.SliderField, { label: "Ambient Sound Level", disabled: disabled, value: state.ambient_level, min: 1, max: 20, step: 1, showValue: true, onChange: (val) => onLevelChange(val) }) }), SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "Focus on Voice", description: "Enhances voices while reducing background noise", disabled: disabled, checked: state.voice_focus, onChange: (checked) => onVoiceFocusChange(checked) }) })] }));
};

const SpeakToChatToggle = ({ enabled, disabled, onChange }) => {
    return (SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "Speak-to-Chat", description: "Pauses music and enables ambient sound when you speak", disabled: disabled, checked: enabled, onChange: (checked) => onChange(checked) }) }));
};

const XMDeckPanel = () => {
    const [connection, setConnection] = SP_REACT.useState({
        connected: false,
        device_name: null,
        battery_level: null,
        charging: false,
        is_busy: false,
        last_error: null,
    });
    const [devices, setDevices] = SP_REACT.useState([]);
    const [anc, setAnc] = SP_REACT.useState({
        mode: "cancelling",
        ambient_level: 1,
        voice_focus: false,
    });
    const [speakToChat, setSpeakToChat] = SP_REACT.useState(false);
    const [loading, setLoading] = SP_REACT.useState(false);
    // Fetch initial statuses from backend daemon
    const refreshStatus = SP_REACT.useCallback(async () => {
        try {
            const connStatus = await call("get_connection_status");
            if (connStatus) {
                setConnection(connStatus);
            }
            if (connStatus?.connected) {
                const ancState = await call("get_anc_state");
                if (ancState) {
                    setAnc(ancState);
                }
            }
        }
        catch (e) {
            console.error("[XMDeck] Failed refreshing status:", e);
        }
    }, []);
    const fetchDevices = SP_REACT.useCallback(async () => {
        try {
            const scanned = await call("scan_devices");
            if (scanned) {
                setDevices(scanned);
            }
        }
        catch (e) {
            console.error("[XMDeck] Failed scanning Bluetooth devices:", e);
        }
    }, []);
    SP_REACT.useEffect(() => {
        refreshStatus();
        fetchDevices();
        const onStateChanged = (update) => {
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
        addEventListener("xmdeck_state_changed", onStateChanged);
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
    const handleModeChange = async (mode) => {
        setAnc((prev) => ({ ...prev, mode }));
        setLoading(true);
        try {
            await call("set_anc_mode", mode);
        }
        catch (e) {
            console.error("[XMDeck] Failed setting ANC mode:", e);
            refreshStatus();
        }
        finally {
            setLoading(false);
        }
    };
    const handleLevelChange = async (ambient_level) => {
        setAnc((prev) => ({ ...prev, ambient_level }));
        try {
            await call("set_ambient_sound", ambient_level, anc.voice_focus);
        }
        catch (e) {
            console.error("[XMDeck] Failed setting ambient level:", e);
        }
    };
    const handleVoiceFocusChange = async (voice_focus) => {
        setAnc((prev) => ({ ...prev, voice_focus }));
        try {
            await call("set_ambient_sound", anc.ambient_level, voice_focus);
        }
        catch (e) {
            console.error("[XMDeck] Failed setting voice focus:", e);
        }
    };
    const handleSpeakToChatChange = async (enabled) => {
        setSpeakToChat(enabled);
        try {
            await call("set_speak_to_chat", enabled);
        }
        catch (e) {
            console.error("[XMDeck] Failed setting Speak-to-Chat:", e);
            refreshStatus();
        }
    };
    const handleManualConnect = async (mac) => {
        setLoading(true);
        try {
            await call("connect_device", mac);
            await refreshStatus();
        }
        catch (e) {
            console.error("[XMDeck] Manual connect failed:", e);
        }
        finally {
            setLoading(false);
        }
    };
    const handleManualScan = async () => {
        setLoading(true);
        try {
            await call("trigger_connect");
            await fetchDevices();
            await refreshStatus();
        }
        catch (e) {
            console.error("[XMDeck] Manual scan failed:", e);
        }
        finally {
            setLoading(false);
        }
    };
    return (SP_JSX.jsxs(DFL.PanelSection, { title: "Sony WH/WF Headphones", children: [SP_JSX.jsx(ConnectionBanner, { status: connection, devices: devices, onConnect: handleManualConnect, onScan: handleManualScan, disabled: loading }), connection.connected && (SP_JSX.jsxs(SP_JSX.Fragment, { children: [SP_JSX.jsx(BatterySection, { status: connection }), SP_JSX.jsx(ANCControls, { state: anc, disabled: loading, onModeChange: handleModeChange }), SP_JSX.jsx(AmbientSlider, { state: anc, disabled: loading, onLevelChange: handleLevelChange, onVoiceFocusChange: handleVoiceFocusChange }), SP_JSX.jsx(SpeakToChatToggle, { enabled: speakToChat, disabled: loading, onChange: handleSpeakToChatChange })] }))] }));
};
var index = DFL.definePlugin(() => {
    return {
        title: SP_JSX.jsx("div", { className: DFL.staticClasses.Title, children: "XMDeck" }),
        content: SP_JSX.jsx(XMDeckPanel, {}),
        icon: SP_JSX.jsx(FaHeadphones, {}),
        onDismount() { },
    };
});

export { index as default };
//# sourceMappingURL=index.js.map
