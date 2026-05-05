import React, { useState } from "react";

function Toggle({ on, onClick }) {
  return (
    <div onClick={onClick} role="switch" aria-checked={on}
      style={{
        width: 44, minWidth: 44, height: 24, borderRadius: 12,
        background: on ? "linear-gradient(135deg,#22c55e,#16a34a)" : "#334155",
        position: "relative", cursor: "pointer", flexShrink: 0,
        transition: "background .3s", display: "inline-block"
      }}>
      <div style={{
        position: "absolute", top: 3, left: on ? 23 : 3,
        width: 18, height: 18, borderRadius: "50%",
        background: "#fff", transition: "left .25s ease",
        boxShadow: "0 1px 4px rgba(0,0,0,.3)"
      }} />
    </div>
  );
}

function Section({ icon, title, isOpen, onToggle, children }) {
  return (
    <div style={{
      background: "rgba(13,17,23,.8)", border: "1px solid rgba(30,41,59,.5)",
      borderRadius: 12, backdropFilter: "blur(6px)", flexShrink: 0
    }}>
      <div onClick={onToggle} style={{
        padding: "14px 18px", borderBottom: isOpen ? "1px solid rgba(30,41,59,.4)" : "none",
        display: "flex", alignItems: "center", gap: 10,
        cursor: "pointer", userSelect: "none"
      }}>
        <span style={{ fontSize: 16 }}>{icon}</span>
        <h3 style={{ flex: 1, fontSize: 13, fontWeight: 700, color: "#e2e8f0", margin: 0 }}>{title}</h3>
        <span style={{
          fontSize: 14, color: "#64748b", transition: "transform .25s",
          transform: isOpen ? "rotate(180deg)" : "rotate(0)"
        }}>▾</span>
      </div>
      {isOpen && <div style={{ padding: "8px 18px 12px" }}>{children}</div>}
    </div>
  );
}

function Row({ label, desc, children }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "11px 0", borderBottom: "1px solid rgba(30,41,59,.12)", minHeight: 44
    }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 2, flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 500 }}>{label}</span>
        {desc && <span style={{ fontSize: 10, color: "#64748b" }}>{desc}</span>}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0, marginLeft: 16 }}>
        {children}
      </div>
    </div>
  );
}

function NumInput({ value, onChange, min, max, step }) {
  return (
    <input type="number" min={min} max={max} step={step} value={value}
      onChange={e => onChange(parseInt(e.target.value) || min || 0)}
      style={{
        width: 68, background: "rgba(15,23,42,.6)", border: "1px solid rgba(30,41,59,.5)",
        borderRadius: 6, padding: "5px 8px", color: "#e2e8f0", fontSize: 12,
        fontFamily: "JetBrains Mono, monospace", textAlign: "center"
      }} />
  );
}

function Slider({ value, onChange, min, max, step, suffix }) {
  return (
    <>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        style={{ width: 110, accentColor: "#3b82f6", cursor: "pointer" }} />
      <span style={{ fontSize: 12, color: "#e2e8f0", fontFamily: "JetBrains Mono", width: 40, textAlign: "right" }}>
        {typeof value === "number" && value < 1 ? `${(value * 100).toFixed(0)}%` : `${value}${suffix || ""}`}
      </span>
    </>
  );
}

function Dropdown({ value, onChange, options }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)}
      style={{
        background: "rgba(15,23,42,.8)", border: "1px solid rgba(30,41,59,.5)",
        borderRadius: 6, padding: "5px 10px", color: "#e2e8f0", fontSize: 12, cursor: "pointer"
      }}>
      {options.map(o => <option key={o.v} value={o.v} style={{ background: "#0d1117" }}>{o.l}</option>)}
    </select>
  );
}

const Unit = ({ u }) => <span style={{ fontSize: 11, color: "#64748b" }}>{u}</span>;

export default function Settings({ settings, updateSetting, saveSettings, resetSettings, clearFrames, clearAnalytics, systemStats }) {
  const [open, setOpen] = useState({ det: true, sig: true, disp: false, alert: false, sys: false, info: false });
  const t = k => setOpen(p => ({ ...p, [k]: !p[k] }));
  const s = settings;
  const us = updateSetting;

  return (
    <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column" }}>
      {/* Scrollable content */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 24px 16px", display: "flex", flexDirection: "column", gap: 12 }}>

        {/* Detection */}
        <Section icon="🎯" title="Detection Settings" isOpen={open.det} onToggle={() => t("det")}>
          <Row label="AI Model" desc="Detection model for vehicle recognition">
            <Dropdown value={s.detection.model} onChange={v => us("detection", "model", v)}
              options={[{ v: "YOLOv8x", l: "YOLOv8x (Best)" }, { v: "YOLOv8l", l: "YOLOv8l (Balanced)" }, { v: "YOLOv8m", l: "YOLOv8m (Fast)" }, { v: "YOLOv4-tiny", l: "YOLOv4-tiny (Fastest)" }]} />
          </Row>
          <Row label="Confidence Threshold" desc={`Minimum confidence to count (${(s.detection.confidence * 100).toFixed(0)}%)`}>
            <Slider value={s.detection.confidence} onChange={v => us("detection", "confidence", v)} min={0.05} max={0.95} step={0.05} />
          </Row>
          <Row label="IOU Threshold" desc={`Overlap suppression (${(s.detection.iou * 100).toFixed(0)}%)`}>
            <Slider value={s.detection.iou} onChange={v => us("detection", "iou", v)} min={0.1} max={0.9} step={0.05} />
          </Row>
          <Row label="Inference Image Size" desc="Larger = more accurate but slower">
            <Dropdown value={s.detection.imageSize} onChange={v => us("detection", "imageSize", parseInt(v))}
              options={[{ v: 320, l: "320px" }, { v: 416, l: "416px" }, { v: 640, l: "640px" }, { v: 832, l: "832px" }]} />
          </Row>
          <Row label="Min Track Frames" desc="Frames needed to count vehicle">
            <NumInput value={s.detection.minTrackFrames} onChange={v => us("detection", "minTrackFrames", v)} min={1} max={30} />
          </Row>
          <Row label="Max Disappeared" desc="Frames before track removed">
            <NumInput value={s.detection.maxDisappeared} onChange={v => us("detection", "maxDisappeared", v)} min={5} max={60} />
          </Row>
        </Section>

        {/* Signal Timing */}
        <Section icon="🚦" title="Signal Timing" isOpen={open.sig} onToggle={() => t("sig")}>
          <Row label="Base Green Time" desc="Minimum green duration">
            <NumInput value={s.signal.baseGreen} onChange={v => us("signal", "baseGreen", v)} min={5} max={30} /><Unit u="sec" />
          </Row>
          <Row label="Max Green Time" desc="Maximum green duration">
            <NumInput value={s.signal.maxGreen} onChange={v => us("signal", "maxGreen", v)} min={20} max={120} /><Unit u="sec" />
          </Row>
          <Row label="Yellow Time" desc="Yellow signal between phases">
            <NumInput value={s.signal.yellowTime} onChange={v => us("signal", "yellowTime", v)} min={1} max={8} /><Unit u="sec" />
          </Row>
          <Row label="All-Red Time" desc="Safety clearance time">
            <NumInput value={s.signal.allRedTime} onChange={v => us("signal", "allRedTime", v)} min={1} max={5} /><Unit u="sec" />
          </Row>
          <Row label="Total Cycle Time" desc="Maximum total signal cycle">
            <NumInput value={s.signal.cycleTime} onChange={v => us("signal", "cycleTime", v)} min={60} max={300} /><Unit u="sec" />
          </Row>
          <Row label="Adaptive Auto Mode" desc="AI adjusts timing automatically">
            <Toggle on={s.signal.autoMode} onClick={() => us("signal", "autoMode", !s.signal.autoMode)} />
          </Row>
          <Row label="Emergency Preemption" desc="Override for emergency vehicles">
            <Toggle on={s.signal.emergencyPreemption} onClick={() => us("signal", "emergencyPreemption", !s.signal.emergencyPreemption)} />
          </Row>
          <Row label="Pedestrian Phase" desc="Dedicated crossing phase">
            <Toggle on={s.signal.pedestrianPhase} onClick={() => us("signal", "pedestrianPhase", !s.signal.pedestrianPhase)} />
          </Row>
        </Section>

        {/* Display */}
        <Section icon="🖥️" title="Display & Visualization" isOpen={open.disp} onToggle={() => t("disp")}>
          <Row label="Frame Refresh Rate" desc="Camera feed update frequency">
            <Dropdown value={s.display.frameRefreshRate} onChange={v => us("display", "frameRefreshRate", parseInt(v))}
              options={[{ v: 250, l: "250ms (Smooth)" }, { v: 500, l: "500ms (Balanced)" }, { v: 1000, l: "1s (Low CPU)" }, { v: 2000, l: "2s (Minimal)" }]} />
          </Row>
          <Row label="Frame Quality" desc={`JPEG quality (${s.display.frameQuality}%)`}>
            <Slider value={s.display.frameQuality} onChange={v => us("display", "frameQuality", parseInt(v))} min={30} max={100} step={5} suffix="%" />
          </Row>
          <Row label="Show Vehicle Trails" desc="Movement paths on feed">
            <Toggle on={s.display.showTrails} onClick={() => us("display", "showTrails", !s.display.showTrails)} />
          </Row>
          <Row label="Show Bounding Boxes" desc="Detection boxes on vehicles">
            <Toggle on={s.display.showBoundingBoxes} onClick={() => us("display", "showBoundingBoxes", !s.display.showBoundingBoxes)} />
          </Row>
          <Row label="Show Confidence Score" desc="AI confidence % overlay">
            <Toggle on={s.display.showConfidence} onClick={() => us("display", "showConfidence", !s.display.showConfidence)} />
          </Row>
          <Row label="Show Vehicle Count" desc="Count overlay on each feed">
            <Toggle on={s.display.showVehicleCount} onClick={() => us("display", "showVehicleCount", !s.display.showVehicleCount)} />
          </Row>
        </Section>

        {/* Alerts */}
        <Section icon="🔔" title="Alerts & Notifications" isOpen={open.alert} onToggle={() => t("alert")}>
          <Row label="Congestion Threshold" desc="Vehicles to trigger alert">
            <NumInput value={s.alerts.congestionThreshold} onChange={v => us("alerts", "congestionThreshold", v)} min={5} max={50} />
          </Row>
          <Row label="Low Traffic Threshold" desc="Below this may skip phase">
            <NumInput value={s.alerts.lowTrafficThreshold} onChange={v => us("alerts", "lowTrafficThreshold", v)} min={0} max={10} />
          </Row>
          <Row label="Emergency Vehicle Alerts" desc="Notify on detection">
            <Toggle on={s.alerts.emergencyAlert} onClick={() => us("alerts", "emergencyAlert", !s.alerts.emergencyAlert)} />
          </Row>
          <Row label="Sound Alerts" desc="Play sound on critical alerts">
            <Toggle on={s.alerts.soundAlerts} onClick={() => us("alerts", "soundAlerts", !s.alerts.soundAlerts)} />
          </Row>
        </Section>

        {/* System */}
        <Section icon="🛠️" title="System & Data" isOpen={open.sys} onToggle={() => t("sys")}>
          <Row label="Log Level" desc="Backend logging verbosity">
            <Dropdown value={s.system.logLevel} onChange={v => us("system", "logLevel", v)}
              options={[{ v: "debug", l: "Debug" }, { v: "info", l: "Info" }, { v: "warning", l: "Warning" }, { v: "error", l: "Error Only" }]} />
          </Row>
          <Row label="Max Video Duration" desc="Processing timeout">
            <NumInput value={s.system.maxVideoDuration} onChange={v => us("system", "maxVideoDuration", v)} min={300} max={3600} step={60} /><Unit u="sec" />
          </Row>
          <Row label="Auto Cleanup Frames" desc="Remove old detection frames">
            <Toggle on={s.system.autoCleanup} onClick={() => us("system", "autoCleanup", !s.system.autoCleanup)} />
          </Row>
          <Row label="Data Retention" desc="Days to keep analytics">
            <NumInput value={s.system.dataRetentionDays} onChange={v => us("system", "dataRetentionDays", v)} min={1} max={365} /><Unit u="days" />
          </Row>
        </Section>

        {/* System Status */}
        {systemStats && (
          <Section icon="📡" title="System Status" isOpen={open.info} onToggle={() => t("info")}>
            {[
              { l: "Backend Version", v: `v${systemStats.backend_version || "4.0"}` },
              { l: "Detection Engine", v: systemStats.detection_engine || "YOLOv8x" },
              { l: "Uptime", v: systemStats.uptime_formatted || "—" },
              { l: "Total Detections", v: String(systemStats.total_detections || 0) },
              { l: "Status", v: systemStats.status || "unknown" },
            ].map((item, i) => (
              <Row key={i} label={item.l}>
                <span style={{
                  fontSize: 13, fontFamily: "JetBrains Mono", fontWeight: 600,
                  color: item.l === "Status" ? (item.v === "operational" ? "#22c55e" : "#ef4444") : "#e2e8f0"
                }}>
                  {item.v.charAt(0).toUpperCase() + item.v.slice(1)}
                </span>
              </Row>
            ))}
          </Section>
        )}

        {/* spacer so last section isn't flush with buttons */}
        <div style={{ height: 4, flexShrink: 0 }} />
      </div>

      {/* Sticky button bar */}
      <div style={{
        display: "flex", gap: 10, flexWrap: "wrap", padding: "10px 24px",
        borderTop: "1px solid rgba(30,41,59,.4)", background: "rgba(6,8,15,.95)", flexShrink: 0
      }}>
        <button className="btn btn-primary" onClick={() => saveSettings(settings)}>💾 Save All Settings</button>
        <button className="btn btn-ghost" onClick={resetSettings}>🔄 Reset to Defaults</button>
        <button className="btn btn-ghost" onClick={clearFrames}>🗑️ Clear Frames</button>
        <button className="btn btn-ghost" onClick={clearAnalytics}>📊 Clear Analytics</button>
      </div>
    </div>
  );
}
